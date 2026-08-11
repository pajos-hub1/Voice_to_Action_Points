import type { AuditLogEntry } from "../api/types";

export function AuditTimeline({ entries }: { entries: AuditLogEntry[] }) {
  if (entries.length === 0) {
    return <p className="empty-state">No audit events yet.</p>;
  }

  return (
    <ol className="audit-timeline">
      {entries.map((entry) => (
        <li key={entry.id} className="audit-entry">
          <div className="audit-entry-header">
            <span className="audit-entry-type">{entry.event_type}</span>
            <span className="audit-entry-time">{new Date(entry.timestamp).toLocaleString()}</span>
          </div>
          <p className="audit-entry-actor">by {entry.actor}</p>
          {Object.keys(entry.payload).length > 0 && (
            <pre className="audit-entry-payload">{JSON.stringify(entry.payload, null, 2)}</pre>
          )}
        </li>
      ))}
    </ol>
  );
}
