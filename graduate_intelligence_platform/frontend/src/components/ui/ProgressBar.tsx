interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  showLabel = false,
  size = 'sm',
}: ProgressBarProps) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));
  const heightClass = size === 'sm' ? 'h-1.5' : 'h-2.5';

  return (
    <div className="flex items-center gap-2">
      <div className={`progress-bar flex-1 ${heightClass}`}>
        <div
          className={`progress-bar-fill ${variant}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-semibold text-muted min-w-[36px] text-right">
          {percent.toFixed(0)}%
        </span>
      )}
    </div>
  );
}
