"""
Safety layer for SwasthyaSetu AI.

This module is intentionally independent from the retrieval (RAG) engine.
Its only job is to answer: "does anything in this conversation look
dangerous enough that the user should be told to seek urgent/emergency
care right now?" It never tries to name a diagnosis.

Design principle (matches the hackathon brief):
  "Separate urgent warning signs from general guidance."
So this module always returns a structured TriageLevel + the specific
red flags it matched, so the API/UI can render them as a distinct,
visually separate block from the general self-care information.
"""
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import DATA_DIR
from app.schemas import TriageLevel, Severity, AgeGroup, Language

with open(DATA_DIR / "red_flags.json", encoding="utf-8") as f:
    _RED_FLAGS = json.load(f)

EMERGENCY_NUMBERS = _RED_FLAGS["emergency_numbers"]


@dataclass
class SafetyResult:
    triage_level: TriageLevel
    matched_flags: List[str] = field(default_factory=list)
    is_crisis: bool = False
    message: Optional[str] = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def check_global_emergency(text: str, language: Language) -> Optional[SafetyResult]:
    """Scan free-text input for cross-topic emergency phrases (breathing,
    chest pain, stroke signs, suicidal ideation, severe bleeding, etc).
    This runs on EVERY user message, regardless of which symptom topic
    the conversation is about.
    """
    normalized = _normalize(text)
    for pattern_group in _RED_FLAGS["emergency_patterns"]:
        for phrase in pattern_group["patterns"]:
            if phrase.lower() in normalized:
                return SafetyResult(
                    triage_level=TriageLevel.EMERGENCY,
                    matched_flags=[pattern_group["message"][language.value]],
                    is_crisis=pattern_group.get("is_crisis", False),
                    message=pattern_group["message"][language.value],
                )
    return None


def check_topic_red_flags(topic_entry: dict, free_text: str, language: Language) -> List[str]:
    """Check whether the free text mentions any of the topic-specific red
    flags stored in the knowledge base entry (e.g. for 'fever':
    'stiff neck', 'convulsions', etc). This is a simple keyword pass —
    good enough for a hackathon demo, and easy to swap for a classifier
    later (see ARCHITECTURE.md)."""
    normalized = _normalize(free_text)
    matched = []
    for flag in topic_entry.get("red_flags", {}).get(language.value, []):
        # Take the most distinctive word(s) from the red-flag phrase for matching
        key_terms = [t for t in re.split(r"[,/]| or | and ", flag.lower()) if len(t.strip()) > 3]
        for term in key_terms:
            if term.strip() in normalized:
                matched.append(flag)
                break
    return matched


def escalate_from_followups(
    base_level: TriageLevel,
    severity: Optional[Severity],
    duration_days: Optional[int],
    age_group: Optional[AgeGroup],
    topic_always_urgent: bool = False,
) -> TriageLevel:
    """Combine structured follow-up answers (duration, severity, age group)
    with whatever the keyword pass already found, and return the final
    triage level. This never DOWNGRADES an already-EMERGENCY level.
    """
    if base_level == TriageLevel.EMERGENCY:
        return TriageLevel.EMERGENCY

    if topic_always_urgent:
        return TriageLevel.URGENT

    level = base_level

    # Vulnerable age groups get escalated a step for the same symptoms.
    vulnerable_age = age_group in (AgeGroup.infant, AgeGroup.senior)

    if severity == Severity.severe:
        level = TriageLevel.URGENT
    elif severity == Severity.moderate and vulnerable_age:
        level = TriageLevel.URGENT
    elif duration_days is not None and duration_days >= 7:
        level = TriageLevel.ROUTINE if level == TriageLevel.SELF_CARE else level
    elif vulnerable_age and level == TriageLevel.SELF_CARE:
        level = TriageLevel.ROUTINE

    return level


def build_emergency_banner(language: Language, matched_flags: List[str], is_crisis: bool) -> str:
    numbers = EMERGENCY_NUMBERS
    if is_crisis:
        if language == Language.hi:
            return (
                "🆘 यह एक संवेदनशील पल लग रहा है। कृपया अभी Tele-MANAS हेल्पलाइन "
                f"{numbers['india_mental_health_telemanas']} (24x7, टोल-फ्री) पर कॉल करें "
                "या नज़दीकी अस्पताल जाएं। आप अकेले नहीं हैं।"
            )
        return (
            "🆘 This sounds like a difficult moment. Please call the Tele-MANAS helpline "
            f"{numbers['india_mental_health_telemanas']} (24x7, toll-free) right now, "
            "or go to your nearest emergency department. You are not alone."
        )

    flags_text = "; ".join(matched_flags)
    if language == Language.hi:
        return (
            f"🚨 आपातकालीन चेतावनी: {flags_text}\n"
            f"कृपया तुरंत {numbers['india_ambulance']} (एम्बुलेंस) या {numbers['india_general']} "
            "(राष्ट्रीय आपातकालीन नंबर) पर कॉल करें, या नज़दीकी अस्पताल के आपातकालीन विभाग में जाएं।"
        )
    return (
        f"🚨 Urgent warning signs detected: {flags_text}\n"
        f"Please call {numbers['india_ambulance']} (ambulance) or {numbers['india_general']} "
        "(national emergency number) right now, or go to your nearest emergency department."
    )
