from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io

from app import stt, chat, tts

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
async def speech_to_text(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = await stt.transcribe_bytes(audio_bytes)
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