from __future__ import annotations

import json

import streamlit as st
from pydantic import ValidationError

from src.graph import build_graph
from src.models import EnvironmentalData, FollowUpResponse, Recommendation

st.set_page_config(page_title="Darukaa.Earth", page_icon="🌍", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "environmental_data" not in st.session_state:
    st.session_state.environmental_data = EnvironmentalData()
if "question_draft" not in st.session_state:
    st.session_state.question_draft = ""
if "active_goal" not in st.session_state:
    st.session_state.active_goal = ""


@st.cache_resource
def workflow():
    return build_graph()


def source_list(sources: list[dict]) -> None:
    st.markdown("#### Scientific sources retrieved")
    for source in sources:
        name = f"{source.get('organization', 'Source')} — {source.get('title', 'Untitled')} ({source.get('year', 'n.d.')})"
        url = source.get("url", "")
        st.markdown(f"- [{name}]({url})" if url else f"- {name}")


def render_result(result: dict) -> None:
    if result.get("error"):
        st.error(result["error"])
        return
    if result.get("clarification_question"):
        st.info(result["clarification_question"])
        return
    recommendation = result.get("recommendation")
    if not recommendation:
        st.warning("No recommendation was returned. Please try again.")
        return
    if isinstance(recommendation, Recommendation):
        recommendation = recommendation.model_dump()

    st.success(recommendation["recommendation"])
    st.caption("Evidence-backed guidance based on the site context you shared and the scientific sources cited below. Local results can vary, so use the monitoring steps to validate progress on your land.")
    st.markdown("#### Why it works")
    st.write(recommendation["reasoning"])
    st.markdown("#### Environmental connections")
    for connection in recommendation["environmental_connections"]:
        st.markdown(f"- {connection}")

    metrics, details = st.columns(2)
    with metrics:
        st.markdown("#### Metrics to monitor")
        for metric in recommendation["impacted_metrics"]:
            st.markdown(f"- {metric}")
    with details:
        st.markdown("#### Expected timing")
        st.write(recommendation["time_horizon"])
        st.markdown("#### Confidence")
        st.write(recommendation["confidence"])
    st.markdown("#### What to measure next")
    for item in recommendation.get("monitoring_plan", []):
        st.markdown(f"- {item}")
    source_list(recommendation.get("sources", []))


def render_follow_up(result: dict) -> None:
    if result.get("error"):
        st.error(result["error"])
        return
    if result.get("clarification_question"):
        st.info(result["clarification_question"])
        return
    reply = result.get("follow_up_response")
    if not reply:
        st.warning("No follow-up response was returned. Please try again.")
        return
    if isinstance(reply, FollowUpResponse):
        reply = reply.model_dump()
    st.write(reply["answer"])
    if reply.get("considerations"):
        with st.expander("Site-specific considerations"):
            for item in reply["considerations"]:
                st.markdown(f"- {item}")
    source_list(reply.get("sources", []))


def submit(question: str, structured_data: dict) -> None:
    if not question.strip():
        st.error("Please enter a question. Structured JSON is optional, but the question is required.")
        return
    try:
        previous = st.session_state.environmental_data
        known = previous.model_copy(update=structured_data)
        has_history = bool(st.session_state.messages)
        previous_result = st.session_state.messages[-1]["result"] if has_history else {}
        continuing_clarification = bool(previous_result.get("clarification_question"))
        # Keep the first question as the goal for both missing-data replies and
        # ordinary follow-ups. A new assessment is explicitly started via the UI.
        active_goal = st.session_state.active_goal if has_history else question
        is_follow_up = has_history and not continuing_clarification
        history = st.session_state.messages[-3:]
        context_parts = []
        for item in history:
            context_parts.append(f"User: {item['question']}")
            prior = item["result"].get("follow_up_response") or item["result"].get("recommendation")
            if prior:
                if isinstance(prior, FollowUpResponse):
                    text = prior.answer
                elif isinstance(prior, Recommendation):
                    text = prior.recommendation
                else:
                    text = prior.get("answer") or prior.get("recommendation", "")
                context_parts.append(f"Assistant: {text}")
        context = " | ".join(context_parts) or "No earlier turns."
        result = workflow().invoke({
            "user_query": question,
            "known_environmental_data": known,
            "active_goal": active_goal,
            "conversation_context": context,
            "is_follow_up": is_follow_up,
        })
        st.session_state.environmental_data = result.get("environmental_data", known)
        st.session_state.active_goal = active_goal
        st.session_state.messages.append({"question": question, "result": result, "is_follow_up": is_follow_up})
    except (RuntimeError, ValidationError) as exc:
        st.session_state.messages.append({"question": question, "result": {"error": str(exc)}, "is_follow_up": False})
    except Exception as exc:
        st.session_state.messages.append({"question": question, "result": {"error": f"The analysis could not be completed: {exc}"}, "is_follow_up": False})


st.title("Darukaa.Earth")
st.subheader("AI Biodiversity Intelligence")
st.write("Ask an environmental question, add optional field data, and receive an evidence-backed biodiversity recommendation.")
if st.session_state.messages and st.button("Start a new assessment"):
    st.session_state.messages = []
    st.session_state.environmental_data = EnvironmentalData()
    st.session_state.active_goal = ""
    st.session_state.question_draft = ""
    st.rerun()
st.divider()

examples = [
    "My soil organic carbon is 0.3%, rainfall is low, and I grow wheat as a monoculture in a semi-arid region. What should I do to improve biodiversity?",
    "Biodiversity is declining on my land. What information do you need?",
    "My soil moisture is low and my land is surrounded by fragmented agricultural fields. What can I change?",
    "How does increasing soil organic carbon affect biodiversity?",
]

with st.expander("Demo questions", expanded=False):
    selected = st.selectbox("Choose an example", ["Select…"] + examples)
    if selected != "Select…" and st.button("Use this example"):
        st.session_state.question_draft = selected
        st.rerun()

with st.container(border=True):
    st.markdown("### Analyze a site")
    st.caption("Your question is required. JSON data is optional.")
    question = st.text_area(
        "Environmental question *",
        value=st.session_state.question_draft,
        height=110,
        placeholder="What should I change to improve biodiversity on this farm?",
    )
    with st.expander("Optional structured environmental input (JSON)"):
        raw_json = st.text_area(
            "Environmental JSON",
            height=150,
            placeholder='''{
  "soil_organic_carbon": 0.3,
  "rainfall": "low",
  "crop": "wheat",
  "land_use": "monoculture",
  "region": "semi-arid"
}''',
        )
        st.caption("Allowed fields: soil_organic_carbon, soil_ph, soil_moisture, rainfall, land_use, crop, biodiversity_indicators, temperature, region, human_impact, latitude, longitude.")
    analyze = st.button("Analyze biodiversity conditions", type="primary")
    st.caption("Live evidence retrieval and reasoning usually take 10-30 seconds.")

if analyze:
    try:
        data = EnvironmentalData.model_validate(json.loads(raw_json)).model_dump(exclude_none=True) if raw_json.strip() else {}
        with st.spinner("Analyzing your site…"):
            submit(question, data)
        st.session_state.question_draft = ""
        st.rerun()
    except (json.JSONDecodeError, ValidationError) as exc:
        st.error(f"Invalid structured JSON: {exc}")

current_data = st.session_state.environmental_data.model_dump(exclude_none=True)
if current_data:
    with st.expander("Remembered site context"):
        st.json(current_data)

if st.session_state.messages:
    st.divider()
    st.header("Analysis history")
    for item in st.session_state.messages:
        if item.get("is_follow_up"):
            with st.chat_message("user"):
                st.write(item["question"])
            with st.chat_message("assistant"):
                render_follow_up(item["result"])
        else:
            with st.container(border=True):
                st.markdown("**Assessment question**")
                st.write(item["question"])
                render_result(item["result"])

    st.divider()
    st.subheader("Continue this environmental assessment")
    st.caption("Ask about the recommendation, provide a missing value, or request another evidence-backed option. Your earlier site context stays available.")
    with st.form("follow_up_form", clear_on_submit=True):
        follow_up = st.text_input(
            "Follow-up question or missing information",
            placeholder="Example: Soil organic carbon is 0.3%, rainfall is low, and land use is monoculture wheat.",
        )
        follow_up_submit = st.form_submit_button("Continue analysis")
    if follow_up_submit:
        with st.spinner("Continuing your assessment…"):
            submit(follow_up, {})
        st.rerun()

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.environmental_data = EnvironmentalData()
        st.session_state.active_goal = ""
        st.rerun()
