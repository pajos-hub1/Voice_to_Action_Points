from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_transcribe_file_mock_backend() -> None:
    files = {"file": ("sample.wav", b"\x00\x01fake-audio-bytes", "audio/wav")}
    response = client.post("/transcribe", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["text"]
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["is_final"] is True
    assert body["latency_ms"] >= 0


def test_transcribe_stream_mock_backend() -> None:
    with client.websocket_connect("/transcribe/stream") as websocket:
        for _ in range(6):
            websocket.send_bytes(b"chunk")
        websocket.send_text("EOS")

        results = []
        while True:
            message = websocket.receive_json()
            results.append(message)
            if message["is_final"]:
                break

        assert len(results) >= 2
        assert results[-1]["is_final"] is True
        assert results[-1]["text"]
        assert all(not r["is_final"] for r in results[:-1])
