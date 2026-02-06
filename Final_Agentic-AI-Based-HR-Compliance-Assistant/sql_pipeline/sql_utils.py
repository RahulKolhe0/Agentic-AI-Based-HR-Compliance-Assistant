import re
from rapidfuzz import process
from sqlglot import parse_one, exp

from sql_pipeline.database import TABLES, TABLE_COLUMNS


# -------------------------------
# Strip Markdown SQL Formatting
# -------------------------------
def clean_sql(sql: str):
    return (
        sql.replace("```sql", "")
           .replace("```", "")
           .replace("`", "")   # 🔥 CRITICAL FIX
           .strip()
    )



# -------------------------------
# Fix Wrong Table Names
# Example: employees → employee
# -------------------------------
def fix_table_names(sql: str):

    for token in re.findall(r"[a-zA-Z_]+", sql):

        # If token is already a valid table, skip
        if token.lower() in TABLES:
            continue

        # Only fix tokens that look like table references
        if token.lower() in ["employees", "employee", "staff", "workers"]:

            match = process.extractOne(token, TABLES)

            if match is None:
                continue

            best, score, _ = match

            if score > 80:
                print(f"🔧 Fixed table name: {token} → {best}")
                sql = sql.replace(token, best)

    return sql


# -------------------------------
# Fix Wrong Column Names (Multi-table)
# -------------------------------
def fix_columns(sql: str):
    all_columns = set()
    for cols in TABLE_COLUMNS.values():
        all_columns.update(cols)

    if not all_columns:
        return sql

    tokens = set(re.findall(r"\b[a-zA-Z_]+\b", sql))

    for token in tokens:
        token_lower = token.lower()

        if token_lower in all_columns:
            continue

        match = process.extractOne(token_lower, all_columns)
        if not match:
            continue

        best, score, _ = match

        if score > 90:
            print(f"🔧 Fixed column: {token} → {best}")
            sql = re.sub(rf"\b{token}\b", best, sql)

    return sql


# -------------------------------
# Validate SQL Safety
# -------------------------------
def validate_sql(sql: str):

    tree = parse_one(sql, dialect="duckdb")

    for node in tree.walk():

        # Block unsafe queries
        if isinstance(node, (exp.Drop, exp.Delete, exp.Update,
                             exp.Insert, exp.Alter)):
            raise ValueError("❌ Unsafe SQL detected!")

    return sql
