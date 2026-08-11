import type { ActionPointStatus } from "../api/types";

const STATUS_CLASS: Record<ActionPointStatus, string> = {
  CREATED: "badge badge-neutral",
  PENDING_APPROVAL: "badge badge-warning",
  APPROVED: "badge badge-info",
  REJECTED: "badge badge-danger",
  EXECUTED: "badge badge-success",
};

export function StatusBadge({ status }: { status: ActionPointStatus }) {
  return <span className={STATUS_CLASS[status]}>{status.replace("_", " ")}</span>;
}
