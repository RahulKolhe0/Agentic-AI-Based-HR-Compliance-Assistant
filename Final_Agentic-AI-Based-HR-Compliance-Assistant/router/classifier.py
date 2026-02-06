import requests

# FIX 32: Policy keywords (RAG-only, highest priority)
POLICY_KEYWORDS = {
    "policy", "posh", "dress code", "leave policy",
    "procedure", "procedures", "compliance", "rules", "regulations",
    "guidelines", "harassment", "maternity", "privilege leave",
    "casual leave", "sick leave policy", "annual leave",
    "probation", "termination", "resignation", "notice period",
    "code of conduct", "ethics", "prevention", "workplace"
}

# FIX 29: Employee data attributes (SQL-only, never RAG)
EMPLOYEE_DATA_ATTRIBUTES = {
    "salary", "monthly salary", "annual salary",
    "joining date", "date of joining",
    "work hours", "overtime", "overtime hours",
    "employee id", "employeeid", "employee name", "employeename",
    "manager", "manager code",
    "years at company", "years in role", "years in current role",
    "leave balance", "sick leaves", "sick leave",
    "performance rating", "compliance risk"
}

# FIX 33: Aggregate keywords (SQL-only)
AGGREGATE_KEYWORDS = {
    "how many", "total number", "count of", "total employees",
    "number of employees", "all employees", "total", "sum of",
    "average", "exceeded"
}

# FIX 36: Ranking keywords (SQL-only, no RAG needed)
RANKING_KEYWORDS = {
    "highest", "lowest", "most", "least", "top", "bottom",
    "maximum", "minimum", "best", "worst", "greatest", "smallest"
}

def llm_intent_classifier(question: str):
    
    q_lower = question.lower()
    
    # --------------------------------------------------
    # FIX 32: Policy questions → RAG only (HIGHEST PRIORITY)
    # --------------------------------------------------
    if any(kw in q_lower for kw in POLICY_KEYWORDS):
        return {"rag"}
    
    # --------------------------------------------------
    # FIX 36: Ranking queries → SQL only
    # --------------------------------------------------
    if any(kw in q_lower for kw in RANKING_KEYWORDS):
        # Ranking queries are pure analytics, no policy needed
        return {"sql"}
    
    # --------------------------------------------------
    # NEW: Remaining/Left/Balance queries → needs BOTH
    # --------------------------------------------------
    # Pattern: "how many sick leaves left for employee X"
    # Needs: policy limit (RAG) + employee data (SQL)
    remaining_keywords = ["left", "remaining", "available", "balance"]
    has_remaining = any(kw in q_lower for kw in remaining_keywords)
    
    if has_remaining and any(leave in q_lower for leave in ["leave", "leaves", "sick", "casual", "privilege"]):
        # This needs policy limit AND employee data
        return {"sql"}  # Will be caught by dependency detector as sql_depends_on_rag
    
    # --------------------------------------------------
    # FIX 33: Aggregate queries → SQL only
    # --------------------------------------------------
    if any(kw in q_lower for kw in AGGREGATE_KEYWORDS):
        # If also mentions policy/documents → needs both
        if "policy" in q_lower or "according to" in q_lower or "as per" in q_lower:
            return {"rag", "sql"}
        return {"sql"}
    
    # --------------------------------------------------
    # FIX 29: Employee data + entity → SQL only
    # --------------------------------------------------
    has_employee_data = any(attr in q_lower for attr in EMPLOYEE_DATA_ATTRIBUTES)
    has_entity_reference = any(
        keyword in q_lower 
        for keyword in ["priya", "rakesh", "shweta", "employee id", "id is", "whose id", "with id"]
    )
    
    # Pure employee data lookup → SQL only
    if has_employee_data and has_entity_reference:
        return {"sql"}

    # --------------------------------------------------
    # LLM classification fallback
    # --------------------------------------------------
    prompt = f"""
You are an HR compliance intent classifier.

Classify the user question into one or more intents:

Intents:
- greet → greetings like hi/hello
- rag → HR policy/compliance/company rules questions
- sql → employee dataset/analytics/count/salary questions
- both → if both rag and sql are needed

IMPORTANT RULES (FIX 29, 32, 33):
- If question asks about POLICY, RULES, PROCEDURES → rag or both
- If question asks about SPECIFIC employee's data → sql ONLY
- If question asks aggregate analytics → sql or both (if policy-based)
- Examples:
  "What is posh policy?" → rag
  "What is dress code?" → rag
  "What is Priya's salary?" → sql
  "What is leave policy?" → rag
  "How many employees?" → sql
  "How many exceeded as per policy?" → both

Return ONLY one of these labels:
greet
rag
sql
both

Question: {question}
Label:
"""

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2:7b",
            "prompt": prompt,
            "stream": False
        }
    )

    label = r.json()["response"].strip().lower()

    if label not in {"greet", "rag", "sql", "both"}:
        # Defensive fallback
        return {"sql"}

    if label == "both":
        return {"rag", "sql"}

    return {label}
