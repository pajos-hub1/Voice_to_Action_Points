import { Link, useParams } from "react-router-dom";

import { ActionPointCard } from "../components/ActionPointCard";
import { AuditTimeline } from "../components/AuditTimeline";
import { useActionPoint } from "../hooks/useActionPoints";
import { useAuditLog } from "../hooks/useAuditLog";

export function ActionPointDetailPage() {
  const { id = "" } = useParams();
  const { data: actionPoint, isLoading, isError } = useActionPoint(id);
  const { data: auditEntries } = useAuditLog(id);

  if (isLoading) {
    return (
      <div className="page">
        <p>Loading...</p>
      </div>
    );
  }

  if (isError || !actionPoint) {
    return (
      <div className="page">
        <p className="form-error">Action point not found.</p>
      </div>
    );
  }

  const entityEntries = Object.entries(actionPoint.entities);

  return (
    <div className="page">
      <Link to="/" className="back-link">
        &larr; Back to dashboard
      </Link>

      <ActionPointCard actionPoint={actionPoint} linkToDetail={false} />

      <section className="detail-section">
        <h2>Entities</h2>
        {entityEntries.length > 0 ? (
          <dl className="entity-list">
            {entityEntries.map(([key, value]) => (
              <div key={key} className="entity-row">
                <dt>{key}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="empty-state">No entities extracted.</p>
        )}
      </section>

      {actionPoint.approver && (
        <section className="detail-section">
          <h2>Approval</h2>
          <p>
            {actionPoint.status === "REJECTED" ? "Rejected" : "Approved"} by {actionPoint.approver}
            {actionPoint.approved_at && ` at ${new Date(actionPoint.approved_at).toLocaleString()}`}
          </p>
        </section>
      )}

      {actionPoint.execution_result && (
        <section className="detail-section">
          <h2>Execution result</h2>
          <pre className="audit-entry-payload">{JSON.stringify(actionPoint.execution_result, null, 2)}</pre>
        </section>
      )}

      <section className="detail-section">
        <h2>Audit trail</h2>
        <AuditTimeline entries={auditEntries ?? []} />
      </section>
    </div>
  );
}
