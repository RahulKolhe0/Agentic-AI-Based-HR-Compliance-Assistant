from rag_pipeline.app import app as rag_app
from sql_pipeline.agent import analytical_agent
import re
from typing import Optional, Dict, Any


# -----------------------------
# Run RAG Pipeline
# -----------------------------
def run_rag(question: str) -> str:
    rag_state = rag_app.invoke({
        "question": question,
        "retrieved": [],
        "reranked": [],
        "categories": {
            "mandatory": [],
            "restriction": [],
            "penalty": [],
            "procedure": [],
            "general": []
        },
        "context": "",
        "answer": "",
        "sources": set(),
        "hallucination_check": {},
        "retry_count": 0
    })

    return rag_state.get("final", rag_state.get("answer", "No response"))


# -----------------------------
# Run SQL Pipeline (RBAC enforced)
# -----------------------------
def run_sql(
    question: str,
    user: dict,
    policy_constraints: Optional[Dict[str, Any]] = None
):
    """
    NOTE:
    - policy_constraints are OPTIONAL
    - Fix 1 only transports them safely
    - Fix 5 will enforce them
    """

    if user is None:
        return "❌ Unauthorized SQL access (user missing)."

    return analytical_agent(
        question=question,
        user=user,
        policy_constraints=policy_constraints
    )


# -----------------------------
# Dependency Execution
# -----------------------------
def sql_depends_on_rag(question: str, user: dict):
    """
    FIX 1 + FIX 23 + NEW: Remaining Leaves Calculation
    
    Handles two patterns:
    1. "Who exceeded?" → WHERE sick_leaves > policy_limit
    2. "How many left?" → policy_limit - employee_sick_leaves
    
    Guarantees:
    - RAG extracts policy facts
    - Numeric limits become STRUCTURED constraints or calculations
    - SQL never sees policy text
    - SQL never invents thresholds
    """
    
    q_lower = question.lower()
    
    # ========================================
    # NEW: Detect "remaining/left" calculation pattern
    # ========================================
    is_remaining_query = any(kw in q_lower for kw in ["left", "remaining", "available", "balance"])
    is_exceeded_query = any(kw in q_lower for kw in ["exceeded", "more than allowed", "above allowed"])
    
    # ========================================
    # Enhanced RAG query for better retrieval
    # ========================================
    enhanced_question = question
    
    if any(kw in q_lower for kw in ["sick leave", "sick days", "casual leave", "privilege leave", "leave"]):
        leave_type = None
        if "sick" in q_lower:
            leave_type = "sick leave"
        elif "casual" in q_lower:
            leave_type = "casual leave"
        elif "privilege" in q_lower:
            leave_type = "privilege leave"
        
        enhanced_question = (
            f"{question}\n\n"
            f"Context: Looking for {leave_type or 'leave'} policy, maximum allowed {leave_type or 'leave'} days, "
            f"or {leave_type or 'leave'} limit per year."
        )
    
    # 1️⃣ Run RAG to get policy limit
    rag_answer = run_rag(enhanced_question)
    
    # 2️⃣ Extract numeric policy value
    policy_value = extract_numeric_policy_value(rag_answer)
    
    if policy_value is None:
        return (
            "📘 Policy Reference:\n"
            f"{rag_answer}\n\n"
            "❌ Unable to extract a numeric policy threshold required for analytics."
        )
    
    # ========================================
    # NEW: REMAINING/LEFT Calculation Branch
    # ========================================
    if is_remaining_query and not is_exceeded_query:
        # This needs: policy_limit - employee_used = remaining
        # Example: "how many sick leaves left for Ashish Das whose id is 2002?"
        
        # Extract employee info from question
        import re
        emp_id_match = re.search(r'\b(?:id|employee\s*id)\s*(?:is|=)?\s*(\d+)', q_lower)
        emp_name_match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', question)
        
        if not emp_id_match and not emp_name_match:
            return "❌ Please specify which employee you're asking about."
        
        # Build SQL to get employee's used leaves
        from sql_pipeline.database import con
        
        if emp_id_match:
            emp_id = emp_id_match.group(1)
            sql = f"SELECT employeeid, employeename, sickleaveslastyear FROM employee WHERE employeeid = {emp_id}"
        else:
            emp_name = emp_name_match.group(1)
            sql = f"SELECT employeeid, employeename, sickleaveslastyear FROM employee WHERE employeename = '{emp_name}'"
        
        try:
            df = con.execute(sql).fetchdf()
            
            if df.empty:
                return "❌ Employee not found in database."
            
            emp_id = df.iloc[0]['employeeid']
            emp_name = df.iloc[0]['employeename']
            used_leaves = int(df.iloc[0]['sickleaveslastyear'])
            remaining_leaves = policy_value - used_leaves
            
            return (
                "📘 Policy Reference:\n"
                f"{rag_answer}\n\n"
                "📊 Calculation:\n"
                f"Employee: {emp_name} (ID: {emp_id})\n"
                f"Maximum allowed sick leaves (as per policy): {policy_value} days\n"
                f"Sick leaves taken last year: {used_leaves} days\n"
                f"**Remaining sick leaves: {remaining_leaves} days**"
            )
        
        except Exception as e:
            return f"❌ Error calculating remaining leaves: {e}"
    
    # ========================================
    # EXCEEDED Query Branch (original logic)
    # ========================================
    # 3️⃣ Build machine-readable policy constraint
    policy_constraints = {
        "kind": "numeric_threshold",
        "source": "policy",
        "column": "sickleaveslastyear",
        "operator": ">",
        "value": policy_value
    }
    
    # 4️⃣ Execute SQL with structured constraints
    sql_answer = run_sql(
        question=question,
        user=user,
        policy_constraints=policy_constraints
    )
    
    # 5️⃣ Strict separation of responsibility
    return (
        "📘 Policy Reference:\n"
        f"{rag_answer}\n\n"
        "📊 Data Derived From Policy:\n"
        f"{sql_answer}"
    )


