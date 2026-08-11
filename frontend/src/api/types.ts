export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export type ActionPointStatus = "CREATED" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "EXECUTED";

export interface ActionPoint {
  id: string;
  transcript: string;
  confidence: number;
  intent: string;
  entities: Record<string, unknown>;
  risk_level: RiskLevel;
  status: ActionPointStatus;
  created_at: string;
  approver: string | null;
  approved_at: string | null;
  executed_at: string | null;
  execution_result: Record<string, unknown> | null;
}

export interface AuditLogEntry {
  id: string;
  action_point_id: string;
  event_type: string;
  actor: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface TranscriptionResult {
  text: string;
  confidence: number;
  language: string | null;
  is_final: boolean;
  latency_ms: number;
}
