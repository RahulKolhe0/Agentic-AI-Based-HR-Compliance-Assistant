from router.graph import router_app

print("🤖 HR Smart Router Ready\n")

while True:
    q = input("Ask: ")
    if q.lower() == "exit":
        break

    result = router_app.invoke({"question": q})
    print("\n🧠 Response:\n", result["final"])
    print("="*80)
