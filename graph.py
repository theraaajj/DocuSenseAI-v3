"""
graph.py — Phase 1 Agentic Brain Upgrade
LangGraph CRAG (Corrective RAG) state machine for DocuSenseAI v2.

Flow:
  retrieve → grade_documents → generate        (if docs are relevant)
                             ↘ rewrite_query → retrieve  (if all docs irrelevant, max 2 retries)
"""

import json
import ollama
from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END


# ─────────────────────────────────────────────
# 1. STATE — everything the graph passes around
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    query: str                  # current (possibly rewritten) query
    original_query: str         # never mutated — for display purposes
    retriever: object           # EnsembleRetriever or VectorStore passed in
    documents: List[Document]   # retrieved chunks
    relevant_docs: List[Document]  # docs that passed grading
    generation: str             # final answer
    retries: int                # how many query rewrites have happened
    grade_log: List[dict]       # [{chunk_preview, is_relevant, reason}, ...]


# ─────────────────────────────────────────────
# 2. PYDANTIC SCHEMA — structured grader output
# ─────────────────────────────────────────────
class GradeOutput(BaseModel):
    is_relevant: bool = Field(description="True if the document chunk is relevant to the query")
    reason: str = Field(description="One sentence explaining why this chunk is or is not relevant")


# ─────────────────────────────────────────────
# 3. NODES
# ─────────────────────────────────────────────

def retrieve(state: AgentState) -> AgentState:
    """Search using the hybrid retriever (Semantic + BM25)."""
    # use .invoke() for any LangChain retriever
    docs = state["retriever"].invoke(state["query"])
    return {**state, "documents": docs}


def grade_documents(state: AgentState) -> AgentState:
    """
    Grade each retrieved chunk for relevance using llama3.
    Uses a JSON-based prompt to approximate structured output from ollama.
    """
    grade_log = []
    relevant_docs = []

    grader_system = """You are a relevance grader. Given a USER QUERY and a DOCUMENT CHUNK,
decide if the chunk contains information useful for answering the query.

Respond ONLY with a JSON object in this exact format (no markdown, no extra text):
{"is_relevant": true or false, "reason": "one sentence explanation"}
"""

    for doc in state["documents"]:
        chunk_preview = doc.page_content[:300].replace("\n", " ")
        user_msg = f"USER QUERY: {state['query']}\n\nDOCUMENT CHUNK:\n{doc.page_content}"

        try:
            response = ollama.chat(
                model="llama3.2",
                format="json",  # Force Ollama to return valid JSON
                messages=[
                    {"role": "system", "content": grader_system},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response["message"]["content"].strip()
            parsed = json.loads(raw)
            grade = GradeOutput(**parsed)

        except Exception as e:
            # If parsing fails, default to relevant to avoid losing context
            grade = GradeOutput(is_relevant=True, reason=f"(grading failed: {e}) — defaulted to relevant")

        grade_log.append({
            "chunk_preview": chunk_preview,
            "is_relevant": grade.is_relevant,
            "reason": grade.reason,
        })

        if grade.is_relevant:
            relevant_docs.append(doc)

    return {**state, "relevant_docs": relevant_docs, "grade_log": grade_log}


def generate(state: AgentState) -> AgentState:
    """Generate a final answer from the relevant docs using phi3."""
    docs_to_use = state["relevant_docs"] if state["relevant_docs"] else state["documents"]
    context_text = "\n\n---\n\n".join([doc.page_content for doc in docs_to_use])

    system_prompt = f"""You are DocuSenseAI, a secure local reasoning assistant.
STRICT RULES:
1. USE ONLY the provided context.
2. If the answer is NOT in the context, strictly state: "I cannot find this information in the provided files."
3. Do NOT invent facts. Do NOT use outside knowledge.
4. If the user asks to "Summarize", provide a structured summary with bullet points.
5. If the user asks to "Write content", provide the raw text verbatim.

CONTEXT FROM FILES:
{context_text}
"""

    response = ollama.chat(
        model="phi3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["original_query"]},
        ],
    )

    return {**state, "generation": response["message"]["content"]}


def rewrite_query(state: AgentState) -> AgentState:
    """
    Rewrite the query when grader says all docs are irrelevant.
    Uses llama3 to rephrase for a better vector search hit.
    """
    system_prompt = """You are a search query optimizer for a document retrieval system.
The current query did not return relevant results. Rephrase it to be more specific and likely 
to match document content. Return ONLY the rewritten query, nothing else."""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original query: {state['query']}"},
        ],
    )

    rewritten = response["message"]["content"].strip()
    new_retries = state.get("retries", 0) + 1

    return {**state, "query": rewritten, "retries": new_retries}


# ─────────────────────────────────────────────
# 4. ROUTING LOGIC
# ─────────────────────────────────────────────
def route_after_grading(state: AgentState) -> Literal["generate", "rewrite_query"]:
    """
    If any docs passed grading → generate.
    If all docs failed AND we haven't retried 2 times yet → rewrite.
    If we've retried 2 times already → generate anyway (best-effort).
    """
    has_relevant = len(state["relevant_docs"]) > 0
    max_retries_hit = state.get("retries", 0) >= 2

    if has_relevant or max_retries_hit:
        return "generate"
    else:
        return "rewrite_query"


# ─────────────────────────────────────────────
# 5. BUILD & COMPILE THE GRAPH
# ─────────────────────────────────────────────
def build_crag_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("generate", generate)
    graph.add_node("rewrite_query", rewrite_query)

    # Entry point
    graph.set_entry_point("retrieve")

    # Edges
    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {
            "generate": "generate",
            "rewrite_query": "rewrite_query",
        },
    )
    graph.add_edge("rewrite_query", "retrieve")   # loop back
    graph.add_edge("generate", END)

    return graph.compile()


# Singleton compiled graph (avoids recompiling on every query)
crag_graph = build_crag_graph()
