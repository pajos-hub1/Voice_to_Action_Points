import { apiRequest } from "./client";
import type { ActionPoint, ActionPointStatus } from "./types";

export function listActionPoints(statusFilter?: ActionPointStatus): Promise<ActionPoint[]> {
  const query = statusFilter ? `?status_filter=${statusFilter}` : "";
  return apiRequest<ActionPoint[]>(`/action-points${query}`);
}

export function getActionPoint(id: string): Promise<ActionPoint> {
  return apiRequest<ActionPoint>(`/action-points/${id}`);
}

export function createActionPoint(transcript: string, confidence: number): Promise<ActionPoint> {
  return apiRequest<ActionPoint>("/action-points", {
    method: "POST",
    body: JSON.stringify({ transcript, confidence }),
  });
}

export function approveActionPoint(id: string, approver: string): Promise<ActionPoint> {
  return apiRequest<ActionPoint>(`/action-points/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ approver }),
  });
}

export function rejectActionPoint(id: string, approver: string, reason?: string): Promise<ActionPoint> {
  return apiRequest<ActionPoint>(`/action-points/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ approver, reason: reason || null }),
  });
}

export function executeActionPoint(id: string): Promise<ActionPoint> {
  return apiRequest<ActionPoint>(`/action-points/${id}/execute`, { method: "POST" });
}
