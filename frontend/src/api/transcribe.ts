import { apiRequest } from "./client";
import type { TranscriptionResult } from "./types";

export function transcribeFile(file: Blob, filename: string): Promise<TranscriptionResult> {
  const formData = new FormData();
  formData.append("file", file, filename);
  return apiRequest<TranscriptionResult>("/transcribe", { method: "POST", body: formData });
}
