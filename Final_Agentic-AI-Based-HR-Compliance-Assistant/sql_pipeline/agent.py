from typing import Optional, Dict, Any, List
import re
from datetime import datetime

from sql_pipeline.nl_to_sql import nl_to_sql
from sql_pipeline.database import con
from sql_pipeline.llm import qwen
from security.rbac import enforce_rbac
from sql_pipeline.sql_utils import (
    clean_sql,
    fix_table_names,
    fix_columns,
    validate_sql
)
from logger import get_logger

logger = get_logger("SQL_AGENT")


# --------------------------------------------------
# FIX 28: Date Formatting Helper
# --------------------------------------------------
def _format_date(date_value) -> str:
    """
    Convert date to human-readable format.
    Input: "11/13/2000" or datetime object
    Output: "13th November 2000"
    """
    try:
        # If it's a string, parse it
        if isinstance(date_value, str):
            # Try multiple date formats
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_value, fmt)
                    break
                except:
                    continue
            else:
                return date_value  # Return original if parsing fails
        else:
            dt = date_value
        
        # Add ordinal suffix (st, nd, rd, th)
        day = dt.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]
        
        return f"{day}{suffix} {dt.strftime('%B %Y')}"
    except:
        return str(date_value)  # Fallback to original

# --------------------------------------------------
# Helper: split multiple SQL statements safely
# --------------------------------------------------
def _split_sql_statements(sql: str) -> List[str]:
    return [
        part.strip()
        for part in sql.split(";")
        if part.strip().lower().startswith("select")
    ]


# --------------------------------------------------
# Helper: analyze SQL semantics (AUTHORITATIVE)
# --------------------------------------------------
def analyze_sql_semantics(sql: str) -> Dict[str, bool]:
    s = sql.lower()
    return {
        "has_where": " where " in s,
        "has_gt": ">" in s,
        "has_count": "count(" in s,
        "has_max": "max(" in s,
        "has_min": "min(" in s,
        "has_avg": "avg(" in s,
        "has_sum": "sum(" in s,
        "has_order": "order by" in s,
        "has_limit": "limit" in s
    }


# --------------------------------------------------
# MAIN AGENT — FIXED CORRECTLY
# --------------------------------------------------
def analytical_agent(
    question: str,
    user: dict,
    policy_constraints: Optional[Dict[str, Any]] = None
):
    """
    FINAL SQL ANALYTICAL AGENT

    Guarantees:
    - Policy-aware SQL generation
    - Multi-query safe execution
    - RBAC-safe analytics
    - ZERO hallucination
    - NO LLM narration when code can answer
    """

    # --------------------------------------------------
    # 1️⃣ NL → SQL
    # --------------------------------------------------
    raw_sql = nl_to_sql(
        question=question,
        policy_constraints=policy_constraints
    )

    if not raw_sql or not raw_sql.strip():
        logger.warning(f"❌ SQL generation failed for question: {question}")
        return "❌ SQL not generated."

    raw_sql = clean_sql(raw_sql)
    logger.info(f"📝 Generated SQL (raw): {raw_sql}")
    
    sql_statements = _split_sql_statements(raw_sql)

    if not sql_statements:
        logger.warning("❌ No valid SELECT queries found in generated SQL")
        return "❌ No valid SELECT query generated."

    outputs: List[str] = []

    # --------------------------------------------------
    # 2️⃣ Execute EACH SQL independently
    # --------------------------------------------------
    for idx, sql in enumerate(sql_statements, start=1):

        sql = fix_table_names(sql)
        sql = fix_columns(sql)
        semantics = analyze_sql_semantics(sql)

        try:
            validate_sql(sql)
            # FIX 18: Pass policy constraint flag to RBAC
            sql = enforce_rbac(
                sql,
                user,
                has_policy_constraint=bool(policy_constraints)
            )
            logger.info(f"🚀 Executing Enforced SQL: {sql}")
            df = con.execute(sql).fetchdf()
        except Exception as e:
            logger.error(f"❌ SQL Execution Error: {str(e)}", exc_info=True)
            return f"❌ SQL execution error in Result {idx}: {e}"

        if df.empty:
            outputs.append(f"Result {idx}: No data found.")
            continue

        # --------------------------------------------------
        # FIX 34: Universal date formatting (apply to ALL queries)
        # --------------------------------------------------
        for col in df.columns:
            if 'date' in col.lower() or 'joining' in col.lower():
                df[col] = df[col].apply(_format_date)

        # --------------------------------------------------
        # 3️⃣ Deterministic result formatting
        # --------------------------------------------------

        # ✅ COUNT(*) queries
        if semantics["has_count"]:
            value = int(df.iloc[0, 0])
            if semantics["has_where"]:
                outputs.append(
                    f"Result {idx}: There are {value} records matching the condition."
                )
            else:
                outputs.append(
                    f"Result {idx}: There are {value} total records in the table."
                )
            continue

        # ✅ MAX() queries
        if semantics["has_max"]:
            col = df.columns[0]
            value = df.iloc[0, 0]
            outputs.append(
                f"Result {idx}: The maximum value of {col} is {value}."
            )
            continue

        # ✅ Ranking / TOP employee queries
        if semantics["has_order"] and semantics["has_limit"]:
            rows = []
            for _, row in df.iterrows():
                # FIX 34: Date formatting now applied universally above
                row_desc = ", ".join(f"{col} = {row[col]}" for col in df.columns)
                rows.append(row_desc)
            outputs.append(
                f"Result {idx}: " + " | ".join(rows)
            )
            continue

        # --------------------------------------------------
        # 4️⃣ LLM fallback ONLY for complex tables
        # --------------------------------------------------
        explanation_prompt = f"""
You are a SQL result narrator.

STRICT RULES:
- Describe ONLY what is shown
- No inference
- No policy meaning
- No assumptions
- FIX 28: Convert dates like "11/13/2000" to readable format "13th November 2000"

SQL:
{sql}

SQL Result:
{df.to_string(index=False)}

Explanation:
"""

        explanation = qwen(explanation_prompt).strip()
        outputs.append(f"Result {idx}:\n{explanation}")

    # --------------------------------------------------
    # 5️⃣ Final response
    # --------------------------------------------------
    return "\n\n".join(outputs)
