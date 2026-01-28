from sql_pipeline.database import TABLE_COLUMNS

def enforce_rbac(sql: str, user: dict):

    role = user["role"]
    emp_id = user["emp_id"]

    # Clean SQL
    sql = sql.rstrip().rstrip(";")
    sql_lower = sql.lower()

    # 🚫 Block write operations
    if role in ["employee", "manager"]:
        forbidden = ["delete", "update", "insert", "drop", "alter"]
        if any(word in sql_lower for word in forbidden):
            raise ValueError("❌ You are not allowed to modify employee data.")

    # 🔍 Detect table used
    table_used = None
    for table in TABLE_COLUMNS:
        if f" {table} " in f" {sql_lower} ":
            table_used = table
            break

    # 🟢 If no table detected → do nothing
    if not table_used:
        return sql + ";"

    cols = TABLE_COLUMNS[table_used]

    # 🟢 Users table → NO RBAC filter
    if table_used == "users":
        return sql + ";"

    # 🟢 Admin → full access
    if role == "admin":
        return sql + ";"

    # 🔧 Build safe conditions ONLY if columns exist
    conditions = []

    if "emp_id" in cols:
        conditions.append(f"emp_id = {emp_id}")

    if role == "manager" and "manager_id" in cols:
        conditions.append(f"manager_id = {emp_id}")

    if not conditions:
        return sql + ";"

    condition = " OR ".join(conditions)

    if " where " in sql_lower:
        sql += f" AND ({condition})"
    else:
        sql += f" WHERE ({condition})"

    return sql + ";"
