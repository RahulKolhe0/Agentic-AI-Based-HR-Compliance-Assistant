import re

AGGREGATE_KEYWORDS = ["count(", "max(", "min(", "avg(", "sum("]
RANKING_KEYWORDS = ["order by", "limit"]


def _is_aggregate_query(sql_lower: str) -> bool:
    return any(k in sql_lower for k in AGGREGATE_KEYWORDS)


def _is_ranking_query(sql_lower: str) -> bool:
    return any(k in sql_lower for k in RANKING_KEYWORDS)


def _already_scoped_to_employee(sql_lower: str) -> bool:
    """
    Explicit employee scoping already present.
    """
    return bool(
        re.search(r"\bemployeeid\s*=\s*\d+", sql_lower)
        or re.search(r"\bemployeename\s*=\s*['\"]", sql_lower)
    )


def _references_employee_entity(sql_lower: str) -> bool:
    """
    FIX 16 — Detect whether SQL explicitly references an employee.
    RBAC must NEVER invent this context.
    """
    return bool(
        re.search(r"\bemployeeid\b", sql_lower)
        or re.search(r"\bemployeename\b", sql_lower)
    )


def _is_single_employee_lookup(sql_lower: str) -> bool:
    """
    Detect personal (non-aggregate, non-ranking) queries.
    """
    return (
        " from employee" in sql_lower
        and not _is_aggregate_query(sql_lower)
        and not _is_ranking_query(sql_lower)
    )



def enforce_rbac(sql: str, user: dict, has_policy_constraint: bool = False) -> str:
    """
    FINAL RBAC LOGIC — FIX 18

    Principles:
    - Admin: full access
    - Aggregates / rankings: global access
    - Row-level restriction ONLY if:
        • query explicitly references an employee entity
        • and is a personal lookup
    - RBAC NEVER invents employee scope
    - FIX 18: RBAC NEVER touches policy-constrained queries
    """

    role = user.get("role")
    emp_id = user.get("emp_id")

    if role is None or emp_id is None:
        raise ValueError("❌ Invalid user context for RBAC.")

    # --------------------------------------------------
    # 🛡️ FIX 18 — Policy Constraint Guard (CRITICAL)
    # --------------------------------------------------
    if has_policy_constraint:
        # Policy constraints already define scope
        # RBAC must NOT inject additional WHERE clauses
        print("🛡️ Policy-constrained query → RBAC bypassed")
        return sql

    sql_lower = sql.lower()

    # --------------------------------------------------
    # 🚫 Block mutations (ALWAYS)
    # --------------------------------------------------
    forbidden = ["delete", "update", "insert", "drop", "alter", "truncate"]
    if any(word in sql_lower for word in forbidden):
        raise ValueError("❌ You are not allowed to modify employee data.")

    # --------------------------------------------------
    # ✅ Admin → full access
    # --------------------------------------------------
    if role == "admin":
        return sql

    # --------------------------------------------------
    # ✅ Global analytics → DO NOT TOUCH
    # --------------------------------------------------
    if _is_aggregate_query(sql_lower) or _is_ranking_query(sql_lower):
        return sql

    # --------------------------------------------------
    # ✅ Already scoped → DO NOT TOUCH
    # --------------------------------------------------
    if _already_scoped_to_employee(sql_lower):
        return sql

    # --------------------------------------------------
    # 🧠 FIX 16 — NO ENTITY → NO RBAC MUTATION
    # --------------------------------------------------
    if not _references_employee_entity(sql_lower):
        # RBAC refuses to guess scope
        return sql

    # --------------------------------------------------
    # 🔐 Apply RBAC ONLY for explicit personal lookups
    # --------------------------------------------------
    if not _is_single_employee_lookup(sql_lower):
        return sql

    # Detect alias if present
    alias_match = re.search(r"\bfrom\s+employee\s+(?:as\s+)?(\w+)", sql_lower)
    if alias_match:
        alias = alias_match.group(1)
        condition = f"{alias}.employeeid = {emp_id}"
    else:
        condition = f"employeeid = {emp_id}"

    # Preserve ORDER BY / LIMIT safely
    order_limit_match = re.search(r"\b(order by|limit)\b", sql_lower)
    if order_limit_match:
        base_sql = sql[:order_limit_match.start()]
        tail_sql = sql[order_limit_match.start():]
    else:
        base_sql = sql
        tail_sql = ""

    # Append WHERE safely
    if re.search(r"\bwhere\b", base_sql, re.IGNORECASE):
        base_sql = base_sql.strip() + f" AND {condition}"
    else:
        base_sql = base_sql.strip() + f" WHERE {condition}"

    return f"{base_sql} {tail_sql}".strip()
