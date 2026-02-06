import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from rag_pipeline.config import MIN_TOKEN_OVERLAP, HALLUCINATION_THRESHOLD, RF_MODEL_PATH
import joblib, os
from rag_pipeline.vectore_store import embedder

if os.path.exists(RF_MODEL_PATH):
    rf_model = joblib.load(RF_MODEL_PATH)
else:
    rf_model = None

def token_overlap_ratio(answer, context):
    answer_tokens = set(answer.lower().split())
    context_tokens = set(context.lower().split())
    if not answer_tokens:
        return 0.0
    return len(answer_tokens & context_tokens) / len(answer_tokens)

def detect_hallucination(question, context, answer):
    result = {
        "is_hallucination": False,
        "score": 0.0,
        "reasons": []
    }

    overlap = token_overlap_ratio(answer, context)
    if overlap < MIN_TOKEN_OVERLAP:
        result["is_hallucination"] = True
        result["reasons"].append(f"Low overlap: {overlap:.2%}")

    if rf_model is not None:
        q_emb = embedder.encode(question)
        c_emb = embedder.encode(context)
        a_emb = embedder.encode(answer)

        features = np.array([
            cosine_similarity([q_emb], [c_emb])[0][0],
            cosine_similarity([a_emb], [c_emb])[0][0],
            cosine_similarity([q_emb], [a_emb])[0][0],
            overlap,
            len(context.split()),
            len(answer.split())
        ]).reshape(1, -1)

        prob = rf_model.predict_proba(features)[0][1]
        result["score"] = float(prob)

        if prob > HALLUCINATION_THRESHOLD:
            result["is_hallucination"] = True
            result["reasons"].append(f"RF score: {prob:.2%}")

    return result
