import asyncio
import time
from typing import AsyncIterator

from voice.base import Transcriber, TranscriptionResult

DEFAULT_TRANSCRIPT = "please schedule a meeting with the design team for tomorrow at 3pm"


class MockTranscriber(Transcriber):
    """Deterministic stand-in for Azure Speech, so the app runs with zero credentials."""

    def __init__(
        self,
        canned_text: str = DEFAULT_TRANSCRIPT,
        confidence: float = 0.93,
        simulated_latency_s: float = 0.05,
    ):
        self._canned_text = canned_text
        self._confidence = confidence
        self._simulated_latency_s = simulated_latency_s

    def transcribe_file(self, audio_bytes: bytes, content_type: str = "audio/wav") -> TranscriptionResult:
        start = time.perf_counter()
        time.sleep(self._simulated_latency_s)
        return TranscriptionResult(
            text=self._canned_text,
            confidence=self._confidence,
            language="en-US",
            is_final=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[TranscriptionResult]:
        start = time.perf_counter()
        words = self._canned_text.split()
        chunk_count = 0

        async for _ in audio_chunks:
            chunk_count += 1
            word_count = chunk_count // 2
            if chunk_count % 2 == 0 and word_count <= len(words):
                await asyncio.sleep(self._simulated_latency_s)
                yield TranscriptionResult(
                    text=" ".join(words[:word_count]),
                    confidence=0.0,
                    is_final=False,
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

        await asyncio.sleep(self._simulated_latency_s)
        yield TranscriptionResult(
            text=self._canned_text,
            confidence=self._confidence,
            language="en-US",
            is_final=True,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
