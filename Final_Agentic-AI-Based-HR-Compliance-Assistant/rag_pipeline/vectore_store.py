import os
import faiss
import pickle
import json
from sentence_transformers import SentenceTransformer

from rag_pipeline.config import VECTOR_DIR

DOC_INDEX_PATH = os.path.join(VECTOR_DIR, "doc_index.faiss")
TEXTS_PATH = os.path.join(VECTOR_DIR, "texts.pkl")
METADATA_PATH = os.path.join(VECTOR_DIR, "metadata.pkl")
INDEXED_FILES_PATH = os.path.join(VECTOR_DIR, "indexed_files.json")

embedder = SentenceTransformer("all-MiniLM-L6-v2")
dimension = embedder.get_sentence_embedding_dimension()


# -----------------------------
# Load Vector Store
# -----------------------------
def load_store():
    os.makedirs(VECTOR_DIR, exist_ok=True)

    if os.path.exists(DOC_INDEX_PATH):
        print("✅ Loading existing vector store...")

        doc_index = faiss.read_index(DOC_INDEX_PATH)

        with open(TEXTS_PATH, "rb") as f:
            texts = pickle.load(f)

        with open(METADATA_PATH, "rb") as f:
            metadata = pickle.load(f)

        # ✅ Load indexed_files
        if os.path.exists(INDEXED_FILES_PATH):
            with open(INDEXED_FILES_PATH, "r") as f:
                indexed_files = json.load(f)

            # ✅ FIX: Convert old list → dict
            if isinstance(indexed_files, list):
                indexed_files = {fname: "" for fname in indexed_files}

        else:
            indexed_files = {}

    else:
        print("🆕 Creating new vector store...")

        doc_index = faiss.IndexFlatL2(dimension)
        texts = []
        metadata = []
        indexed_files = {}

    return doc_index, texts, metadata, indexed_files


# -----------------------------
# Save Vector Store
# -----------------------------
def save_store(doc_index, texts, metadata, indexed_files):
    faiss.write_index(doc_index, DOC_INDEX_PATH)

    with open(TEXTS_PATH, "wb") as f:
        pickle.dump(texts, f)

    with open(METADATA_PATH, "wb") as f:
        pickle.dump(metadata, f)

    with open(INDEXED_FILES_PATH, "w") as f:
        json.dump(indexed_files, f, indent=2)

    print("✅ Vector store saved successfully!")


# -----------------------------
# Reset Store (Rebuild)
# -----------------------------
def reset_store():
    doc_index = faiss.IndexFlatL2(dimension)
    return doc_index, [], [], {}
