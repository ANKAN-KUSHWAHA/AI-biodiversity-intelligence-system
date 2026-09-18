from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from src.llm import get_llm
from src.models import EnvironmentalData, FollowUpResponse, Recommendation, Source
from src.reasoning import clarification, missing_critical, parse_query
from src.retrieval import format_context, retrieve
from src.state import DarukaaState


def parse_input(state: DarukaaState) -> dict:
    return {
        "environmental_data": parse_query(state["user_query"], state.get("known_environmental_data")),
        "workflow_trace": ["1. Parsed this turn and merged it with remembered site data."],
    }


def check_missing_information(state: DarukaaState) -> dict:
    missing = missing_critical(state["environmental_data"])
    # A general scientific "how/what is" question is not a site-specific prescription.
    informational = any(token in state["user_query"].lower() for token in ["how does", "what is", "explain"])
    if informational:
        missing = []
    if missing:
        return {"missing_information": missing, "clarification_question": clarification(missing), "workflow_trace": state.get("workflow_trace", []) + ["2. Paused for the missing decision variables; no recommendation was invented."]}
    return {"missing_information": [], "workflow_trace": state.get("workflow_trace", []) + ["2. Confirmed at least three decision variables are available."]}


def route_after_missing(state: DarukaaState) -> str:
    return "clarify" if state.get("missing_information") else "retrieve"


def route_after_retrieval(state: DarukaaState) -> str:
    """Never let an empty retrieval flow into an evidence-backed answer."""
    return "error" if state.get("error") else "reason"


def retrieve_knowledge(state: DarukaaState) -> dict:
    data = state["environmental_data"].model_dump(exclude_none=True)
    query = state.get("active_goal", state["user_query"]) + "\nLatest user message: " + state["user_query"] + "\nEnvironmental data: " + str(data)
    docs = retrieve(query)
    if not docs:
        return {"error": "No relevant material was retrieved from the local knowledge base."}
    sources = [Source(title=d["metadata"].get("title", "Untitled"), organization=d["metadata"].get("organization", "Unknown"), year=str(d["metadata"].get("year", "n.d.")), url=d["metadata"].get("source_url", ""), topic=d["metadata"].get("topic", "Environmental science")) for d in docs]
    return {"retrieved_documents": docs, "sources": sources, "workflow_trace": state.get("workflow_trace", []) + [f"3. Retrieved {len(docs)} relevant scientific source chunks from ChromaDB."]}


def reason_about_environment(state: DarukaaState) -> dict:
    # This node makes the LLM's reasoning evidence-bound and requires it to use several inputs.
    context = format_context(state["retrieved_documents"])
    data = state["environmental_data"].model_dump(exclude_none=True)
    prompt = f"""You are Darukaa.Earth, an environmental scientist. Analyze the user's land question using ONLY the retrieved scientific excerpts below. Do not invent measurements, sources, or effects. Explicitly connect at least three available environmental variables. Distinguish evidence from local uncertainty.\n\nOngoing user goal: {state.get('active_goal', state['user_query'])}\nConversation context: {state.get('conversation_context', 'None')}\nLatest message: {state['user_query']}\nEnvironmental data: {data}\n\nRetrieved scientific evidence:\n{context}\n\nWrite a concise evidence-bound scientific reasoning paragraph. Do not recommend an action yet."""
    result = get_llm().invoke(prompt)
    return {"reasoning": result.content, "workflow_trace": state.get("workflow_trace", []) + ["4. Connected the available soil, climate, land-use and biodiversity variables against retrieved evidence."]}


def generate_recommendation(state: DarukaaState) -> dict:
    context = format_context(state["retrieved_documents"])
    data = state["environmental_data"].model_dump(exclude_none=True)
    if state.get("is_follow_up"):
        prompt = f"""You are Darukaa.Earth, continuing an existing environmental assessment. Answer the user's latest follow-up directly and conversationally, using the earlier assessment as context. Do not repeat the complete site report or restate the original recommendation unless it is necessary. Use only supplied information and retrieved sources. Never invent measurements, sources, URLs, numerical improvement, or outcomes. Give 0-3 concise site-specific considerations. Cite only source records included below.\n\nOriginal goal: {state.get('active_goal')}\nConversation so far: {state.get('conversation_context', 'None')}\nFollow-up question: {state['user_query']}\nEnvironmental data: {data}\nRetrieved evidence:\n{context}"""
        answer = get_llm().with_structured_output(FollowUpResponse).invoke(prompt)
        answer.sources = state["sources"]
        return {"follow_up_response": answer, "workflow_trace": state.get("workflow_trace", []) + ["5. Answered the follow-up using the existing assessment context and grounded citations."]}

    prompt = f"""You are Darukaa.Earth, an evidence-first environmental scientist. Produce ONE practical, specific land-management recommendation for this case. Use only supplied variables and retrieved sources. Never invent a source, URL, numerical improvement, or outcome. Your environmental_connections must explicitly connect at least three available variables. Explain uncertainty; do not promise outcomes. monitoring_plan must give practical measurable baseline/follow-up observations (for example a soil test, moisture reading, pollinator count), not unsupported numeric forecasts. Cite only source records included below, using their exact title, organization, year, URL, and topic.\n\nOngoing goal: {state.get('active_goal', state['user_query'])}\nConversation context: {state.get('conversation_context', 'None')}\nLatest message: {state['user_query']}\nEnvironmental data: {data}\nPrior evidence-bound reasoning: {state['reasoning']}\n\nRetrieved evidence:\n{context}"""
    answer = get_llm().with_structured_output(Recommendation).invoke(prompt)
    answer.sources = state["sources"]
    return {"recommendation": answer, "workflow_trace": state.get("workflow_trace", []) + ["5. Produced a structured action, monitoring plan, confidence, and grounded citations."]}


def build_graph():
    graph = StateGraph(DarukaaState)
    graph.add_node("parse_input", parse_input)
    graph.add_node("check_missing_information", check_missing_information)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("reason_about_environment", reason_about_environment)
    graph.add_node("generate_recommendation", generate_recommendation)
    graph.add_edge(START, "parse_input")
    graph.add_edge("parse_input", "check_missing_information")
    graph.add_conditional_edges("check_missing_information", route_after_missing, {"clarify": END, "retrieve": "retrieve_knowledge"})
    graph.add_conditional_edges("retrieve_knowledge", route_after_retrieval, {"error": END, "reason": "reason_about_environment"})
    graph.add_edge("reason_about_environment", "generate_recommendation")
    graph.add_edge("generate_recommendation", END)
    return graph.compile()
