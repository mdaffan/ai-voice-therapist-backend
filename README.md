# Voice Therapist Backend (FastAPI + uv)

## Setup
```bash
cd voice-therapist-server
cp .env.example .env  # add your keys
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

## Development server
```bash
./scripts/dev.sh
# → http://localhost:8000/docs
```

## API
| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/stt` | multipart file `speech.webm` | `{ "text": "..." }` |
| POST | `/chat` | `{ "text": "hello" }` | `{ "response": "..." }` |
| POST | `/tts` | `{ "text": "hello" }` | `audio/mpeg` stream | 