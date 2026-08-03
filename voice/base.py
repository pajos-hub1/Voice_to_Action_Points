from abc import ABC, abstractmethod
from typing import AsyncIterator

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: str | None = None
    is_final: bool = True
    latency_ms: float


class Transcriber(ABC):
    @abstractmethod
    def transcribe_file(self, audio_bytes: bytes, content_type: str = "audio/wav") -> TranscriptionResult:
        """Transcribe a complete audio file (blocking; run off the event loop)."""

    @abstractmethod
    def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[TranscriptionResult]:
        """Transcribe a live audio stream, yielding partial results then a final one."""
