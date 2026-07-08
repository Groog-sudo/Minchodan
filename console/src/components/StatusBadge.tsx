interface StatusBadgeProps {
  label: string;
  tone?: "good" | "warn" | "bad" | "idle";
}

export function StatusBadge({ label, tone = "idle" }: StatusBadgeProps) {
  return <span className={`status-badge status-badge-${tone}`}>{label}</span>;
}
