import os
import numpy as np
import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader
)

from rag_pipeline.vectore_store import load_store, save_store, embedder
from rag_pipeline.config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP


# ======================================================
# File Hash (For Updated Policy Detection)
# ======================================================
def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# ======================================================
# Document Loader (PDF + DOCX + TXT)
# ======================================================
def load_document(file_path):
    if file_path.lower().endswith(".pdf"):
        return PyPDFLoader(file_path).load()

    if file_path.lower().endswith(".docx"):
        return Docx2txtLoader(file_path).load()

    if file_path.lower().endswith(".txt"):
        try:
            return TextLoader(file_path, encoding="utf-8").load()
        except Exception:
            print("⚠️ UTF-8 failed, retrying with cp1252 encoding...")
            return TextLoader(file_path, encoding="cp1252").load()

    raise ValueError(f"Unsupported file type: {file_path}")


# ======================================================
# Main Ingestion Function
# ======================================================
def ingest():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing vector store
    doc_index, texts, metadata, indexed_files = load_store()

    SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")

    # Detect all supported documents
    doc_files = [
        f for f in os.listdir(DATA_DIR)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]

    # Only process new files
    new_files = [f for f in doc_files if f not in indexed_files]

    if not new_files:
        print("✅ No new documents to process")
        return

    print(f"📄 Processing {len(new_files)} new documents...\n")

    # Process each new document
    for file in new_files:
        file_path = os.path.join(DATA_DIR, file)

        print(f"➡️ Loading: {file}")

        # Load document pages
        pages = load_document(file_path)

        # Add metadata
        for p in pages:
            p.metadata["source"] = file
            p.metadata["file_type"] = file.split(".")[-1].lower()

        # Chunking
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

        chunks = splitter.split_documents(pages)

        new_texts = [c.page_content for c in chunks]
        new_meta = [c.metadata for c in chunks]

        # Embeddings
        print("🔹 Generating embeddings...")
        new_embeddings = embedder.encode(new_texts, show_progress_bar=True)

        # Add to FAISS
        doc_index.add(np.array(new_embeddings))

        texts.extend(new_texts)
        metadata.extend(new_meta)

        # Save hash tracking
        indexed_files[file] = file_hash(file_path)

        print(f"✅ Added {len(chunks)} chunks from {file}\n")

    # Save everything
    save_store(doc_index, texts, metadata, indexed_files)

    print("✅ Index updated successfully!")
    print("Total indexed chunks:", len(texts))
