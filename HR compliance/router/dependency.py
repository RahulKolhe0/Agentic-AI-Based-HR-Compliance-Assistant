import re

def detect_dependency(question: str) -> str:
    """
    Decide pipeline execution order:

    Returns:
        "sql_depends_on_rag"
        "rag_depends_on_sql"
        "independent"
    """

    q = question.lower()

    # -----------------------------
    # SQL depends on RAG
    # -----------------------------
    # Policy threshold needed first
    if any(x in q for x in [
        "allowed", "maximum", "limit", "as per policy",
        "exceeded", "more than allowed", "above permitted"
    ]):
        if any(y in q for y in [
            "how many employees", "count employees", "employees exceeded"
        ]):
            return "sql_depends_on_rag"

    # -----------------------------
    # RAG depends on SQL
    # -----------------------------
    # Data summary needed first
    if any(x in q for x in [
        "based on employee data", "according to dataset",
        "attrition rate", "performance trend", "analytics"
    ]):
        return "rag_depends_on_sql"

    # -----------------------------
    # Default: independent
    # -----------------------------
    return "independent"
