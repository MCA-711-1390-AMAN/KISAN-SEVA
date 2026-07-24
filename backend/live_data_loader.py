"""
backend/live_data_loader.py
─────────────────────────────────────────────────────────
Kisan Seva — Live Government Data Loader

This module adds THREE new data sources on top of your existing
PDF pipeline, without changing anything that already works:

  1. data.gov.in API      → structured datasets (real, verified API)
  2. Web scraping          → pmkisan.gov.in / pmfby.gov.in live pages
  3. HuggingFace mirror    → 723 pre-scraped myScheme.gov.in scheme PDFs
                             (myscheme.gov.in has NO public REST API,
                              so this community PDF mirror is the
                              practical substitute — verified June 2026)

Each source returns a list of LangChain Document objects, the same
shape your PDF loader already produces — so they merge into the
same FAISS index with zero changes to rag_chain.py.
"""

import os
os.environ.setdefault("USER_AGENT", "KisanSeva-EducationalProject/1.0")
import time
import json
import requests
from typing import List
from langchain.docstore.document import Document
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DATA_GOV_IN_API_KEY  = os.getenv("DATA_GOV_IN_API_KEY", "")
DATA_GOV_RESOURCE_ID = os.getenv("DATA_GOV_RESOURCE_ID", "")


# ─────────────────────────────────────────────────────────
# SOURCE 1 — data.gov.in Open Government Data API
# ─────────────────────────────────────────────────────────

def fetch_data_gov_in(resource_id: str = None, max_records: int = 100) -> List[Document]:
    resource_id = resource_id or DATA_GOV_RESOURCE_ID
    if not DATA_GOV_IN_API_KEY or not resource_id:
        print("⚠️  data.gov.in skipped — set DATA_GOV_IN_API_KEY and "
              "DATA_GOV_RESOURCE_ID in your .env to enable this source.")
        return []

    url = f"https://api.data.gov.in/resource/{resource_id}"
    params = {
        "api-key": DATA_GOV_IN_API_KEY,
        "format":  "json",
        "limit":   max_records,
    }

    try:
        resp = requests.get(url, params=params, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"⚠️  data.gov.in fetch failed: {e}")
        return []

    records = data.get("records", [])
    docs = []
    for rec in records:
        lines = [f"{k}: {v}" for k, v in rec.items() if v]
        text  = "\n".join(lines)
        if not text.strip():
            continue
        docs.append(Document(
            page_content=text,
            metadata={
                "scheme_name": "PM KISAN Beneficiary Data",
                "source_file": f"data.gov.in/{resource_id}",
                "source_type": "live_api",
            }
        ))

    print(f"✅ data.gov.in: loaded {len(docs)} records")
    return docs


# ─────────────────────────────────────────────────────────
# SOURCE 2 — Live web scraping of official scheme pages
# ─────────────────────────────────────────────────────────

SCHEME_URLS = [
    "https://pmkisan.gov.in/Documents/PMKISAN_Operational_Guidelines.pdf",
    "https://pmfby.gov.in/pdf/RevisedOperationalGuidelinesofPMFBY.pdf",
]


def fetch_live_web_pages(urls: List[str] = None) -> List[Document]:
    urls = urls or SCHEME_URLS
    try:
        from langchain_community.document_loaders import WebBaseLoader
    except ImportError:
        print("⚠️  WebBaseLoader not available — run: "
              "pip install langchain-community beautifulsoup4")
        return []

    all_docs = []
    for url in urls:
        try:
            loader = WebBaseLoader(
                web_paths=[url],
                requests_kwargs={"timeout": 15, "headers": {
                    "User-Agent": "Mozilla/5.0 (KisanSeva Educational Project)"
                }}
            )
            docs = loader.load()
            for d in docs:
                d.metadata["scheme_name"] = url.split("/")[2]
                d.metadata["source_file"] = url
                d.metadata["source_type"] = "live_scrape"
            all_docs.extend(docs)
            print(f"✅ Scraped: {url} ({len(docs)} doc)")
        except Exception as e:
            print(f"⚠️  Failed to scrape {url}: {e}")
        time.sleep(1)

    return all_docs


# ─────────────────────────────────────────────────────────
# SOURCE 3 — myScheme.gov.in dataset (via HuggingFace mirror)
# ─────────────────────────────────────────────────────────

def fetch_myscheme_dataset(max_files: int = 15,
                           download_dir: str = None) -> List[Document]:
    try:
        from huggingface_hub import list_repo_files, hf_hub_download
    except ImportError:
        print("⚠️  huggingface_hub missing — run: pip install huggingface_hub")
        return []

    base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    download_dir = download_dir or os.path.join(base_dir, "data", "myscheme_cache")
    os.makedirs(download_dir, exist_ok=True)

    try:
        files     = list_repo_files("shrijayan/gov_myscheme", repo_type="dataset")
        pdf_files = [f for f in files if f.lower().endswith(".pdf")][:max_files]
    except Exception as e:
        print(f"⚠️  Could not list myScheme dataset files: {e}")
        return []

    if not pdf_files:
        print("⚠️  No PDF files found in myScheme dataset")
        return []

    from langchain_community.document_loaders import PyMuPDFLoader

    docs = []
    for fname in pdf_files:
        try:
            local_path = hf_hub_download(
                repo_id="shrijayan/gov_myscheme",
                filename=fname,
                repo_type="dataset",
                local_dir=download_dir,
            )
            loader    = PyMuPDFLoader(local_path)
            page_docs = loader.load()
            scheme_name = os.path.basename(fname).replace(".pdf", "").replace("_", " ").title()
            for d in page_docs:
                d.metadata["scheme_name"] = scheme_name
                d.metadata["source_file"] = fname
                d.metadata["source_type"] = "live_dataset"
            docs.extend(page_docs)
        except Exception as e:
            print(f"⚠️  Skipped {fname}: {e}")

    print(f"✅ myScheme dataset: loaded {len(docs)} pages from {len(pdf_files)} scheme PDFs")
    return docs


# ─────────────────────────────────────────────────────────
# COMBINED LOADER — used by ingest.py
# ─────────────────────────────────────────────────────────

def fetch_all_live_sources() -> List[Document]:
    print("\n=== Fetching live government data sources ===")
    docs = []
    docs += fetch_data_gov_in()
    docs += fetch_live_web_pages()
    docs += fetch_myscheme_dataset()
    print(f"=== Live sources total: {len(docs)} documents ===\n")
    return docs


if __name__ == "__main__":
    results = fetch_all_live_sources()
    print(f"\nFetched {len(results)} total documents from live sources.")
    if results:
        print("\nSample document:")
        print(results[0].page_content[:300])
        print("Metadata:", results[0].metadata)