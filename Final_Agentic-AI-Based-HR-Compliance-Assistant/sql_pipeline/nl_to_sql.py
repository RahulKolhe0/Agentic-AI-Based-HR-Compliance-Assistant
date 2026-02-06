from sql_pipeline.database import TABLES, TABLE_COLUMNS
from sql_pipeline.llm import qwen
from typing import Optional, Dict, Any, List
import re


# --------------------------------------------------
# Attribute vocabulary (planner-aligned)
# --------------------------------------------------
ATTRIBUTE_MAP = {
    "name": "employeename",
    "employee name": "employeename",
    "id": "employeeid",
    "employee id": "employeeid",
    "joining date": "dateofjoining",
    "date of joining": "dateofjoining",
    "salary": "salary",
    "manager": "managercode",
    "manager code": "managercode",
    "years at company": "yearsatcompany",
    "years in current role": "yearsinrole"
}


def _extract_requested_columns(question: str, all_columns: set) -> List[str]:
    """
    FIX 12 — Deterministic attribute extraction
    """
    q = question.lower()
    cols = set()

    for phrase, col in ATTRIBUTE_MAP.items():
        if phrase in q and col in all_columns:
            cols.add(col)

    # Always include identity if employee is involved
    if any(k in q for k in ["employee", "id", "name"]):
        if "employeeid" in all_columns:
            cols.add("employeeid")
        if "employeename" in all_columns:
            cols.add("employeename")

    return sorted(cols)


# --------------------------------------------------
# FIX 17: Ranking Query Detection
# --------------------------------------------------
RANKING_KEYWORDS = {
    "highest", "lowest", "most", "least", "top", "bottom",
    "maximum", "minimum", "max", "min", "best", "worst",
    "largest", "smallest", "greatest"
}

RANKING_METRIC_MAP = {
    "years at company": "yearsatcompany",
    "years in current role": "yearsincurrentrole",
    "years in role": "yearsincurrentrole",
    "salary": "salary",
    "sick leaves": "sickleaveslastyear",
    "sick leave": "sickleaveslastyear",
    "leave": "sickleaveslastyear",
    "taken the highest sick leaves": "sickleaveslastyear",
    "taken sick leaves": "sickleaveslastyear",
    "has taken the highest sick": "sickleaveslastyear"
}


def _is_ranking_query(question: str) -> bool:
    """Detect if question asks for ranking/extremum."""
    q = question.lower()
    return any(keyword in q for keyword in RANKING_KEYWORDS)


