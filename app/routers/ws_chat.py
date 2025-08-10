from __future__ import annotations

import json
import uuid
import logging
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query  # type: ignore

from app.services import chat, stt, tts
from app.services.chat import THERAPIST_SYSTEM_PROMPT
from app.infra.config import settings  # reuse existing settings helper

# ---------------- Logging setup (prod config) ----------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

router = APIRouter()

# ------------- Per-session conversation memory -------------
_CONVERSATIONS: Dict[str, List[dict]] = {}


def _get_history(session_id: str) -> List[dict]:
    if session_id not in _CONVERSATIONS:
        _CONVERSATIONS[session_id] = [
            {"role": "system", "content": THERAPIST_SYSTEM_PROMPT},
        ]
    return _CONVERSATIONS[session_id]


# ---------------------------------------------------------------------------
# Protocol message tags 
# ---------------------------------------------------------------------------
CLIENT = {"END": "end"}
SERVER = {
    "TRANSCRIPT": "transcript",
    "ASSISTANT_TEXT": "assistant_text",
    "AUDIO_END": "audio_end",
}

# ---------------- DEV STUB HELPERS  ---------------

# Uncomment to bypass real services during dev.
# HARDCODED_TRANSCRIPT = "I understand. How are you feeling now?"
# HARDCODED_ASSISTANT_REPLY = "I'm here for you. Take your time."
# def dev_stub_transcript() -> str:
#     """Return hard-coded transcript (dev only)."""
#     return "I understand. How are you feeling now?"  # dev stub

# async def dev_stub_chat(history: list[dict]) -> str:
#     """Return hard-coded assistant reply (dev only)."""
#     return "I'm here for you. Take your time."  # dev stub

# async def dev_stream_sample_audio(websocket: WebSocket, *, chunk_size: int = 4096):
#     """Stream a local MP3 for rapid UI testing (dev only)."""
#     sample_path = Path(__file__).resolve().parents[2] / "data" / "audio.mp3"
#     try:
#         with open(sample_path, "rb") as fp:
#             while (chunk := fp.read(chunk_size)):
#                 await websocket.send_bytes(chunk)
#     except FileNotFoundError:
#         logger.warning("Sample audio missing: %s", sample_path)
#     finally:
#         await websocket.send_json({"type": SERVER["AUDIO_END"]})

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
async def _receive_full_utterance(websocket: WebSocket) -> bytearray:
    """Accumulate binary mic data until the client sends `{type:'end'}`."""
    buf = bytearray()
    while True:
        pkt = await websocket.receive()
        if isinstance(pkt.get("bytes"), (bytes, bytearray)):
            buf.extend(pkt["bytes"])
            continue
        try:
            msg = json.loads(pkt.get("text") or "{}")
        except json.JSONDecodeError:
            continue
        if msg.get("type") == CLIENT["END"]:
            return buf  # utterance finished


async def _stream_tts_audio(websocket: WebSocket, text: str):
    """Stream TTS bytes and send AUDIO_END when finished."""
    try:
        if settings.use_deepgram and settings.deepgram_api_key:
            byte_iter = tts.synthesize_stream_deepgram(text)
        else:
            byte_iter = tts.synthesize_stream(text)

        async for chunk in byte_iter:
            await websocket.send_bytes(chunk)
    finally:
        await websocket.send_json({"type": SERVER["AUDIO_END"]})


async def _send_assistant_text(websocket: WebSocket, text: str, *, partial: bool):
    await websocket.send_json({
        "type": SERVER["ASSISTANT_TEXT"],
        "text": text,
        "partial": partial,
    })


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/chat")
async def websocket_chat_v2(
    websocket: WebSocket,
    session_id: str | None = Query(None, description="Conversation/session identifier"),
):
    """Unified STT → Chat → TTS flow (stub, but structured)."""

    await websocket.accept()
    sid = session_id or str(uuid.uuid4())
    history = _get_history(sid)
    turn_counter = 0  # increment each user utterance

    try:
        while True: 
            # 1. Capture the complete user utterance -------------------------
            recording_buf = await _receive_full_utterance(websocket)
            logger.info("Utterance received – %d bytes", len(recording_buf))
            # 2. Transcribe audio -------------------------------------------
            try:
                transcript_text = await stt.transcribe_bytes(bytes(recording_buf), session_id=sid, turn=turn_counter)
            except Exception as exc:  # pragma: no cover – log & inform client
                logger.exception("STT failed: %s", exc)
                await websocket.send_json({"type": "error", "stage": "stt", "detail": str(exc)})
                continue  # allow next turn

            await websocket.send_json({"type": SERVER["TRANSCRIPT"], "text": transcript_text})
            history.append({"role": "user", "content": transcript_text})

            # 3. Chat completion (streaming) --------------------------------
            try:
                assistant_text_full = ""
                async for delta in chat.generate_stream(history):
                    assistant_text_full += delta
                    await _send_assistant_text(websocket, delta, partial=True)
                await _send_assistant_text(websocket, assistant_text_full, partial=False)
            except Exception as exc:
                logger.exception("Chat generation failed: %s", exc)
                await websocket.send_json({"type": "error", "stage": "chat", "detail": str(exc)})
                continue

            history.append({"role": "assistant", "content": assistant_text_full})

            # 4. Stream TTS audio -------------------------------------------
            await _stream_tts_audio(websocket, assistant_text_full)

            recording_buf.clear()
            turn_counter += 1  # prep for next turn

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        return
    except Exception as exc:  # pragma: no cover
        logger.exception("Unhandled error in chat_v2 handler: %s", exc)
        return 