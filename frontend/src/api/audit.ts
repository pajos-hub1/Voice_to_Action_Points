import { apiRequest } from "./client";
import type { AuditLogEntry } from "./types";

export function listAuditLog(actionPointId?: string): Promise<AuditLogEntry[]> {
  const query = actionPointId ? `?action_point_id=${actionPointId}` : "";
  return apiRequest<AuditLogEntry[]>(`/audit-log${query}`);
}
