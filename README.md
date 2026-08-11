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

State machine: `CREATED -> PENDING_APPROVAL -> APPROVED -> EXECUTED`, with `PENDING_APPROVAL -> REJECTED` as the only other exit. Execution is enforced server-side (`executor/run.py`) independent of the API layer — approval can't be bypassed by calling the executor directly.

## Status

All phases from `plan.txt` are complete.

- [x] Phase 0 — Setup
- [x] Phase 1 — Transcription
- [x] Phase 2 — Intent extraction + Action Points
- [x] Phase 3 — Human approval gate
- [x] Phase 4 — Executor + audit log
- [x] Phase 5 — Wiring, metrics, polish

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

## End-to-end walkthrough (curl)

Every request is logged with its latency and returns an `X-Process-Time-Ms` header (FR-11).

**1. Transcribe** an audio file (mock backend returns a canned transcript):

```bash
curl -s -F "file=@sample.wav;type=audio/wav" localhost:8000/transcribe
# {"text":"please schedule a meeting with the design team for tomorrow at 3pm","confidence":0.93,...}
```

For real-time streaming, connect to `ws://localhost:8000/transcribe/stream`, send binary audio chunks, then send the text message `EOS` to get partial results followed by a final one.

**2. Propose** an Action Point from the transcript (runs intent extraction, validates against the schema, persists with `PENDING_APPROVAL`):

```bash
ID=$(curl -s -X POST localhost:8000/action-points \
  -H "Content-Type: application/json" \
  -d '{"transcript":"please schedule a meeting with the design team for tomorrow at 3pm","confidence":0.93}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
```

**3. Try to execute early — blocked** (this is the control point; nothing runs without approval):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/action-points/$ID/execute
# 409
```

**4. Approve or reject** — a human makes the call:

```bash
curl -s -X POST localhost:8000/action-points/$ID/approve -H "Content-Type: application/json" -d '{"approver":"alice"}'
# status: APPROVED

# or, to reject instead:
# curl -s -X POST localhost:8000/action-points/$ID/reject -H "Content-Type: application/json" -d '{"approver":"alice","reason":"not needed"}'
```

**5. Execute** the approved Action Point against the mock integrations:

```bash
curl -s -X POST localhost:8000/action-points/$ID/execute
# status: EXECUTED, execution_result: {...}
```

**6. Audit** — every step is traceable to the transcript and the approver:

```bash
curl -s "localhost:8000/audit-log?action_point_id=$ID"
# [{"event_type":"PROPOSED",...}, {"event_type":"APPROVED","actor":"alice",...}, {"event_type":"EXECUTED",...}]
```

Other useful endpoints: `GET /action-points` (list, optional `?status_filter=`), `GET /action-points/{id}` (detail), `GET /audit-log` (all events, no filter).

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

## Docker

```bash
docker compose up --build
```

Local development only: this automatically loads `docker-compose.override.yml`, which bind-mounts your source tree and runs uvicorn with `--reload`, so edits apply without rebuilding.

For production, deploy the baked image without the override so the container runs exactly what was built:

```bash
docker compose -f docker-compose.yml up --build
```

Both run the app against the bundled Postgres service. Set `DATABASE_URL=postgresql://voice_to_action_points:voice_to_action_points@db:5432/voice_to_action_points` in `.env` to use it instead of the default SQLite file.
