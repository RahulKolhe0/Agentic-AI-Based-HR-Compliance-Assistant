print("🔥🔥🔥 NEW 2-PHASE NL_TO_SQL LOADED 🔥🔥🔥")

from sql_pipeline.database import TABLES, TABLE_COLUMNS
from sql_pipeline.llm import qwen

# ------------------------------------------------------------------
# NL → SQL (2-PHASE, STRICT MODE)
#
# WHY THIS EXISTS:
# - Phase 1 strictly selects ONE valid table to prevent hallucinated tables
# - Phase 2 generates SQL that is:
#     • schema-bound (no invented columns)
#     • policy-safe (policy numbers come ONLY from sql_context)
#     • analytics-correct (ORDER BY + LIMIT for extremum queries)
#
# DESIGN PRINCIPLES:
# - LLM is NOT trusted with schema or policy inference
# - All authority flows:
#       Policy PDFs → RAG → sql_context → SQL literals
# - SQL must NEVER reference policy documents, PDFs, or derived tables
#
# RESULT:
# - Deterministic SQL
# - No hidden joins
# - No invented limits
# - No semantic drift between policy and data
# ------------------------------------------------------------------


def nl_to_sql(question: str, sql_context: str = ""):

    print("🔥 USING NEW NL_TO_SQL LOGIC")

    # ==========================================================
    # PHASE 1 — TABLE SELECTION (QUESTION ONLY)
    # ==========================================================
    tables_list = ", ".join(TABLES)

    table_prompt = f"""
You are a database router.

Select EXACTLY ONE table name from below.
Return ONLY the table name or NONE.

AVAILABLE TABLES:
{tables_list}

RULES:
- Output ONE word only
- Do NOT explain
- Do NOT invent table names

Question:
{question}

Answer:
"""

    selected_table = qwen(table_prompt).strip().lower()

    if selected_table == "none":
        return None

    if selected_table not in TABLES:
        raise ValueError(
            f"Invalid table selected by LLM: '{selected_table}'. "
            f"Allowed tables: {TABLES}"
        )

    # ==========================================================
    # PHASE 2 — SQL GENERATION (QUESTION + POLICY CONTEXT)
    # ==========================================================
    columns = TABLE_COLUMNS[selected_table]
    columns_str = ", ".join(columns)

    sql_prompt = f"""
You are a STRICT SQL generator for DuckDB.

TABLE: {selected_table}
ALLOWED COLUMNS:
{columns_str}

CONTEXT (policy-derived facts, if any):
{sql_context}

CRITICAL RULES (MANDATORY):
1. Use ONLY table "{selected_table}"
2. Use ONLY the listed columns
3. NEVER invent tables or columns (e.g. policies, rules, limits, documents)
4. NEVER reference PDFs, policy text, or policy tables
5. NEVER use subqueries to derive policy limits
6. If numeric policy limits are provided in CONTEXT:
   - Use them DIRECTLY as literal values
   - Do NOT compute or infer new limits
7. For highest / lowest / top / most / least:
   - Use ORDER BY + LIMIT 1
   - Do NOT mix aggregates with non-aggregated columns
8. Use COUNT(*) for counting rows
9. Output ONLY valid SQL (no markdown, no explanation)

QUESTION:
{question}

SQL:
"""

    return qwen(sql_prompt).strip()