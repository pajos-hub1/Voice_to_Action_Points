import asyncio

from fastapi import APIRouter, Depends, File, UploadFile, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.dependencies import get_transcriber_dep
from voice.base import Transcriber, TranscriptionResult

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe(
    file: UploadFile = File(...),
    transcriber: Transcriber = Depends(get_transcriber_dep),
) -> TranscriptionResult:
    audio_bytes = await file.read()
    # transcribe_file() is blocking (Azure Speech SDK, or the mock's sleep).
    # asyncio.to_thread keeps it off the event loop — keep this offload if
    # this handler is ever changed.
    return await asyncio.to_thread(transcriber.transcribe_file, audio_bytes, file.content_type or "audio/wav")


@router.websocket("/transcribe/stream")
async def transcribe_stream(
    websocket: WebSocket,
    transcriber: Transcriber = Depends(get_transcriber_dep),
) -> None:
    await websocket.accept()

    async def audio_chunks():
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            data = message.get("bytes")
            if data is not None:
                yield data
            elif message.get("text") == "EOS":
                return

    try:
        async for result in transcriber.stream(audio_chunks()):
            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        return

    await websocket.close()
