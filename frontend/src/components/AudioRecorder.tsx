import { useRef, useState } from "react";

interface AudioRecorderProps {
  onCapture: (audio: Blob, filename: string) => void;
  disabled?: boolean;
}

export function AudioRecorder({ onCapture, disabled }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        onCapture(blob, "recording.webm");
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setError("Microphone access was denied or is unavailable. Use file upload instead.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setIsRecording(false);
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onCapture(file, file.name);
    event.target.value = "";
  }

  return (
    <div className="audio-recorder">
      <div className="audio-recorder-row">
        {isRecording ? (
          <button type="button" className="btn btn-danger" onClick={stopRecording} disabled={disabled}>
            Stop recording
          </button>
        ) : (
          <button type="button" className="btn btn-primary" onClick={startRecording} disabled={disabled}>
            Record from mic
          </button>
        )}
        <span className="audio-recorder-or">or</span>
        <label className="btn btn-secondary">
          Upload audio file
          <input type="file" accept="audio/*" onChange={handleFileChange} disabled={disabled} hidden />
        </label>
      </div>
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
