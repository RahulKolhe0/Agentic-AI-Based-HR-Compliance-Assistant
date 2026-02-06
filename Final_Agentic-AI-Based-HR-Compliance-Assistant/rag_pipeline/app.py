from langgraph.graph import StateGraph, END
from rag_pipeline.graph_nodes import *
from rag_pipeline.ingest import ingest

print("🔍 Checking for new PDFs...")
ingest()

graph = StateGraph(GraphState)

graph.add_node("intent", intent_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("rerank", rerank_node)
graph.add_node("categorize", lambda s: {**s, "categories": categorize_chunks(s["reranked"])})
graph.add_node("context", context_node)
graph.add_node("generate", generate_node)
graph.add_node("validate", validate_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("intent")

graph.add_edge("intent", "retrieve")
graph.add_edge("retrieve", "rerank")
graph.add_edge("rerank", "categorize")
graph.add_edge("categorize", "context")
graph.add_edge("context", "generate")

# validate ONLY uses conditional edges
graph.add_edge("generate", "validate")

graph.add_conditional_edges(
    "validate",
    should_retry,
    {
        "retry": "generate",
        "end": "finalize"
    }
)

graph.add_edge("finalize", END)

app = graph.compile()
