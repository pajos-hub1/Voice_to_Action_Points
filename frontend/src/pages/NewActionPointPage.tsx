import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { transcribeFile } from "../api/transcribe";
import { AudioRecorder } from "../components/AudioRecorder";
import { useCreateActionPoint } from "../hooks/useActionPoints";

export function NewActionPointPage() {
  const navigate = useNavigate();
  const [transcript, setTranscript] = useState("");
  const [confidence, setConfidence] = useState(0);
  const [hasTranscript, setHasTranscript] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const transcribeMutation = useMutation({
    mutationFn: ({ audio, filename }: { audio: Blob; filename: string }) => transcribeFile(audio, filename),
  });
  const createMutation = useCreateActionPoint();

  async function handleCapture(audio: Blob, filename: string) {
    setError(null);
    try {
      const result = await transcribeMutation.mutateAsync({ audio, filename });
      setTranscript(result.text);
      setConfidence(result.confidence);
      setHasTranscript(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Transcription failed.");
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!transcript.trim()) return;
    setError(null);
    try {
      const actionPoint = await createMutation.mutateAsync({ transcript: transcript.trim(), confidence });
      navigate(`/action-points/${actionPoint.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create action point.");
    }
  }

  return (
    <div className="page">
      <h1>New Action Point</h1>
      <p className="page-subtitle">
        Speak or upload an instruction. Nothing executes until you review and approve the proposal.
      </p>

      <AudioRecorder onCapture={handleCapture} disabled={transcribeMutation.isPending} />
      {transcribeMutation.isPending && <p>Transcribing...</p>}

      {hasTranscript && (
        <form className="review-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="transcript">
            Transcript (edit if needed)
          </label>
          <textarea
            id="transcript"
            className="textarea"
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
            rows={4}
          />
          <p className="page-subtitle">confidence: {(confidence * 100).toFixed(0)}%</p>
          <button type="submit" className="btn btn-primary" disabled={createMutation.isPending || !transcript.trim()}>
            {createMutation.isPending ? "Creating..." : "Create Action Point"}
          </button>
        </form>
      )}

      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
