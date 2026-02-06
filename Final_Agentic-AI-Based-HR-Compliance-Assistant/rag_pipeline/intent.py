def detect_intent(question: str) -> str:
    q = question.lower().strip()

    if any(k in q for k in ["how to", "procedure", "process", "steps"]):
        return "procedure"
    if any(k in q for k in ["can i", "is it allowed", "allowed", "permitted"]):
        return "permission"
    if any(k in q for k in ["penalty", "consequence", "violate", "disciplinary"]):
        return "penalty"
    if q.startswith("what is") or q.startswith("define"):
        return "definition"

    return "general"
