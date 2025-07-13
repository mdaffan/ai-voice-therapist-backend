# Voice-Therapist Backend

FastAPI application providing STT ↔ GPT-4o ↔ TTS glue for the Voice-Therapist MVP.

---

## 1 Architecture

```
┌───────────┐   REST / SSE   ┌──────────────────┐
│  Routers  │──────────────▶│  Service layer   │
└────┬──────┘                └────────┬─────────┘
     │ include_router()                 │
     ▼                                  ▼
  FastAPI app                  3rd-party vendors (OpenAI, Anthropic …)
```

Directory layout:

```
voice-therapist-server/app
├─ main.py          ← creates FastAPI app & plugs routers
├─ routers/         ← HTTP endpoints (chat, stt, tts, health)
├─ services/        ← thin wrappers around vendor SDKs
└─ infra/
   └─ config.py     ← typed env-loader (Pydantic)
```

## 2 Quick-start (local)

```bash
# 1. clone repo
cd voice-therapist-server

# 2. create .env with your keys
cp .env.example .env
echo "OPENAI_API_KEY=sk-…"      >> .env
echo "ANTHROPIC_API_KEY=sk-…"   >> .env

# 3. install deps (requires Python ≥3.10)
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 4. run dev server
./scripts/dev.sh        # http://localhost:9000/docs
```

## 3 Docker

```bash
# Build & run container (port 9000)
docker build -f Dockerfile -t voice-therapist-server .
docker run -p 9000:9000 --env-file .env voice-therapist-server
```

## 4 Endpoints

| Method | Path           | Body                                             | Returns                       |
|--------|---------------|--------------------------------------------------|--------------------------------|
| POST   | `/stt`        | multipart file `speech.webm` + `session_id` etc. | `{ "text": "…" }`              |
| POST   | `/chat`       | `{ "text": "hi", "session_id": "uuid" }`          | `{ "response": "…" }`           |
| POST   | `/chat_stream`| same as above                                    | `text/event-stream`            |
| POST   | `/tts`        | `{ "text": "hello" }`                           | `audio/mpeg` (full)            |
| POST   | `/tts_stream` | `{ "text": "hello" }`                           | `audio/mpeg` (chunked stream)  |

---

### Configuration reference (`.env`)

```
# Vendor keys
OPENAI_API_KEY=sk-…
ANTHROPIC_API_KEY=sk-…

# Optional overrides
GPT_MODEL=gpt-4o
CLAUDE_MODEL=anthropic/claude-3-7-sonnet-latest
STT_MODEL=whisper-1
TTS_MODEL=tts-1
PORT=9000
``` 