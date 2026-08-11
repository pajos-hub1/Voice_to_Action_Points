import type { RiskLevel } from "../api/types";

const RISK_CLASS: Record<RiskLevel, string> = {
  LOW: "badge badge-success",
  MEDIUM: "badge badge-warning",
  HIGH: "badge badge-danger",
};

export function RiskBadge({ risk }: { risk: RiskLevel }) {
  return <span className={RISK_CLASS[risk]}>{risk} risk</span>;
}
