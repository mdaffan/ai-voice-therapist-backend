from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from pathlib import Path
import os
from app.services import stt, chat, tts
# set api keys 

# Import service layer
from app.services import stt, chat, tts
# ---------------- Conversation memory ------------------
from typing import Dict, List

# Hold conversation history across requests (simple in-memory store)
_CONVERSATIONS: Dict[str, List[dict]] = {}

def _get_history(session_id: str) -> List[dict]:
    """Return the conversation list for a session, initialising with system prompt."""
    if session_id not in _CONVERSATIONS:
        from app.services.chat import THERAPIST_SYSTEM_PROMPT  # avoid circular issues

        _CONVERSATIONS[session_id] = [
            {"role": "system", "content": THERAPIST_SYSTEM_PROMPT},
        ]
    return _CONVERSATIONS[session_id]

# Import settings to ensure env vars are populated
from app.infra.config import settings  # noqa: E402  pylint: disable=wrong-import-position

# Persist uploaded audio under ../../data/<session>/<turn>.webm
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Voice Therapist API",
    version="0.1.0",
    summary="Low-latency voice ↔ GPT-4o backend"
)

# Allow dev UI; restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    turn: int = Form(...)
):
    """Save the uploaded blob and run STT on the saved file."""

    audio_bytes = await file.read()

    # ---------- persist to disk ----------
    safe_session = session_id.replace("..", "")  # rudimentary sanitisation
    session_dir = DATA_DIR / safe_session
    session_dir.mkdir(parents=True, exist_ok=True)
    audio_path = session_dir / f"{turn}.webm"

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # ---------- transcribe ----------
    text = await stt.transcribe_file(str(audio_path))
    return {"text": text}





# Streaming chat completion (Server-Sent Events)
@app.post("/chat_stream")
async def chat_completion_stream(body: dict):
    text = body.get("text")
    session_id = body.get("session_id", "default")

    if not text:
        raise HTTPException(400, detail="`text` field missing")

    history = _get_history(session_id)
    history.append({"role": "user", "content": text})

    async def _event_generator():
        assistant_text_accum = ""
        async for token in chat.generate_stream(history):
            assistant_text_accum += token
            # SSE format requires lines starting with 'data:' and ended by a blank line
            yield f"data: {token}\n\n"

        # After streaming is done, append assistant full reply to history
        history.append({"role": "assistant", "content": assistant_text_accum})

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
    )




# Streaming TTS endpoint
@app.post("/tts_stream")
async def tts_stream(body: dict):
    text = body.get("text")
    if not text:
        raise HTTPException(400, detail="`text` field missing")

    async def _gen():
        async for chunk in tts.synthesize_stream_deepgram(text):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=reply.mp3"},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}