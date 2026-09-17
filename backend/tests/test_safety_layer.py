from app import safety_layer, rag_engine, conversation
from app.schemas import Language, TriageLevel, Severity, AgeGroup


def test_global_emergency_detects_chest_pain():
    result = safety_layer.check_global_emergency("I have severe chest pain", Language.en)
    assert result is not None
    assert result.triage_level == TriageLevel.EMERGENCY


def test_global_emergency_detects_hindi_phrase():
    result = safety_layer.check_global_emergency("मुझे सांस नहीं आ रही", Language.hi)
    assert result is not None


def test_no_emergency_for_mild_symptom():
    result = safety_layer.check_global_emergency("I have a mild headache", Language.en)
    assert result is None


def test_retrieval_matches_fever_keyword():
    hits = rag_engine.retrieve("bukhar hai")
    assert hits
    assert hits[0].entry["id"] == "fever"


def test_retrieval_matches_english_fever():
    hits = rag_engine.retrieve("I have a high fever since yesterday")
    assert hits
    assert hits[0].entry["id"] == "fever"


def test_escalation_never_downgrades_emergency():
    level = safety_layer.escalate_from_followups(
        base_level=TriageLevel.EMERGENCY, severity=Severity.mild,
        duration_days=1, age_group=AgeGroup.adult,
    )
    assert level == TriageLevel.EMERGENCY


def test_escalation_severe_symptom_becomes_urgent():
    level = safety_layer.escalate_from_followups(
        base_level=TriageLevel.SELF_CARE, severity=Severity.severe,
        duration_days=1, age_group=AgeGroup.adult,
    )
    assert level == TriageLevel.URGENT


def test_every_kb_entry_has_a_verified_source():
    for entry in rag_engine.ENTRIES:
        assert entry.get("sources"), f"{entry['id']} is missing a verified source"
        for src in entry["sources"]:
            assert src["url"].startswith("https://")


def test_always_urgent_topics_have_no_home_remedies():
    for topic_id in ("chest_pain", "breathing_difficulty"):
        entry = rag_engine.get_entry_by_id(topic_id)
        assert entry.get("home_remedies") is None


def test_home_remedy_entries_have_their_own_citation():
    for entry in rag_engine.ENTRIES:
        if entry.get("home_remedies"):
            assert entry.get("remedy_sources"), f"{entry['id']} has home remedies but no remedy_sources"
            assert entry.get("remedy_caution"), f"{entry['id']} has home remedies but no caution text"


def test_full_conversation_flow_reaches_final_answer_with_recap():
    session = conversation.start_session(Language.en)
    r1 = conversation.handle_message(session, "I have had a fever since yesterday")
    assert r1.triage_level == TriageLevel.NEED_MORE_INFO
    assert session.stage == conversation.Stage.AWAITING_TOPIC_CONFIRMATION

    conversation.handle_message(session, "yes")
    assert session.stage == conversation.Stage.AWAITING_DURATION

    conversation.handle_message(session, "today")
    assert session.stage == conversation.Stage.AWAITING_SEVERITY

    conversation.handle_message(session, "mild")
    assert session.stage == conversation.Stage.AWAITING_AGE

    conversation.handle_message(session, "adult")
    assert session.stage == conversation.Stage.AWAITING_REDFLAG_CHECK

    r6 = conversation.handle_message(session, "none")
    assert r6.is_final is True
    assert r6.triage_level == TriageLevel.SELF_CARE
    assert r6.recap is not None and "Fever" in r6.recap
    assert r6.sources, "final answer must carry verified sources"
    assert r6.home_remedies, "fever should surface home remedies at SELF_CARE level"
    assert r6.remedy_sources


def test_topic_rejection_lets_user_rephrase():
    session = conversation.start_session(Language.en)
    conversation.handle_message(session, "I have a headache")
    assert session.stage == conversation.Stage.AWAITING_TOPIC_CONFIRMATION

    conversation.handle_message(session, "no")
    assert session.stage == conversation.Stage.AWAITING_SYMPTOM
    assert session.matched_topic_id is None


def test_emergency_skips_home_remedies_even_for_normally_self_care_topic():
    session = conversation.start_session(Language.en)
    conversation.handle_message(session, "I have had a fever since yesterday")
    conversation.handle_message(session, "yes")
    conversation.handle_message(session, "today")
    conversation.handle_message(session, "severe")
    conversation.handle_message(session, "senior")
    r = conversation.handle_message(session, "flag::0")
    assert r.triage_level in (TriageLevel.URGENT, TriageLevel.EMERGENCY)
    assert r.home_remedies == []
