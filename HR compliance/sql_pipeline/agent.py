from sql_pipeline.nl_to_sql import nl_to_sql
from sql_pipeline.sql_utils import clean_sql, fix_columns, validate_sql
from sql_pipeline.database import con
from sql_pipeline.llm import qwen
from security.rbac import enforce_rbac
from sql_pipeline.sql_utils import (
    clean_sql,
    fix_table_names,
    fix_columns,
    fix_clause_order,
    validate_sql,
    strip_sql_comments
)

def analytical_agent(question, user, sql_context: str =""):

    sql = nl_to_sql(question, sql_context)
    if not sql:
        return "❌ SQL not generated."
    
    print("\n📝 RAW SQL from LLM:", sql)

    sql = clean_sql(sql)
    print("🧹 After clean_sql:", sql)
    
    sql = fix_table_names(sql)
    print("🔧 After fix_table_names:", sql)
    
    sql = fix_columns(sql)
    print("📊 After fix_columns:", sql)
    
    sql = fix_clause_order(sql)
    print("⚡ After fix_clause_order:", sql)
    
    print("\n🧾 FINAL SQL:\n", sql)
    sql = strip_sql_comments(sql)
    try:
        validate_sql(sql)

        # ✅ RBAC FILTER APPLIED HERE
        sql = enforce_rbac(sql, user)

        print("\n🔐 SQL After RBAC Enforcement:\n", sql)

        df = con.execute(sql).fetchdf()

    except Exception as e:
        return f"❌ {e}"

    if df.empty:
        return "No data found."

    return qwen(f"""
User question: {question}
SQL result:
{df.to_string(index=False)}
Explain simply.
""")
