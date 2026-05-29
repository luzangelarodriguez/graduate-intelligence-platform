interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'title' | 'value' | 'rect';
  width?: string;
  height?: string;
}

export function Skeleton({ className = '', variant = 'text', width, height }: SkeletonProps) {
  const variantClass = {
    text: 'skeleton-text',
    title: 'skeleton-title',
    value: 'skeleton-value',
    rect: '',
  }[variant];

  return (
    <div
      className={`skeleton ${variantClass} ${className}`}
      style={{ width, height }}
    />
  );
}

interface SkeletonCardProps {
  lines?: number;
}

export function SkeletonCard({ lines = 3 }: SkeletonCardProps) {
  return (
    <div className="exec-card p-5">
      <Skeleton variant="text" width="40%" className="mb-3" />
      <Skeleton variant="value" className="mb-4" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" width={i === lines - 1 ? '60%' : '100%'} className="mb-2" />
      ))}
    </div>
  );
}

export function SkeletonKpiGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="kpi-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="kpi-card">
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="value" />
          <Skeleton variant="text" width="80%" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="exec-card overflow-hidden">
      <div className="p-4 border-b border-line">
        <Skeleton variant="title" width="30%" />
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th><Skeleton width="80px" /></th>
            <th><Skeleton width="100px" /></th>
            <th><Skeleton width="60px" /></th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i}>
              <td><Skeleton width="150px" /></td>
              <td><Skeleton width="100px" /></td>
              <td><Skeleton width="60px" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
