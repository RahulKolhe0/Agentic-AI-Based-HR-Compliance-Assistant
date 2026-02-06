from sentence_transformers import CrossEncoder
from rag_pipeline.config import FINAL_TOP_K

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_chunks(query, chunks):
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs)
    for i,s in enumerate(scores):
        chunks[i]["score"] = float(s)
    return sorted(chunks, key=lambda x:x["score"], reverse=True)[:FINAL_TOP_K]
