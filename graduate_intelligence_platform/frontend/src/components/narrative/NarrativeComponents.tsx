import type { ReactNode } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';

// Narrative Insight Card
interface InsightCardProps {
  headline: string;
  body?: string;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  metric?: {
    value: string | number;
    label: string;
    trend?: 'up' | 'down' | 'neutral';
  };
}

export function InsightCard({ headline, body, variant = 'default', metric }: InsightCardProps) {
  const borderColors = {
    default: 'border-l-primary',
    success: 'border-l-success',
    warning: 'border-l-warning',
    danger: 'border-l-danger',
  };

  return (
    <div className={`bg-white rounded-lg border border-line border-l-4 ${borderColors[variant]} p-5`}>
      <p className="text-base font-medium text-foreground leading-relaxed">{headline}</p>
      {body && <p className="text-sm text-muted mt-2">{body}</p>}
      {metric && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-line">
          <span className="text-2xl font-bold text-foreground">{metric.value}</span>
          <span className="text-sm text-muted">{metric.label}</span>
          {metric.trend && (
            <span className={`ml-auto ${
              metric.trend === 'up' ? 'text-success' : 
              metric.trend === 'down' ? 'text-danger' : 'text-muted'
            }`}>
              {metric.trend === 'up' && <TrendingUp size={18} />}
              {metric.trend === 'down' && <TrendingDown size={18} />}
              {metric.trend === 'neutral' && <Minus size={18} />}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Executive KPI Display
interface ExecutiveKpiProps {
  value: string | number;
  label: string;
  sublabel?: string;
  trend?: { value: number; label: string };
  size?: 'default' | 'large';
}

export function ExecutiveKpi({ value, label, sublabel, trend, size = 'default' }: ExecutiveKpiProps) {
  return (
    <div className="text-center">
      <p className={`font-bold text-foreground ${size === 'large' ? 'text-5xl' : 'text-3xl'}`}>
        {value}
      </p>
      <p className={`font-medium text-foreground mt-1 ${size === 'large' ? 'text-base' : 'text-sm'}`}>
        {label}
      </p>
      {sublabel && <p className="text-xs text-muted mt-1">{sublabel}</p>}
      {trend && (
        <p className={`text-xs mt-2 ${trend.value >= 0 ? 'text-success' : 'text-danger'}`}>
          {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
        </p>
      )}
    </div>
  );
}

// Section with narrative title
interface NarrativeSectionProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export function NarrativeSection({ title, subtitle, children, className = '' }: NarrativeSectionProps) {
  return (
    <section className={`mb-10 ${className}`}>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-foreground">{title}</h2>
        {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

// Risk Badge
interface RiskBadgeProps {
  level: 'high' | 'medium' | 'low';
  label?: string;
}

export function RiskBadge({ level, label }: RiskBadgeProps) {
  const colors = {
    high: 'bg-danger/10 text-danger border-danger/20',
    medium: 'bg-warning/10 text-warning border-warning/20',
    low: 'bg-success/10 text-success border-success/20',
  };
  const labels = { high: 'Alto', medium: 'Medio', low: 'Bajo' };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${colors[level]}`}>
      {level === 'high' && <AlertTriangle size={12} />}
      {label || labels[level]}
    </span>
  );
}

// Metric Card for storytelling
interface StoryMetricProps {
  icon: ReactNode;
  value: string | number;
  label: string;
  context?: string;
}

export function StoryMetric({ icon, value, label, context }: StoryMetricProps) {
  return (
    <div className="bg-white rounded-lg border border-line p-5">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-bold text-foreground">{value}</p>
          <p className="text-sm font-medium text-foreground">{label}</p>
          {context && <p className="text-xs text-muted mt-1">{context}</p>}
        </div>
      </div>
    </div>
  );
}

// Data Point for inline metrics
interface DataPointProps {
  value: string | number;
  label: string;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
}

export function DataPoint({ value, label, variant = 'default' }: DataPointProps) {
  const colors = {
    default: 'text-foreground',
    primary: 'text-primary',
    success: 'text-success',
    warning: 'text-warning',
    danger: 'text-danger',
  };

  return (
    <span className="inline-flex items-baseline gap-1">
      <span className={`font-bold ${colors[variant]}`}>{value}</span>
      <span className="text-muted text-sm">{label}</span>
    </span>
  );
}

// Evidence Card for committee workspace
interface EvidenceCardProps {
  title: string;
  source: string;
  date?: string;
  children: ReactNode;
}

export function EvidenceCard({ title, source, date, children }: EvidenceCardProps) {
  return (
    <div className="bg-subtle/50 rounded-lg border border-line p-5">
      <div className="flex items-start justify-between gap-4 mb-3">
        <h4 className="font-medium text-foreground">{title}</h4>
        <span className="text-xs text-muted whitespace-nowrap">{date}</span>
      </div>
      <div className="text-sm text-foreground">{children}</div>
      <p className="text-xs text-muted mt-3 pt-3 border-t border-line">Fuente: {source}</p>
    </div>
  );
}

// Loading skeleton for narrative sections
export function NarrativeSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-6 bg-subtle rounded w-3/4" />
      <div className="h-4 bg-subtle rounded w-1/2" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-32 bg-subtle rounded-lg" />
        ))}
      </div>
      <div className="h-64 bg-subtle rounded-lg" />
    </div>
  );
}
