interface StatusBadgeProps {
  status: 'success' | 'warning' | 'danger' | 'neutral' | 'accent';
  label: string;
  dot?: boolean;
}

export function StatusBadge({ status, label, dot = false }: StatusBadgeProps) {
  return (
    <span className={`badge badge-${status}`}>
      {dot && <span className={`status-dot ${status === 'success' ? 'online' : status === 'warning' ? 'warning' : status === 'danger' ? 'offline' : ''}`} />}
      {label}
    </span>
  );
}
