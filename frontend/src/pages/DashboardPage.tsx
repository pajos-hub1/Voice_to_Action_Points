import { useState } from "react";

import type { ActionPointStatus } from "../api/types";
import { ActionPointCard } from "../components/ActionPointCard";
import { useActionPoints } from "../hooks/useActionPoints";

const STATUS_OPTIONS: ActionPointStatus[] = ["PENDING_APPROVAL", "APPROVED", "REJECTED", "EXECUTED", "CREATED"];

export function DashboardPage() {
  const [statusFilter, setStatusFilter] = useState<ActionPointStatus | "">("");
  const { data: actionPoints, isLoading, isError } = useActionPoints(statusFilter || undefined);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Action Points</h1>
        <select
          className="input"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as ActionPointStatus | "")}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {status.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Could not load action points. Is the backend running?</p>}
      {actionPoints && actionPoints.length === 0 && (
        <p className="empty-state">No action points yet. Create one to get started.</p>
      )}

      <div className="action-point-list">
        {actionPoints?.map((actionPoint) => <ActionPointCard key={actionPoint.id} actionPoint={actionPoint} />)}
      </div>
    </div>
  );
}
