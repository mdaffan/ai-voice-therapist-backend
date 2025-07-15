# Voice-Therapist Backend

FastAPI application providing STT ↔ GPT-4o ↔ TTS glue for the Voice-Therapist MVP.

---

## 1 Architecture

```mermaid
graph TD
  subgraph "Client (Browser)"
    UI["React + Vite\n(Click-to-talk UI)"]
  end
  subgraph "Server (FastAPI)"
    STT_EP["/stt endpoint"]
    CHAT_EP["/chat_stream endpoint"]
    TTS_EP["/tts_stream endpoint"]
    
    subgraph "STT Services"
      OPENAI_STT["OpenAI Whisper\n(Default)"]
      DEEPGRAM_STT["Deepgram STT\n(if USE_DEEPGRAM=true)"]
    end
    
    subgraph "Chat Services"
      LITELLM["LiteLLM Router"]
      OPENAI_CHAT["OpenAI GPT-4o\n(Primary)"]
      CLAUDE["Claude Opus\n(Fallback)"]
    end
    
    subgraph "TTS Services"
      OPENAI_TTS["OpenAI TTS\n(Default)"]
      DEEPGRAM_TTS["Deepgram TTS\n(if USE_DEEPGRAM=true)"]
    end
  end
  subgraph "Vendors"
    OPENAI_API["OpenAI APIs"]
    DEEPGRAM_API["Deepgram APIs"]
    ANTHROPIC["Anthropic API"]
  end

  UI -- "audio file" --> STT_EP
  STT_EP -- "transcript" --> UI
  UI -- "text" --> CHAT_EP
  CHAT_EP -- "SSE tokens" --> UI
  CHAT_EP -- "assistant text" --> TTS_EP
  TTS_EP -- "audio stream" --> UI

  STT_EP --> OPENAI_STT
  STT_EP --> DEEPGRAM_STT
  OPENAI_STT --> OPENAI_API
  DEEPGRAM_STT --> DEEPGRAM_API
  
  CHAT_EP --> LITELLM
  LITELLM --> OPENAI_CHAT
  LITELLM --> CLAUDE
  OPENAI_CHAT --> OPENAI_API
  CLAUDE --> ANTHROPIC
  
  TTS_EP --> OPENAI_TTS
  TTS_EP --> DEEPGRAM_TTS
  OPENAI_TTS --> OPENAI_API
  DEEPGRAM_TTS --> DEEPGRAM_API




```

Directory layout:

```
voice-therapist-server/app
├─ main.py          ← declares HTTP endpoints (/stt, /chat_stream, /tts_stream, /health)
├─ services/        ← whisper, chat (LiteLLM), TTS wrappers
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

| Endpoint | Payload |
|----------|---------|
| `POST /stt` | multipart `speech.webm`, `session_id` (form-data) |
| `POST /chat_stream` | `{ "text": "hi", "session_id": "uuid" }` |
| `POST /tts_stream` | `{ "text": "hello" }` |