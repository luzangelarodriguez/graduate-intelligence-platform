import type { ReactNode } from 'react';

interface KpiCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  featured?: boolean;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  onClick?: () => void;
}

export function KpiCard({
  label,
  value,
  description,
  icon,
  featured = false,
  trend,
  trendValue,
  onClick,
}: KpiCardProps) {
  const cardClass = featured
    ? 'kpi-card kpi-card-featured'
    : 'kpi-card exec-card-hover';

  const Wrapper = onClick ? 'button' : 'div';

  return (
    <Wrapper
      className={cardClass}
      onClick={onClick}
      type={onClick ? 'button' : undefined}
    >
      <div className="flex items-center justify-between">
        <span className="kpi-card-label">{label}</span>
        {icon && (
          <span className={featured ? 'text-white/70' : 'text-muted'}>{icon}</span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <span className="kpi-card-value">{value}</span>
        {trend && trendValue && (
          <span
            className={`text-sm font-semibold ${
              trend === 'up'
                ? 'text-success'
                : trend === 'down'
                ? 'text-danger'
                : 'text-muted'
            }`}
          >
            {trend === 'up' && '+'}
            {trendValue}
          </span>
        )}
      </div>
      {description && (
        <p className="kpi-card-description">{description}</p>
      )}
    </Wrapper>
  );
}

interface KpiGridProps {
  children: ReactNode;
  columns?: 2 | 3 | 4 | 5 | 6;
}

export function KpiGrid({ children, columns = 4 }: KpiGridProps) {
  const colsClass = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-5',
    6: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
  }[columns];

  return <div className={`grid gap-4 ${colsClass}`}>{children}</div>;
}