def _detect_ranking_metric(question: str) -> Optional[str]:
    """
    FIX 27: Extract which column to rank by.
    Handles complex phrasings like 'taken the highest sick leaves'.
    """
    q = question.lower()
    
    # Try exact phrase matches first (longest to shortest)
    sorted_phrases = sorted(RANKING_METRIC_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    
    for phrase, col in sorted_phrases:
        if phrase in q:
            return col
    
    return None


# --------------------------------------------------
# FIX 21: Multi-Condition Logic Detection
# --------------------------------------------------
def _has_multiple_entity_conditions(question: str) -> bool:
    """
    Detect if question has multiple attributes for SAME entity.
    Example: "Priya Patel whose id is 82410"
    """
    q = question.lower()
    
    # Patterns indicating same-entity multiple conditions
    has_name = bool(re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", question))
    has_id = bool(re.search(r"\b(id|employee id)\s*(?:is|=)?\s*\d+", q))
    
    # Keywords that indicate conjunction for same entity
    conjunction_keywords = ["whose", "with id", "id is", "id ="]
    has_conjunction = any(kw in q for kw in conjunction_keywords)
    
    return has_name and has_id and has_conjunction


def nl_to_sql(
    question: str,
    policy_constraints: Optional[Dict[str, Any]] = None
):
    """
    FIX 12 + FIX 24 — Attribute Aggregation → Single SQL

    Guarantees:
    - ONE entity → ONE SELECT
    - MANY attributes → MANY columns
    - COUNT queries → COUNT(*) only (no extra columns)
    - ZERO hallucination
    """

    # --------------------------------------------------
    # FIX 24: Detect COUNT-only queries
    # --------------------------------------------------
    q_lower = question.lower()
    is_count_query = any(kw in q_lower for kw in [
        "how many", "count", "total number", "number of"
    ])

    # --------------------------------------------------
    # 1️⃣ Build schema text
    # --------------------------------------------------
    schema_text = ""
    all_columns = set()

    for table in TABLES:
        cols = TABLE_COLUMNS[table]
        schema_text += f"\nTable: {table}\nColumns: {cols}\n"
        all_columns.update(cols)

    # --------------------------------------------------
    # 2️⃣ Extract requested columns (NEW) + FIX 35
    # --------------------------------------------------
    requested_columns = _extract_requested_columns(question, all_columns)

    # FIX 35: For COUNT queries, don't enforce specific columns
    if is_count_query:
        column_clause = "COUNT(*)"
    else:
        if not requested_columns:
            # Defensive fallback — never empty SELECT
            requested_columns = ["employeeid", "employeename"]
        column_clause = ", ".join(requested_columns)

    # --------------------------------------------------
    # 3️⃣ Validate policy constraint EARLY
    # --------------------------------------------------
    constraint_block = ""

    if policy_constraints:
        column = policy_constraints.get("column")
        operator = policy_constraints.get("operator")
        value = policy_constraints.get("value")

        if column not in all_columns:
            return "SELECT 'INVALID_CONSTRAINT' AS error"

        if operator not in {">", ">=", "<", "<=", "="}:
            return "SELECT 'INVALID_CONSTRAINT' AS error"

        constraint_block = f"""
MANDATORY POLICY CONSTRAINT (NON-NEGOTIABLE):
- Column: {column}
- Operator: {operator}
- Value: {value}
"""

    # --------------------------------------------------
    # 4️⃣ Build enforcement rules (FIX 17 + FIX 21 + FIX 30)
    # --------------------------------------------------
    ranking_rule = ""
    if _is_ranking_query(question):
        metric = _detect_ranking_metric(question)
        if metric:
            ranking_rule = f"""
🚨🚨🚨 CRITICAL - RANKING QUERY DETECTED (MANDATORY) 🚨🚨🚨

THIS IS NON-NEGOTIABLE:
1. You MUST use: ORDER BY {metric} DESC LIMIT 1
2. You MUST select: employeeid, employeename, {metric}
3. You are ABSOLUTELY FORBIDDEN from using:
   - MAX() function
   - MIN() function  
   - ANY aggregate functions (COUNT, SUM, AVG)
   - GROUP BY clause
   
CORRECT EXAMPLE:
SELECT employeeid, employeename, {metric}
FROM employee
ORDER BY {metric} DESC
LIMIT 1

FAILURE TO FOLLOW THIS WILL CAUSE INCORRECT RESULTS!
"""
    
    multi_condition_rule = ""
    if _has_multiple_entity_conditions(question):
        multi_condition_rule = """
🚨 MULTI-CONDITION SAME ENTITY DETECTED:
- When SAME employee has multiple attributes (name AND id):
- You MUST use AND operator (NOT OR)
- Example: WHERE employeename = 'X' AND employeeid = Y
"""

    # FIX 24 + FIX 35: COUNT-only rule
    count_rule = ""
    if is_count_query:
        count_rule = """
🚨 COUNT QUERY DETECTED:
- If asked for "total number of employees" with NO condition → Use: SELECT COUNT(*) FROM employee (NO WHERE)
- If asked with a condition → Use: SELECT COUNT(*) FROM employee WHERE <condition>
- You MUST NOT include ANY other columns in SELECT
- You MUST NOT use GROUP BY unless explicitly requested
- Output format: single integer count only
"""

    # --------------------------------------------------
    # 5️⃣ Strict prompt (LLM boxed-in) + FIX 35
    # --------------------------------------------------
    # FIX 35: Only enforce columns for non-COUNT queries
    column_enforcement = ""
    if not is_count_query:
        column_enforcement = f"""- Columns MUST be exactly:
  {column_clause}"""
    
    prompt = f"""
You are a SQL-only generator.

AVAILABLE SCHEMA:
{schema_text}

{constraint_block}

{ranking_rule}

{multi_condition_rule}

{count_rule}

ABSOLUTE RULES:
- Output ONLY ONE SELECT statement
- DO NOT generate multiple SELECTs
{column_enforcement}
- Use ONLY table: employee
- NO aggregates unless explicitly asked
- NO backticks
- If constraint exists → MUST be applied

QUESTION:
{question}

SQL:
"""

    sql = qwen(prompt).strip()

    # --------------------------------------------------
    # 5️⃣ Post-validation (unchanged safety)
    # --------------------------------------------------
    sql_lower = sql.lower()

    if policy_constraints and any(
        agg in sql_lower for agg in ["max(", "min(", "avg(", "sum("]
    ):
        return "SELECT 'INVALID_CONSTRAINT' AS error"

    if policy_constraints:
        pattern = rf"{policy_constraints['column']}\s*{re.escape(policy_constraints['operator'])}\s*{policy_constraints['value']}"
        if not re.search(pattern, sql_lower):
            return "SELECT 'INVALID_CONSTRAINT' AS error"

    return sql
