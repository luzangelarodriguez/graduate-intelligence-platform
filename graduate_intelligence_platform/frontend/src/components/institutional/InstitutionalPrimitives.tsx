import { AlertTriangle, CheckCircle2, Info, Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import type { ResourceStatus } from '../../services/serviceState';

interface PageHeroProps {
  eyebrow: string;
  title: string;
  subtitle: string;
  children?: ReactNode;
}

interface SectionCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

interface EmptyDiagnosticProps {
  title: string;
  cause: string;
  endpoint: string;
  action: string;
}

export function PageHero({ eyebrow, title, subtitle, children }: PageHeroProps) {
  return (
    <section className="institutional-hero">
      <div>
        <span className="institutional-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

export function SectionCard({ title, subtitle, children }: SectionCardProps) {
  return (
    <article className="institutional-card">
      <div className="mb-4">
        <h2>{title}</h2>
        {subtitle ? <p className="mt-1 text-sm">{subtitle}</p> : null}
      </div>
      {children}
    </article>
  );
}

export function MetricCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <article className="institutional-metric">
      <span className="institutional-card-label">{label}</span>
      <strong>{value}</strong>
      <p className="m-0 text-sm text-muted">{detail}</p>
    </article>
  );
}

export function EmptyDiagnostic({ title, cause, endpoint, action }: EmptyDiagnosticProps) {
  return (
    <div className="institutional-empty">
      <strong>{title}</strong>
      <p>{cause}</p>
      <dl>
        <div>
          <dt>Endpoint relacionado</dt>
          <dd>{endpoint}</dd>
        </div>
        <div>
          <dt>Acción recomendada</dt>
          <dd>{action}</dd>
        </div>
      </dl>
    </div>
  );
}

export function StatusBadge({ status }: { status: ResourceStatus }) {
  const config = {
    success: { label: 'Con datos', className: 'success', icon: CheckCircle2 },
    empty: { label: 'Sin registros', className: 'warning', icon: Info },
    error: { label: 'Con error', className: 'danger', icon: AlertTriangle },
  }[status];
  const Icon = config.icon;

  return (
    <span className={`institutional-status ${config.className}`}>
      <Icon size={13} strokeWidth={2} />
      &nbsp;{config.label}
    </span>
  );
}

export function LoadingPanel({ label = 'Cargando evidencia institucional...' }: { label?: string }) {
  return (
    <div className="institutional-card flex items-center gap-3">
      <Loader2 className="animate-spin text-brand" size={18} />
      <span className="text-sm font-semibold text-muted">{label}</span>
    </div>
  );
}

export function QuickLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className="institutional-button" to={to}>
      {children}
    </Link>
  );
}

export function DataTable({
  title,
  subtitle,
  columns,
  rows,
  empty,
}: {
  title: string;
  subtitle?: string;
  columns: string[];
  rows: ReactNode[][];
  empty: ReactNode;
}) {
  return (
    <article className="institutional-table-card">
      <div className="institutional-table-head">
        <h2>{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="institutional-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-4">{empty}</div>
      )}
    </article>
  );
}



