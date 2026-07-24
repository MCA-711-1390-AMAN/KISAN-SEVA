"""
backend/ingest.py — UPDATED with live government data sources
─────────────────────────────────────────────────────────────
Same as your original ingest.py, but now combines:
  • PDF files in data/schemes/        (existing)
  • Live data.gov.in API records       (new — needs API key)
  • Live web-scraped scheme pages      (new — works out of the box)
  • myScheme.gov.in dataset mirror     (new — needs huggingface_hub)

If the live sources fail (no API key set, no internet, etc.) this
script still works exactly like before — PDFs only. Nothing breaks.
"""

import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from live_data_loader import fetch_all_live_sources

BASE_DIR          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMES_DIR       = os.path.join(BASE_DIR, "data", "schemes")
VECTORSTORE_PATH  = os.path.join(BASE_DIR, "vectorstore", "faiss_index")


def load_all_pdfs(directory: str):
    """Load every PDF found in the schemes folder (unchanged from before)."""
    all_docs = []
    if not os.path.isdir(directory):
        print(f"⚠️  {directory} does not exist — skipping PDFs")
        return []

    pdf_files = [f for f in os.listdir(directory) if f.endswith(".pdf")]
    if not pdf_files:
        print("No PDFs found in data/schemes/")
        return []

    for filename in pdf_files:
        filepath = os.path.join(directory, filename)
        print(f"Loading PDF: {filename}")
        loader = PyMuPDFLoader(filepath)
        docs = loader.load()

        scheme_name = filename.replace(".pdf", "").replace("_", " ").title()
        for doc in docs:
            doc.metadata["scheme_name"] = scheme_name
            doc.metadata["source_file"] = filename
            doc.metadata["source_type"] = "pdf"

        all_docs.extend(docs)
        print(f"  → {len(docs)} pages loaded from {filename}")

    return all_docs


def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(docs)
    print(f"\nTotal chunks created: {len(chunks)}")
    return chunks


def build_vectorstore(chunks):
    print("\nLoading embedding model (first time ~2 min)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "mps"}
    )

    print("Building FAISS vector store...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    os.makedirs(os.path.dirname(VECTORSTORE_PATH), exist_ok=True)
    vectorstore.save_local(VECTORSTORE_PATH)
    print(f"✅ Vector store saved to {VECTORSTORE_PATH}")
    return vectorstore


def main():
    print("=== Kisan Seva — PDF + Live Data Ingestion ===\n")

    # Source 1: your existing PDFs (always works)
    pdf_docs = load_all_pdfs(SCHEMES_DIR)

    # Sources 2, 3, 4: live government data (fault-tolerant — never crashes)
    live_docs = fetch_all_live_sources()

    all_docs = pdf_docs + live_docs

    if not all_docs:
        print("❌ No documents loaded from any source. "
              "Add PDFs to data/schemes/ or configure live sources.")
        exit(1)

    print(f"\nTotal documents before chunking: {len(all_docs)} "
          f"({len(pdf_docs)} from PDFs, {len(live_docs)} from live sources)")

    chunks = split_documents(all_docs)
    build_vectorstore(chunks)
    print("\n✅ Ingestion complete! Knowledge base now includes live government data.")


if __name__ == "__main__":
    main()