from __future__ import annotations

from typing import TypedDict
from src.models import EnvironmentalData, FollowUpResponse, Recommendation, Source


class DarukaaState(TypedDict, total=False):
    user_query: str
    conversation_context: str
    active_goal: str
    is_follow_up: bool
    environmental_data: EnvironmentalData
    known_environmental_data: EnvironmentalData
    missing_information: list[str]
    retrieved_documents: list[dict]
    reasoning: str
    recommendation: Recommendation
    follow_up_response: FollowUpResponse
    sources: list[Source]
    clarification_question: str
    workflow_trace: list[str]
    error: str
