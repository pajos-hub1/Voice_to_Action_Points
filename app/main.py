from fastapi import FastAPI

app = FastAPI(
    title="Voice-to-Action-Points Assistant",
    description="Speak an instruction, get a structured Action Point, approve it, and only then does the system act.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
