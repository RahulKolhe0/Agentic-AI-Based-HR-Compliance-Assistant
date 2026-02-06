from router.graph import router_app
from memory.long_term import init_db

init_db()

print(">>> MAIN ROUTER STARTED <<<")

print("\n" + "="*80)
print("🤖 HR COMPLIANCE SMART ASSISTANT")
print("="*80)
print("Type 'exit' to quit\n")

while True:
    user_query = input("❓ Ask: ").strip()

    if user_query.lower() == "exit":
        print("Goodbye!")
        break

    if not user_query:
        continue

    try:
        result = router_app.invoke({
            "question": user_query
        })

        if not isinstance(result, dict):
            raise RuntimeError("Router did not return a valid state")

        print("\n" + "="*80)
        print("🧠 RESPONSE")
        print("-"*80)
        print(result.get("final", "No response"))
        print("="*80 + "\n")

    except Exception as e:
        print("❌ System Error:", e)
