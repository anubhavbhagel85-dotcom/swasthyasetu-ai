from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import APP_NAME, APP_VERSION, ALLOWED_ORIGINS, BHASHINI_ENABLED
from app.schemas import StartRequest, StartResponse, ChatRequest, ChatResponse, HealthResponse, Source
from app import conversation, rag_engine, translation

# In-memory store for transcripts of conversations that happened fully
# offline (client-side engine) and get synced back once connectivity
# returns. A real deployment would persist this to a database; for the
# hackathon MVP this exists mainly to prove the sync round-trip works.
OFFLINE_SYNC_LOG: List[dict] = []

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Multilingual symptom guidance API with a source-backed RAG layer "
                 "and an independent safety/triage layer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", version=APP_VERSION, knowledge_base_entries=len(rag_engine.ENTRIES))


@app.get("/api/sources", response_model=list[Source])
def sources():
    """Every verified source cited anywhere in the knowledge base — powers a
    transparent 'Verified Sources' page in the frontend."""
    return [Source(**s) for s in rag_engine.list_all_sources()]


@app.post("/api/chat/start", response_model=StartResponse)
def start_chat(req: StartRequest):
    session = conversation.start_session(req.language)
    return StartResponse(
        session_id=session.session_id,
        message=conversation._welcome_text(req.language),
        language=req.language,
    )


@app.post("/api/chat/message", response_model=ChatResponse)
def send_message(req: ChatRequest):
    session = conversation.SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id. Call /api/chat/start first.")

    # Let a user typing in Hindi auto-flip the reply language even if the
    # session started in English.
    detected = translation.detect_language(req.message)
    if detected == "hi" and session.language.value == "en" and len(req.message) > 3:
        session.language = req.language if req.language else session.language

    return conversation.handle_message(session, req.message)


class VoiceTranscribeRequest(BaseModel):
    audio_base64: str


class VoiceTranscribeResponse(BaseModel):
    transcript: str


@app.post("/api/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe(req: VoiceTranscribeRequest):
    """Bonus endpoint: Hindi speech-to-text via Bhashini. Returns 503 if
    Bhashini credentials are not configured, so the frontend can silently
    fall back to the browser's Web Speech API."""
    if not BHASHINI_ENABLED:
        raise HTTPException(status_code=503, detail="Bhashini not configured on this server.")
    transcript = await translation.speech_to_text_hindi(req.audio_base64)
    return VoiceTranscribeResponse(transcript=transcript)


class OfflineTurn(BaseModel):
    role: str  # "user" | "assistant"
    text: str
    triage_level: Optional[str] = None
    matched_topic: Optional[str] = None


class SyncRequest(BaseModel):
    session_id: str
    language: str
    turns: List[OfflineTurn]


class SyncResponse(BaseModel):
    received_turns: int
    server_time: str


@app.post("/api/sync", response_model=SyncResponse)
def sync_offline_transcript(req: SyncRequest):
    """Bonus 'offline messaging' feature: when the frontend has been running
    on the on-device fallback engine (see frontend/src/offline/offlineEngine.js)
    because the network was down, it calls this endpoint once connectivity
    returns to hand over the transcript for continuity/analytics. This is
    intentionally a fire-and-forget log, NOT a re-answering of the
    conversation — the on-device answers already used the same cited
    knowledge base, so nothing needs to be recomputed server-side."""
    OFFLINE_SYNC_LOG.append({
        "session_id": req.session_id,
        "language": req.language,
        "turns": [t.model_dump() for t in req.turns],
        "synced_at": datetime.now(timezone.utc).isoformat(),
    })
    return SyncResponse(received_turns=len(req.turns), server_time=datetime.now(timezone.utc).isoformat())


@app.get("/")
def root():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "endpoints": [
            "/api/health", "/api/sources", "/api/chat/start", "/api/chat/message",
            "/api/voice/transcribe", "/api/sync",
        ],
    }