def rag_depends_on_sql(question: str, user: dict):
    """
    SQL → RAG
    (unchanged in Fix 1)
    """

    sql_answer = run_sql(question, user)

    combined_question = f"""
Employee Data Result:
{sql_answer}

Now answer using policy documents:
{question}
"""

    rag_answer = run_rag(combined_question)

    return f"{sql_answer}\n\n📘 Policy Explanation:\n{rag_answer}"


# -----------------------------
# Independent Execution
# -----------------------------
def independent_run(question: str, intents: set, user: dict):

    outputs = []

    if "rag" in intents:
        outputs.append("📘 Policy Answer:\n" + run_rag(question))

    if "sql" in intents:
        outputs.append("📊 Data Answer:\n" + run_sql(question, user))

    return "\n\n".join(outputs)


# -----------------------------
# Policy Value Extraction (FIX 26)
# -----------------------------
def extract_numeric_policy_value(text: str) -> Optional[int]:
    """
    FIX 26: Robust numeric extraction from various RAG response formats.
    
    Handles:
    - "The maximum is 12 days"
    - "per year is 12"
    - "allowed: 12"
    - "limit of 12 days"
    - "12 days maximum"
    """
    
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Try multiple patterns in order of specificity
    patterns = [
        r"(?:is|:)\s*(\d+)\s*(?:days?)?",           # "is 12" or "is 12 days"
        r"(\d+)\s*days?",                            # "12 days"
        r"maximum.*?(\d+)",                          # "maximum ... 12"
        r"limit.*?(\d+)",                            # "limit ... 12"
        r"allowed.*?(\d+)",                          # "allowed ... 12"
        r"up\s*to\s*(\d+)",                          # "up to 12"
        r"(\d+)\s*(?:sick\s*)?leave",               # "12 sick leave"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            value = int(match.group(1))
            # Sanity check: policy values should be reasonable (1-365)
            if 1 <= value <= 365:
                return value
    
    return None
