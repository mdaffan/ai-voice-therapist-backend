from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from pathlib import Path
import os
from app import stt, chat, tts
# set api keys 


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


@app.post("/chat")
async def chat_completion(body: dict):
    text = body.get("text")
    if not text:
        raise HTTPException(400, detail="`text` field missing")
    answer = await chat.generate(text)
    return {"response": answer}


@app.post("/tts")
async def text_to_speech(body: dict):
    text = body.get("text")
    if not text:
        raise HTTPException(400, detail="`text` field missing")
    mp3_bytes = await tts.synthesize(text)
    return StreamingResponse(
        io.BytesIO(mp3_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=reply.mp3"}
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}