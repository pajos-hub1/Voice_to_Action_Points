import asyncio
import json
import tempfile
import time
from typing import Any, AsyncIterator

import azure.cognitiveservices.speech as speechsdk

from voice.base import Transcriber, TranscriptionResult


class AzureTranscriber(Transcriber):
    """Real Azure Speech SDK backend. Requires AZURE_SPEECH_KEY / AZURE_SPEECH_REGION."""

    def __init__(self, speech_key: str, region: str):
        self._speech_key = speech_key
        self._region = region

    def _speech_config(self) -> speechsdk.SpeechConfig:
        return speechsdk.SpeechConfig(subscription=self._speech_key, region=self._region)

    def transcribe_file(self, audio_bytes: bytes, content_type: str = "audio/wav") -> TranscriptionResult:
        start = time.perf_counter()
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            audio_config = speechsdk.audio.AudioConfig(filename=tmp.name)
            recognizer = speechsdk.SpeechRecognizer(speech_config=self._speech_config(), audio_config=audio_config)
            result = recognizer.recognize_once()

        latency_ms = (time.perf_counter() - start) * 1000
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            raise RuntimeError(f"Azure transcription failed: {result.reason}")

        return TranscriptionResult(
            text=result.text,
            confidence=self._extract_confidence(result),
            is_final=True,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_confidence(result: Any) -> float:
        try:
            best = json.loads(result.json)["NBest"][0]
            return float(best["Confidence"])
        except (KeyError, IndexError, ValueError, TypeError):
            return 0.9

    async def stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[TranscriptionResult]:
        start = time.perf_counter()
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=self._speech_config(), audio_config=audio_config)

        def on_recognizing(evt: Any) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                TranscriptionResult(
                    text=evt.result.text,
                    confidence=0.0,
                    is_final=False,
                    latency_ms=(time.perf_counter() - start) * 1000,
                ),
            )

        def on_recognized(evt: Any) -> None:
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    TranscriptionResult(
                        text=evt.result.text,
                        confidence=self._extract_confidence(evt.result),
                        is_final=True,
                        latency_ms=(time.perf_counter() - start) * 1000,
                    ),
                )

        def on_stopped(evt: Any) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, None)

        recognizer.recognizing.connect(on_recognizing)
        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_stopped)
        recognizer.canceled.connect(on_stopped)

        recognizer.start_continuous_recognition()

        async def feed() -> None:
            async for chunk in audio_chunks:
                await asyncio.to_thread(push_stream.write, chunk)
            push_stream.close()
            await asyncio.to_thread(recognizer.stop_continuous_recognition)

        feed_task = asyncio.create_task(feed())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        await feed_task
