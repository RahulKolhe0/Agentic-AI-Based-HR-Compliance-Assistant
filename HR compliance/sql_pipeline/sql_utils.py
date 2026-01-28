import re
from rapidfuzz import process
from sqlglot import parse_one, exp

from sql_pipeline.database import TABLES, TABLE_COLUMNS


# -------------------------------
# Strip Markdown SQL Formatting
# -------------------------------
def strip_sql_comments(sql: str):
    # Remove single-line comments
    return re.sub(r"--.*", "", sql).strip()

def clean_sql(sql: str):
    return sql.replace("```sql", "").replace("```", "").strip()

def fix_clause_order(sql: str):

    sql_lower = sql.lower()

    if " where " in sql_lower and " order by " in sql_lower:
        where_idx = sql_lower.index(" where ")
        order_idx = sql_lower.index(" order by ")

        if order_idx < where_idx:
            before_order = sql[:order_idx]
            order_part = sql[order_idx:where_idx]
            where_part = sql[where_idx:]

            sql = before_order + where_part + order_part

    return sql

# -------------------------------
# Fix Wrong Table Names
# Example: employees → employee
# -------------------------------
def fix_table_names(sql: str):
    """
    Fix ONLY the table name in FROM / JOIN clauses.
    Never touch column names.
    """

    # Fix FROM clause
    from_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
    if from_match:
        used_table = from_match.group(1)

        if used_table.lower() not in TABLES:
            match = process.extractOne(used_table.lower(), TABLES)
            if match:
                best, score, _ = match
                if score > 70:
                    print(f"🔧 Fixed FROM table: {used_table} → {best}")
                    sql = re.sub(
                        r'\bFROM\s+' + re.escape(used_table),
                        f'FROM {best}',
                        sql,
                        flags=re.IGNORECASE
                    )

    # Fix JOIN clauses (future-proof)
    for join_match in re.finditer(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE):
        used_table = join_match.group(1)

        if used_table.lower() not in TABLES:
            match = process.extractOne(used_table.lower(), TABLES)
            if match:
                best, score, _ = match
                if score > 70:
                    print(f"🔧 Fixed JOIN table: {used_table} → {best}")
                    sql = re.sub(
                        r'\bJOIN\s+' + re.escape(used_table),
                        f'JOIN {best}',
                        sql,
                        flags=re.IGNORECASE
                    )

    return sql



# -------------------------------
# Fix Wrong Column Names (Multi-table)
# -------------------------------
def fix_columns(sql: str):
    """
    Fix column names WITHOUT touching table names.
    """

    # -----------------------------
    # Identify table names used
    # -----------------------------
    tables_in_query = set()

    for m in re.finditer(r'\bFROM\s+(\w+)', sql, re.IGNORECASE):
        tables_in_query.add(m.group(1).lower())

    for m in re.finditer(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE):
        tables_in_query.add(m.group(1).lower())

    # -----------------------------
    # Collect all known columns
    # -----------------------------
    all_columns = []
    for cols in TABLE_COLUMNS.values():
        all_columns.extend(cols)

    if not all_columns:
        return sql

    # -----------------------------
    # Fix only NON-table tokens
    # -----------------------------
    for token in re.findall(r"[a-zA-Z_]+", sql):
        token_lower = token.lower()

        # 🚫 Skip table names
        if token_lower in tables_in_query:
            continue

        # 🚫 Skip SQL keywords
        if token_lower in {
            "select", "from", "where", "order", "by", "limit",
            "and", "or", "count", "distinct", "avg", "sum",
            "max", "min", "group", "having", "join", "on", "as"
        }:
            continue

        # 🚫 Skip valid columns
        if token_lower in all_columns:
            continue

        # Fuzzy match columns
        match = process.extractOne(token_lower, all_columns)
        if match:
            best, score, _ = match
            if score > 85:
                print(f"🔧 Fixed column: {token} → {best}")
                sql = re.sub(rf'\b{token}\b', best, sql)

    return sql

# -------------------------------
# Validate SQL Safety
# -------------------------------
def validate_sql(sql: str):

    # 🚨 Reject repeated identifiers (LLM runaway protection)
    # Example caught: employeenameemployeenameemployeename
    if re.search(r"(\b\w+\b)\1{2,}", sql.lower()):
        raise ValueError("❌ Invalid SQL: repeated identifier detected.")

    # 🚨 Check for valid table names
    sql_lower = sql.lower()
    for table in TABLES:
        if table in sql_lower:
            break  # At least one valid table found
    else:
        # No valid table found, try to extract what was used
        # Look for FROM clause
        from_match = re.search(r'\bfrom\s+(\w+)', sql_lower)
        if from_match:
            used_table = from_match.group(1)
            if used_table not in TABLES:
                # Suggest the closest match
                from rapidfuzz import process
                match = process.extractOne(used_table, TABLES)
                if match:
                    best_match, score, _ = match
                    raise ValueError(f"❌ Invalid table '{used_table}'. Did you mean '{best_match}'?")
                else:
                    raise ValueError(f"❌ Invalid table '{used_table}'. Available tables: {', '.join(TABLES)}")

    # Parse SQL safely
    tree = parse_one(sql)

    for node in tree.walk():

        # Block unsafe queries
        if isinstance(node, (
            exp.Drop,
            exp.Delete,
            exp.Update,
            exp.Insert,
            exp.Alter
        )):
            raise ValueError("❌ Unsafe SQL detected!")

    return sql
