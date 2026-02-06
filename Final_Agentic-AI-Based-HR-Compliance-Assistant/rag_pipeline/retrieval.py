import numpy as np
from rag_pipeline.config import TOP_K, SIMILARITY_THRESHOLD
from rag_pipeline.vectore_store import load_store, embedder

doc_index, texts, metadata, _ = load_store()

def retrieve_chunks(query):
    q_emb = embedder.encode([query])
    distances, indices = doc_index.search(np.array(q_emb), TOP_K)

    results = []
    for idx, dist in zip(indices[0], distances[0]):
        if dist < SIMILARITY_THRESHOLD:
            results.append({
                "text": texts[idx],
                "metadata": metadata[idx],
                "distance": float(dist)
            })
    return results
