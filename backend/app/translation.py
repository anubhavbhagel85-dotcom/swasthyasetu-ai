"""
Language + voice helpers.

Core text flow: the knowledge base already stores every entry in both
English and Hindi, so no runtime translation call is needed for the
must-have text flow — this keeps the demo fast and free of external
API flakiness during judging.

Bonus voice flow: wraps the Government of India's Bhashini API
(https://bhashini.gov.in, free developer tier) for Hindi speech-to-text
and text-to-speech. If BHASHINI_USER_ID / BHASHINI_API_KEY are not set,
`bhashini_enabled` is False and the frontend automatically falls back to
the browser's built-in Web Speech API instead — so the demo never breaks
on stage for lack of a registered API key.
"""
import re
import httpx

from app.config import BHASHINI_ENABLED, BHASHINI_USER_ID, BHASHINI_API_KEY, BHASHINI_PIPELINE_ID

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

BHASHINI_PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


def detect_language(text: str) -> str:
    """Very lightweight script-based detector: if the message contains
    Devanagari characters, treat it as Hindi; otherwise English. This is
    intentionally simple — good enough to auto-switch the reply language
    when a user types in Hindi even if the UI toggle is set to English."""
    return "hi" if _DEVANAGARI_RE.search(text) else "en"


async def speech_to_text_hindi(audio_base64: str) -> str:
    """Send base64-encoded audio to Bhashini ASR and return the Hindi
    transcript. Raises RuntimeError if Bhashini credentials are not
    configured (frontend should fall back to Web Speech API in that case).
    """
    if not BHASHINI_ENABLED:
        raise RuntimeError("Bhashini is not configured. Set BHASHINI_USER_ID and BHASHINI_API_KEY.")

    payload = {
        "pipelineTasks": [{
            "taskType": "asr",
            "config": {"language": {"sourceLanguage": "hi"}, "serviceId": BHASHINI_PIPELINE_ID},
        }],
        "inputData": {"audio": [{"audioContent": audio_base64}]},
    }
    headers = {"userID": BHASHINI_USER_ID, "ulcaApiKey": BHASHINI_API_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(BHASHINI_PIPELINE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["pipelineResponse"][0]["output"][0]["source"]


async def text_to_speech_hindi(text: str) -> str:
    """Send Hindi text to Bhashini TTS and return base64-encoded audio."""
    if not BHASHINI_ENABLED:
        raise RuntimeError("Bhashini is not configured. Set BHASHINI_USER_ID and BHASHINI_API_KEY.")

    payload = {
        "pipelineTasks": [{
            "taskType": "tts",
            "config": {"language": {"sourceLanguage": "hi"}, "serviceId": BHASHINI_PIPELINE_ID},
        }],
        "inputData": {"input": [{"source": text}]},
    }
    headers = {"userID": BHASHINI_USER_ID, "ulcaApiKey": BHASHINI_API_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(BHASHINI_PIPELINE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["pipelineResponse"][0]["audio"][0]["audioContent"]
