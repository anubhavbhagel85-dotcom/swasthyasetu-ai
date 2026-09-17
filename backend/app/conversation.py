"""
Conversation state machine for SwasthyaSetu AI.

Flow (matches the hackathon "must-have" list, now extended for depth +
authenticity per the team's v1.1 feature additions):
  1. Symptom input (free text, EN/HI)
  2. Topic confirmation - "Did you mean X?" with a visible confidence score,
     so a wrong keyword match gets caught before wasting the user's time
     on follow-ups (this puts more real weight on the follow-up flow being
     right, instead of trusting one retrieval guess blindly).
  3. Follow-up questions: duration -> severity -> age group -> red-flag checklist
  4. A recap ("here's exactly what you told me") before the final answer -
     the core "authenticity" feature: the user can see the answer is
     grounded in their own words, not a generic template.
  5. Final answer with THREE separately-cited blocks:
       - clinical self-care (WHO / NHS / MoHFW)
       - traditional home remedies (Ministry of AYUSH) - only ever shown
         for SELF_CARE / ROUTINE triage, never for URGENT / EMERGENCY
       - the safety banner, kept visually/textually separate throughout

Session state is kept in-memory for the hackathon MVP (see
DEPLOYMENT_GUIDE.md for swapping this dict for Redis in production, and
for how this mirrors the client-side offline engine in
frontend/src/offline/offlineEngine.js used when there's no connectivity).
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from app.schemas import (
    ChatResponse, QuickReply, Source, TriageLevel, Severity, AgeGroup, Language,
)
from app import rag_engine, safety_layer

SESSIONS: Dict[str, "Session"] = {}

CONFIDENCE_HIGH = 0.5
CONFIDENCE_MEDIUM = 0.2


class Stage(str, Enum):
    AWAITING_SYMPTOM = "AWAITING_SYMPTOM"
    AWAITING_TOPIC_CONFIRMATION = "AWAITING_TOPIC_CONFIRMATION"
    AWAITING_DURATION = "AWAITING_DURATION"
    AWAITING_SEVERITY = "AWAITING_SEVERITY"
    AWAITING_AGE = "AWAITING_AGE"
    AWAITING_REDFLAG_CHECK = "AWAITING_REDFLAG_CHECK"
    DONE = "DONE"


DURATION_OPTIONS = {
    "en": [("today", "Just started today", 0), ("2_3_days", "2-3 days", 2),
           ("4_7_days", "4-7 days", 5), ("over_week", "More than a week", 10)],
    "hi": [("today", "आज ही शुरू हुआ", 0), ("2_3_days", "2-3 दिन", 2),
           ("4_7_days", "4-7 दिन", 5), ("over_week", "एक हफ्ते से ज़्यादा", 10)],
}
SEVERITY_OPTIONS = {
    "en": [("mild", "Mild - barely noticeable"), ("moderate", "Moderate - noticeable but manageable"),
           ("severe", "Severe - hard to bear / limits activity")],
    "hi": [("mild", "हल्का - मुश्किल से महसूस होता है"), ("moderate", "मध्यम - महसूस होता है पर सहन करने लायक"),
           ("severe", "गंभीर - सहन करना मुश्किल / काम करने में दिक्कत")],
}
AGE_OPTIONS = {
    "en": [("infant", "Under 1 year"), ("child", "1-12 years"), ("teen", "13-17 years"),
           ("adult", "18-59 years"), ("senior", "60+ years")],
    "hi": [("infant", "1 साल से कम"), ("child", "1-12 साल"), ("teen", "13-17 साल"),
           ("adult", "18-59 साल"), ("senior", "60+ साल")],
}
YES_NO_OPTIONS = {
    "en": [("yes", "Yes, that's right"), ("no", "No, let me rephrase")],
    "hi": [("yes", "हां, यह सही है"), ("no", "नहीं, मैं फिर से बताता हूं")],
}


@dataclass
class Session:
    session_id: str
    language: Language
    stage: Stage = Stage.AWAITING_SYMPTOM
    matched_topic_id: Optional[str] = None
    match_confidence: Optional[float] = None
    duration_days: Optional[int] = None
    duration_label: Optional[str] = None
    severity: Optional[Severity] = None
    severity_label: Optional[str] = None
    age_group: Optional[AgeGroup] = None
    age_label: Optional[str] = None
    accumulated_red_flags: List[str] = field(default_factory=list)
    original_message: str = ""
    rephrase_attempts: int = 0


def start_session(language: Language) -> Session:
    session = Session(session_id=str(uuid.uuid4()), language=language)
    SESSIONS[session.session_id] = session
    return session


def _welcome_text(language: Language) -> str:
    if language == Language.hi:
        return (
            "नमस्ते मैं SwasthyaSetu AI हूं। मुझे बताइए आपको क्या तकलीफ महसूस हो रही है "
            "(जैसे: बुखार, खांसी, सिरदर्द, पेट दर्द)।\n\n"
            "ध्यान दें: मैं डॉक्टर नहीं हूं और कोई बीमारी नहीं बताता - मैं सिर्फ सामान्य, "
            "स्रोत-आधारित जानकारी और यह सुझाव देता हूं कि आपको किस स्तर की मदद लेनी चाहिए।"
        )
    return (
        "Hi, I'm SwasthyaSetu AI. Tell me what symptom you're experiencing "
        "(e.g., fever, cough, headache, stomach pain).\n\n"
        "Note: I'm not a doctor and I don't diagnose conditions - I share general, "
        "source-backed information and help you judge what level of care may be appropriate."
    )


def _quick_replies(options, language: Language) -> List[QuickReply]:
    lang = language.value
    return [QuickReply(id=opt[0], label=opt[1]) for opt in options[lang]]


def _duration_to_days(choice_id: str) -> int:
    for lang_opts in DURATION_OPTIONS.values():
        for oid, _, days in lang_opts:
            if oid == choice_id:
                return days
    return 0


def _label_for(options, lang: str, choice_id: str) -> str:
    for opt in options[lang]:
        if opt[0] == choice_id:
            return opt[1]
    return choice_id


def _sources_from_entry(entry: dict) -> List[Source]:
    return [Source(**s) for s in entry.get("sources", [])]


def _confidence_hedge(confidence: float, lang: str) -> str:
    if confidence >= CONFIDENCE_HIGH:
        return ""
    if confidence >= CONFIDENCE_MEDIUM:
        return " (moderate-confidence match)" if lang == "en" else " (मध्यम-भरोसे का मिलान)"
    return " (low-confidence guess - please double-check)" if lang == "en" else " (कम भरोसे का अनुमान - कृपया दोबारा जांचें)"


def _build_recap(session: Session) -> str:
    lang = session.language.value
    entry = rag_engine.get_entry_by_id(session.matched_topic_id)
    topic_label = entry["title"][lang] if entry else session.original_message

    if lang == "hi":
        lines = [f"आपने बताया: {topic_label}, {session.duration_label} से, गंभीरता: {session.severity_label}, आयु वर्ग: {session.age_label}।"]
        if session.accumulated_red_flags:
            lines.append("आपने यह भी बताया: " + "; ".join(session.accumulated_red_flags))
        return " ".join(lines)

    lines = [f"Here's what you told me: {topic_label}, present for {session.duration_label}, "
             f"severity: {session.severity_label}, age group: {session.age_label}."]
    if session.accumulated_red_flags:
        lines.append("You also flagged: " + "; ".join(session.accumulated_red_flags))
    return " ".join(lines)


def _format_final_answer(session: Session) -> ChatResponse:
    entry = rag_engine.get_entry_by_id(session.matched_topic_id) if session.matched_topic_id else None
    lang = session.language.value

    base_level = TriageLevel.SELF_CARE
    topic_always_urgent = bool(entry and entry.get("always_urgent"))
    final_level = safety_layer.escalate_from_followups(
        base_level=base_level,
        severity=session.severity,
        duration_days=session.duration_days,
        age_group=session.age_group,
        topic_always_urgent=topic_always_urgent,
    )
    if session.accumulated_red_flags:
        final_level = TriageLevel.EMERGENCY if topic_always_urgent else TriageLevel.URGENT

    sections = [_build_recap(session)]

    if entry:
        sections.append(entry["overview"][lang])

    if final_level in (TriageLevel.EMERGENCY, TriageLevel.URGENT) and session.accumulated_red_flags:
        banner = safety_layer.build_emergency_banner(session.language, session.accumulated_red_flags, is_crisis=False)
        sections.append(banner)
    elif final_level == TriageLevel.ROUTINE:
        sections.append(
            "It's a good idea to get this checked by a doctor if it doesn't improve soon."
            if lang == "en" else
            "अगर जल्द सुधार न हो, तो डॉक्टर से जांच करवाना बेहतर होगा।"
        )

    if entry and final_level in (TriageLevel.SELF_CARE, TriageLevel.ROUTINE):
        tips = entry["self_care"][lang]
        header = "What you can do (WHO / NHS / MoHFW guidance):" if lang == "en" else "आप क्या कर सकते हैं (WHO / NHS / MoHFW मार्गदर्शन):"
        sections.append(header + "\n" + "\n".join(f"- {t}" for t in tips))

    home_remedies, remedy_sources, remedy_caution = [], [], None
    if entry and final_level in (TriageLevel.SELF_CARE, TriageLevel.ROUTINE) and entry.get("home_remedies"):
        home_remedies = entry["home_remedies"][lang]
        remedy_sources = entry.get("remedy_sources", [])
        remedy_caution = entry.get("remedy_caution", {}).get(lang)
        header = "Traditional home remedies (Ministry of AYUSH):" if lang == "en" else "पारंपरिक घरेलू उपाय (आयुष मंत्रालय):"
        sections.append(header + "\n" + "\n".join(f"- {t}" for t in home_remedies) + f"\n\nCaution: {remedy_caution}")

    if entry:
        rf_header = "Seek medical care promptly if you notice:" if lang == "en" else "अगर ये दिखे तो तुरंत डॉक्टर से मिलें:"
        sections.append(rf_header + "\n" + "\n".join(f"- {t}" for t in entry["red_flags"][lang]))

    disclaimer = rag_engine.DISCLAIMER[lang]
    sections.append(disclaimer)

    reply_text = "\n\n".join(sections)

    return ChatResponse(
        session_id=session.session_id,
        triage_level=final_level,
        reply_text=reply_text,
        quick_replies=[],
        matched_topic=session.matched_topic_id,
        match_confidence=session.match_confidence,
        recap=_build_recap(session),
        red_flags_detected=session.accumulated_red_flags,
        sources=_sources_from_entry(entry) if entry else [],
        home_remedies=home_remedies,
        remedy_sources=[Source(**s) for s in remedy_sources],
        remedy_caution=remedy_caution,
        emergency_numbers=safety_layer.EMERGENCY_NUMBERS if final_level in (
            TriageLevel.EMERGENCY, TriageLevel.URGENT) else None,
        is_final=True,
    )


def _emergency_response(session: Session, safety_result) -> ChatResponse:
    banner = safety_layer.build_emergency_banner(
        session.language, safety_result.matched_flags, safety_result.is_crisis
    )
    session.stage = Stage.DONE
    return ChatResponse(
        session_id=session.session_id,
        triage_level=TriageLevel.EMERGENCY,
        reply_text=banner,
        quick_replies=[],
        matched_topic=session.matched_topic_id,
        red_flags_detected=safety_result.matched_flags,
        sources=[],
        emergency_numbers=safety_layer.EMERGENCY_NUMBERS,
        is_final=True,
    )


def _reset_followup_state(session: Session) -> None:
    session.matched_topic_id = None
    session.match_confidence = None
    session.duration_days = None
    session.duration_label = None
    session.severity = None
    session.severity_label = None
    session.age_group = None
    session.age_label = None
    session.accumulated_red_flags = []


def handle_message(session: Session, message: str) -> ChatResponse:
    lang = session.language

    emergency = safety_layer.check_global_emergency(message, lang)
    if emergency:
        return _emergency_response(session, emergency)

    if session.stage == Stage.AWAITING_SYMPTOM:
        session.original_message = message
        hits = rag_engine.retrieve(message)
        if not hits:
            text = (
                "I couldn't confidently match that to a topic I currently cover. "
                "Could you describe it differently, or choose one below?"
                if lang == Language.en else
                "मैं इसे किसी मौजूदा विषय से ठीक से नहीं जोड़ पाया। कृपया अलग तरीके से बताएं "
                "या नीचे से कोई विकल्प चुनें।"
            )
            common = rag_engine.ENTRIES[:6]
            chips = [QuickReply(id=e["id"], label=e["title"][lang.value]) for e in common]
            return ChatResponse(
                session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
                reply_text=text, quick_replies=chips, matched_topic=None,
            )

        entry = hits[0].entry
        session.matched_topic_id = entry["id"]
        session.match_confidence = round(hits[0].score, 2)
        session.accumulated_red_flags += safety_layer.check_topic_red_flags(entry, message, lang)
        session.stage = Stage.AWAITING_TOPIC_CONFIRMATION

        hedge = _confidence_hedge(hits[0].score, lang.value)
        text = (
            f"Got it - this sounds related to {entry['title'][lang.value]}{hedge}. Is that right?"
            if lang == Language.en else
            f"समझ गया - यह {entry['title'][lang.value]}{hedge} से संबंधित लगता है। क्या यह सही है?"
        )
        return ChatResponse(
            session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
            reply_text=text, quick_replies=_quick_replies(YES_NO_OPTIONS, lang),
            matched_topic=session.matched_topic_id, match_confidence=session.match_confidence,
        )

    if session.stage == Stage.AWAITING_TOPIC_CONFIRMATION:
        if message == "no":
            session.rephrase_attempts += 1
            entry_to_avoid = session.matched_topic_id
            _reset_followup_state(session)
            session.stage = Stage.AWAITING_SYMPTOM
            if session.rephrase_attempts >= 2:
                common = [e for e in rag_engine.ENTRIES if e["id"] != entry_to_avoid][:6]
                chips = [QuickReply(id=e["id"], label=e["title"][lang.value]) for e in common]
                text = ("No problem - please pick the closest match instead:" if lang == Language.en
                        else "कोई बात नहीं - कृपया सबसे नज़दीकी विकल्प चुनें:")
                return ChatResponse(
                    session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
                    reply_text=text, quick_replies=chips, matched_topic=None,
                )
            text = ("Sorry about that - please describe the symptom again in your own words."
                    if lang == Language.en else
                    "माफ़ कीजिए - कृपया लक्षण को फिर से अपने शब्दों में बताएं।")
            return ChatResponse(
                session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
                reply_text=text, quick_replies=[], matched_topic=None,
            )

        if message != "yes" and rag_engine.get_entry_by_id(message):
            session.matched_topic_id = message
            session.match_confidence = 1.0

        session.stage = Stage.AWAITING_DURATION
        text = ("How long has this been going on?" if lang == Language.en
                else "यह कब से हो रहा है?")
        return ChatResponse(
            session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
            reply_text=text, quick_replies=_quick_replies(DURATION_OPTIONS, lang),
            matched_topic=session.matched_topic_id,
        )

    if session.stage == Stage.AWAITING_DURATION:
        session.duration_days = _duration_to_days(message)
        session.duration_label = _label_for(DURATION_OPTIONS, lang.value, message)
        session.stage = Stage.AWAITING_SEVERITY
        text = "How severe would you say it is?" if lang == Language.en else "यह कितना गंभीर महसूस हो रहा है?"
        return ChatResponse(
            session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
            reply_text=text, quick_replies=_quick_replies(SEVERITY_OPTIONS, lang),
            matched_topic=session.matched_topic_id,
        )

    if session.stage == Stage.AWAITING_SEVERITY:
        try:
            session.severity = Severity(message)
        except ValueError:
            session.severity = Severity.mild
        session.severity_label = _label_for(SEVERITY_OPTIONS, lang.value, message)
        session.stage = Stage.AWAITING_AGE
        text = "Who is this for?" if lang == Language.en else "यह जानकारी किसके लिए है?"
        return ChatResponse(
            session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
            reply_text=text, quick_replies=_quick_replies(AGE_OPTIONS, lang),
            matched_topic=session.matched_topic_id,
        )

    if session.stage == Stage.AWAITING_AGE:
        try:
            session.age_group = AgeGroup(message)
        except ValueError:
            session.age_group = AgeGroup.adult
        session.age_label = _label_for(AGE_OPTIONS, lang.value, message)
        session.stage = Stage.AWAITING_REDFLAG_CHECK
        entry = rag_engine.get_entry_by_id(session.matched_topic_id)
        flags = entry["red_flags"][lang.value]
        text = (
            "Last check - are you noticing any of these right now?"
            if lang == Language.en else
            "आखिरी सवाल - क्या अभी आपको इनमें से कोई लक्षण महसूस हो रहा है?"
        )
        chips = [QuickReply(id=f"flag::{i}", label=f) for i, f in enumerate(flags)]
        chips.append(QuickReply(id="none", label="None of these" if lang == Language.en else "इनमें से कोई नहीं"))
        return ChatResponse(
            session_id=session.session_id, triage_level=TriageLevel.NEED_MORE_INFO,
            reply_text=text, quick_replies=chips, matched_topic=session.matched_topic_id,
        )

    if session.stage == Stage.AWAITING_REDFLAG_CHECK:
        if message.startswith("flag::"):
            entry = rag_engine.get_entry_by_id(session.matched_topic_id)
            idx = int(message.split("::")[1])
            flag_text = entry["red_flags"][lang.value][idx]
            session.accumulated_red_flags.append(flag_text)
        session.stage = Stage.DONE
        return _format_final_answer(session)

    session.stage = Stage.AWAITING_SYMPTOM
    session.rephrase_attempts = 0
    _reset_followup_state(session)
    return handle_message(session, message)
