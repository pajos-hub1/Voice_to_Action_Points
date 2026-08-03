# Voice-to-Action-Points Assistant

A real-time assistant that turns spoken instructions into structured, reviewable **Action Points**. A user speaks; the system transcribes the audio, understands the intent, and produces a clear, structured action proposal — but nothing executes until a human explicitly approves it. The AI proposes, the human disposes.

Full spec: [`Voice_to_Action_Points_PRD.docx`](./Voice_to_Action_Points_PRD.docx). Implementation plan: [`plan.txt`](./plan.txt).

## Pipeline

```
mic / audio file
  -> Transcribe (Azure Speech SDK, or mock)      -> transcript + confidence
  -> Understand (OpenAI intent extraction, or mock) -> intent + entities
  -> Structure (Pydantic Action Point schema)     -> status = PENDING_APPROVAL
  -> Human approval gate (approve / reject)        <== the control point
  -> Execute (mock integrations, only if APPROVED)
  -> Append-only audit log
```

## Status

This project is being built one phase at a time. See `plan.txt` for the full breakdown; each phase is implemented, tested, and reviewed before moving to the next.

- [x] Phase 0 — Setup
- [x] Phase 1 — Transcription
- [x] Phase 2 — Intent extraction + Action Points
- [x] Phase 3 — Human approval gate
- [x] Phase 4 — Executor + audit log
- [ ] Phase 5 — Wiring, metrics, polish

## Setup

Runs entirely on mock backends by default — no Azure or OpenAI keys required.

```bash
python -m venv venv        # already created
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

```bash
curl localhost:8000/health
# {"status":"ok"}
```

## Test

```bash
pytest
```

## Switching to real Azure Speech / OpenAI

Set in `.env`:

```
TRANSCRIBER_BACKEND=azure
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...

INTENT_BACKEND=openai
OPENAI_API_KEY=...
```

No code changes needed — both backends are selected via a factory behind a shared interface.
