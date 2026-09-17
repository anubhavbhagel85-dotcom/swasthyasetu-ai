"""Pydantic schemas shared across the API."""
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class Language(str, Enum):
    en = "en"
    hi = "hi"


class TriageLevel(str, Enum):
    EMERGENCY = "EMERGENCY"        # Call emergency services now
    URGENT = "URGENT"              # See a doctor within hours
    ROUTINE = "ROUTINE"            # See a doctor if it doesn't improve
    SELF_CARE = "SELF_CARE"        # General guidance, no red flags detected
    NEED_MORE_INFO = "NEED_MORE_INFO"  # Still asking follow-up questions


class AgeGroup(str, Enum):
    infant = "infant"        # < 1 year
    child = "child"          # 1-12 years
    teen = "teen"            # 13-17 years
    adult = "adult"          # 18-59 years
    senior = "senior"        # 60+ years


class Severity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class Source(BaseModel):
    name: str
    url: str
    type: str


class StartRequest(BaseModel):
    language: Language = Language.en


class StartResponse(BaseModel):
    session_id: str
    message: str
    language: Language


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session id returned by /chat/start")
    message: str = Field(..., description="Free-text user message, or the value of a quick-reply chip")
    language: Language = Language.en


class QuickReply(BaseModel):
    id: str
    label: str


class ChatResponse(BaseModel):
    session_id: str
    triage_level: TriageLevel
    reply_text: str
    quick_replies: List[QuickReply] = []
    matched_topic: Optional[str] = None
    red_flags_detected: List[str] = []
    sources: List[Source] = []
    emergency_numbers: Optional[Dict[str, str]] = None
    is_final: bool = False
    # --- Authenticity / transparency fields ---
    match_confidence: Optional[float] = Field(
        None, description="0-1 retrieval confidence for matched_topic, shown to the user so they can judge fit themselves.")
    recap: Optional[str] = Field(
        None, description="Plain-language echo of exactly what the user told us (duration/severity/age/red flags), shown before the answer.")
    # --- Home remedies (separately cited from clinical self-care; never populated for URGENT/EMERGENCY) ---
    home_remedies: List[str] = []
    remedy_sources: List[Source] = []
    remedy_caution: Optional[str] = None
    offline: bool = Field(False, description="True if this response was generated on-device without reaching the backend.")


class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_base_entries: int
