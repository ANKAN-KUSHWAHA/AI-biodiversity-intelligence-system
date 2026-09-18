from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class EnvironmentalData(BaseModel):
    """Information supplied by the user; all fields are optional by design."""
    soil_organic_carbon: float | None = Field(default=None, description="Percent, e.g. 0.3")
    soil_ph: float | None = None
    soil_moisture: str | None = None
    rainfall: str | None = None
    land_use: str | None = None
    crop: str | None = None
    biodiversity_indicators: str | None = None
    temperature: str | None = None
    region: str | None = None
    human_impact: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Source(BaseModel):
    title: str
    organization: str
    year: str
    url: str
    topic: str


class Recommendation(BaseModel):
    recommendation: str = Field(description="Specific, practical intervention")
    reasoning: str = Field(description="Evidence-bound mechanism and caveats")
    environmental_connections: list[str] = Field(description="Explicit links between supplied variables")
    impacted_metrics: list[str]
    time_horizon: str = Field(description="Short, medium and/or long term timing")
    confidence: Literal["High", "Medium", "Low"]
    monitoring_plan: list[str] = Field(description="Measurable baseline and follow-up observations; do not invent numeric improvement estimates")
    sources: list[Source] = Field(description="Only sources provided in retrieved context")


class FollowUpResponse(BaseModel):
    """Compact continuation of an existing site assessment."""
    answer: str = Field(description="Direct answer to the follow-up, grounded in the ongoing assessment")
    considerations: list[str] = Field(description="Short site-specific caveats or next decisions")
    sources: list[Source] = Field(description="Only sources provided in retrieved context")


class Clarification(BaseModel):
    clarification_question: str
    missing_information: list[str]
