from __future__ import annotations

import re
from src.models import EnvironmentalData


FIELD_LABELS = {
    "soil_organic_carbon": "soil organic carbon (%)", "soil_ph": "soil pH", "soil_moisture": "soil moisture",
    "rainfall": "rainfall pattern", "land_use": "land use", "crop": "crop type",
    "biodiversity_indicators": "biodiversity indicator", "temperature": "temperature", "region": "region",
    "human_impact": "human impact (pollution, deforestation, etc.)",
    "latitude": "latitude", "longitude": "longitude",
}


def parse_query(query: str, existing: EnvironmentalData | None = None) -> EnvironmentalData:
    """Small transparent extractor; prior-turn fields are retained and never invented."""
    data = (existing or EnvironmentalData()).model_dump()
    q = query.lower()
    soc = re.search(r"(?:soil organic carbon|soc)\s*(?:is|=|:)?\s*(\d+(?:\.\d+)?)\s*%", q)
    ph = re.search(r"(?:soil )?p\s*h\s*(?:is|=|:)?\s*(\d(?:\.\d+)?)", q)
    if soc: data["soil_organic_carbon"] = float(soc.group(1))
    # Typical follow-up after we asked for SOC: "It is 0.3%."
    implicit_soc = re.search(r"(?:it|soc)\s*(?:is|=|:)\s*(\d+(?:\.\d+)?)\s*%", q)
    if implicit_soc and data.get("soil_organic_carbon") is None:
        data["soil_organic_carbon"] = float(implicit_soc.group(1))
    if ph: data["soil_ph"] = float(ph.group(1))
    patterns = {
        "rainfall": ["low rainfall", "high rainfall", "erratic rainfall", "dry rainfall"],
        "soil_moisture": ["low soil moisture", "high soil moisture", "dry soil", "waterlogged"],
        "land_use": ["monoculture", "intercropping", "agroforestry", "cropland", "pasture"],
        "crop": ["wheat", "maize", "rice", "soy", "cotton", "millet"],
        "region": ["semi-arid", "arid", "tropical", "temperate", "coastal"],
        "human_impact": ["pollution", "deforestation", "fragmented", "habitat fragmentation"],
    }
    for field, terms in patterns.items():
        found = next((term for term in terms if term in q), None)
        if found: data[field] = found
    rainfall_value = re.search(r"rainfall\s*(?:is|=|:)\s*(low|high|erratic|seasonal)", q)
    moisture_value = re.search(r"soil moisture\s*(?:is|=|:)\s*(low|high|moderate)", q)
    if rainfall_value: data["rainfall"] = rainfall_value.group(1)
    if moisture_value: data["soil_moisture"] = moisture_value.group(1)
    latitude = re.search(r"(?:latitude|lat)\s*(?:is|=|:)?\s*(-?\d+(?:\.\d+)?)", q)
    longitude = re.search(r"(?:longitude|lon|lng)\s*(?:is|=|:)?\s*(-?\d+(?:\.\d+)?)", q)
    if latitude: data["latitude"] = float(latitude.group(1))
    if longitude: data["longitude"] = float(longitude.group(1))
    if "biodiversity is declining" in q or "species richness" in q or "pollinator" in q:
        data["biodiversity_indicators"] = "declining biodiversity" if "declining" in q else "biodiversity concern"
    return EnvironmentalData(**data)


def missing_critical(data: EnvironmentalData) -> list[str]:
    """Need three decision variables before prescribing land-management action."""
    # Biodiversity indicators describe the outcome we want to protect; they do not
    # replace the three environmental drivers needed for a site-specific action.
    fields = ["soil_organic_carbon", "soil_ph", "soil_moisture", "rainfall", "land_use", "crop", "region", "human_impact", "temperature"]
    present = [f for f in fields if getattr(data, f) is not None]
    if len(present) >= 3:
        return []
    priority = ["soil_organic_carbon", "rainfall", "land_use", "crop", "region"]
    return [FIELD_LABELS[f] for f in priority if getattr(data, f) is None][:3 - len(present)]


def clarification(missing: list[str]) -> str:
    return "To make an evidence-backed recommendation without guessing, please share: " + ", ".join(missing) + "."
