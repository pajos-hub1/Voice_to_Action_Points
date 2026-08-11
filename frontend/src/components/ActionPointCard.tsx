import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import type { ActionPoint } from "../api/types";
import { useApproveActionPoint, useExecuteActionPoint, useRejectActionPoint } from "../hooks/useActionPoints";
import { RiskBadge } from "./RiskBadge";
import { StatusBadge } from "./StatusBadge";

interface ActionPointCardProps {
  actionPoint: ActionPoint;
  linkToDetail?: boolean;
}

export function ActionPointCard({ actionPoint, linkToDetail = true }: ActionPointCardProps) {
  const [approver, setApprover] = useState("");
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const approve = useApproveActionPoint();
  const reject = useRejectActionPoint();
  const execute = useExecuteActionPoint();

  const busy = approve.isPending || reject.isPending || execute.isPending;

  async function handleApprove() {
    if (!approver.trim()) return;
    setActionError(null);
    try {
      await approve.mutateAsync({ id: actionPoint.id, approver: approver.trim() });
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Approval failed.");
    }
  }

  async function handleReject() {
    if (!approver.trim()) return;
    setActionError(null);
    try {
      await reject.mutateAsync({ id: actionPoint.id, approver: approver.trim(), reason: reason.trim() || undefined });
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Rejection failed.");
    }
  }

  async function handleExecute() {
    setActionError(null);
    try {
      await execute.mutateAsync(actionPoint.id);
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Execution failed.");
    }
  }

  const title = linkToDetail ? (
    <Link to={`/action-points/${actionPoint.id}`} className="action-point-title">
      {actionPoint.intent}
    </Link>
  ) : (
    <span className="action-point-title">{actionPoint.intent}</span>
  );

  return (
    <div className="action-point-card">
      <div className="action-point-header">
        {title}
        <div className="action-point-badges">
          <RiskBadge risk={actionPoint.risk_level} />
          <StatusBadge status={actionPoint.status} />
        </div>
      </div>

      <p className="action-point-transcript">&ldquo;{actionPoint.transcript}&rdquo;</p>
      <p className="action-point-meta">
        confidence {(actionPoint.confidence * 100).toFixed(0)}% - created {new Date(actionPoint.created_at).toLocaleString()}
      </p>

      {actionPoint.status === "PENDING_APPROVAL" && (
        <div className="action-point-actions">
          <input
            className="input"
            placeholder="Your name (approver)"
            value={approver}
            onChange={(event) => setApprover(event.target.value)}
            disabled={busy}
          />
          <input
            className="input"
            placeholder="Reason (optional, for reject)"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={busy}
          />
          <div className="action-point-buttons">
            <button type="button" className="btn btn-primary" onClick={handleApprove} disabled={busy || !approver.trim()}>
              Approve
            </button>
            <button type="button" className="btn btn-danger" onClick={handleReject} disabled={busy || !approver.trim()}>
              Reject
            </button>
          </div>
        </div>
      )}

      {actionPoint.status === "APPROVED" && (
        <div className="action-point-actions">
          <button type="button" className="btn btn-primary" onClick={handleExecute} disabled={busy}>
            Execute
          </button>
        </div>
      )}

      {actionError && <p className="form-error">{actionError}</p>}
    </div>
  );
}
