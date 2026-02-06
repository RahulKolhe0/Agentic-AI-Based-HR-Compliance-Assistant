def rule_based_intent(question: str):
    q = question.lower()

    # Greeting
    if q in ["hi", "hello", "good morning", "hey"]:
        return {"greet"}

    # Strong SQL triggers
    if any(k in q for k in ["count", "average", "total employees"]):
        return {"sql"}

    return {"unknown"}
