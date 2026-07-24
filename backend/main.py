import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from eligibility import FarmerProfile, check_eligibility
from rag_chain import load_rag_chain

from dotenv import load_dotenv
load_dotenv()

# ── Paths ──────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ── Global RAG chain ───────────────────────────────────
rag_chain = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain
    print("Starting Kisan Seva API...")
    try:
        rag_chain = load_rag_chain()
        print("✅ RAG chain loaded successfully")
    except Exception as e:
        print(f"⚠️  RAG chain failed to load: {e}")
        print("Chat endpoint will be unavailable until PDFs are ingested.")
    yield

app = FastAPI(
    title="Kisan Seva API",
    description="Government Scheme Finder for Indian Farmers",
    version="1.0.0",
    lifespan=lifespan
)

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Serve frontend ─────────────────────────────────────
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── Request / Response models ──────────────────────────
class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    sources: list


# ── Routes ─────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/farmer")
async def farmer_interface():
    return FileResponse(os.path.join(FRONTEND_DIR, "farmer.html"))

@app.get("/admin")
async def admin_interface():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))

@app.get("/operator")
async def operator_interface():
    return FileResponse(os.path.join(FRONTEND_DIR, "operator.html"))


@app.get("/health")
async def health():
    return {
        "status": "running",
        "rag_ready": rag_chain is not None
    }


@app.get("/api/schemes")
async def list_schemes():
    from eligibility import SCHEMES
    return {
        "total": len(SCHEMES),
        "schemes": [
            {
                "id":        s["id"],
                "name":      s["name"],
                "full_name": s["full_name"],
                "benefit":   s["benefit"]
            }
            for s in SCHEMES
        ]
    }


@app.post("/api/eligibility")
async def eligibility(profile: FarmerProfile):
    try:
        results        = check_eligibility(profile)
        eligible_count = sum(1 for r in results if r["eligible"])
        return {
            "success":        True,
            "total_schemes":  len(results),
            "eligible_count": eligible_count,
            "schemes":        results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not ready. Please run ingest.py first."
        )
    try:
        response = rag_chain.invoke({"question": req.question})
        sources  = []
        for doc in response.get("source_documents", []):
            sources.append({
                "scheme":  doc.metadata.get("scheme_name", "Unknown"),
                "file":    doc.metadata.get("source_file", ""),
            })
        return ChatResponse(
            answer=response["answer"],
            sources=sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-checklist")
async def download_checklist(profile: FarmerProfile):
    """Generate a downloadable documents checklist for eligible schemes."""
    try:
        schemes  = check_eligibility(profile)
        eligible = [s for s in schemes if s["eligible"]]

        lines = []
        lines.append("=" * 52)
        lines.append("        KISAN SEVA — DOCUMENTS CHECKLIST")
        lines.append("=" * 52)
        lines.append("")
        lines.append("Farmer Profile:")
        lines.append(f"  State        : {profile.state}")
        lines.append(f"  Land         : {profile.land_acres} acres")
        lines.append(f"  Category     : {profile.category}")
        lines.append(f"  Crop         : {profile.crop_type}")
        lines.append(f"  Annual Income: Rs. {int(profile.annual_income):,}")
        lines.append("")
        lines.append(f"Aap {len(eligible)} schemes ke liye eligible hain.")
        lines.append("-" * 52)

        for i, scheme in enumerate(eligible, 1):
            lines.append("")
            lines.append(f"{i}. {scheme['full_name']} ({scheme['name']})")
            lines.append(f"   Benefit  : {scheme['benefit']}")
            lines.append(f"   Apply at : {scheme['apply_at']}")
            lines.append(f"   Documents required:")
            for doc in scheme["documents"]:
                lines.append(f"     [ ]  {doc}")

        lines.append("")
        lines.append("=" * 52)
        lines.append("  Generated by Kisan Seva AI")
        lines.append("  Apne nazdiki CSC centre par ye documents")
        lines.append("  lekar jaayein.")
        lines.append("=" * 52)

        content = "\n".join(lines)
        return Response(
            content=content.encode("utf-8"),
            media_type="text/plain",
            headers={
                "Content-Disposition":
                    "attachment; filename=kisan_seva_checklist.txt"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))