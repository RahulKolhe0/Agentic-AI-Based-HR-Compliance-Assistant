from sql_pipeline.agent import analytical_agent

print("\n✅ HR Analytical Agent Ready\n")

while True:
    q = input("❓ Ask: ")
    if q.lower() == "exit":
        break
    print("\n🧠 Answer:\n", analytical_agent(q))
    print("="*70)
