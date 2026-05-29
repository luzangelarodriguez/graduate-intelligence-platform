import type { ReactNode } from 'react';
import { ArrowUpRight, CheckCircle2, CircleAlert, FileText, ShieldCheck } from 'lucide-react';

import type { Progress, Tone } from '../../data/institutional_observatory';

type CardProps = {
  title?: string;
  label?: string;
  children: ReactNode;
  className?: string;
};

export function ExecutiveCard({ title, label, children, className = '' }: CardProps) {
  return (
    <section className={`oi-card ${className}`}>
      {(title || label) && (
        <div className="oi-card-head">
          <div>
            {label ? <span>{label}</span> : null}
            {title ? <h2>{title}</h2> : null}
          </div>
        </div>
      )}
      {children}
    </section>
  );
}

export function MetricHero({
  label,
  value,
  detail,
  tone = 'blue',
}: {
  label: string;
  value: string;
  detail: string;
  tone?: Tone;
}) {
  return (
    <article className={`oi-metric oi-tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

export function ProgressRow({ item }: { item: Progress }) {
  return (
    <div className={`oi-progress oi-tone-${item.tone || 'blue'}`}>
      <div>
        <strong>{item.label}</strong>
        <span>{item.value}</span>
      </div>
      <div className="oi-track">
        <i className={item.level} />
      </div>
    </div>
  );
}

export function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="oi-table-wrap">
      <table className="oi-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.join('-')}>
              {row.map((cell, index) => (
                <td key={`${cell}-${index}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusMark({ tone = 'blue', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`oi-status oi-tone-${tone}`}>{children}</span>;
}

export function DecisionBar() {
  return (
    <div className="oi-decision-bar">
      <button type="button">
        <CheckCircle2 size={17} />
        Aprobar propuesta
      </button>
      <button type="button">
        <CircleAlert size={17} />
        Solicitar ajuste
      </button>
      <button type="button">
        <ArrowUpRight size={17} />
        Ver trazabilidad
      </button>
    </div>
  );
}

export function DocumentPanel({
  title,
  children,
  variant = 'default',
}: {
  title: string;
  children: ReactNode;
  variant?: 'default' | 'proposal';
}) {
  return (
    <article className={`oi-document oi-document-${variant}`}>
      <div className="oi-document-title">
        <FileText size={18} />
        <h3>{title}</h3>
      </div>
      {children}
    </article>
  );
}

export function AuditNote({ children }: { children: ReactNode }) {
  return (
    <div className="oi-audit-note">
      <ShieldCheck size={18} />
      <p>{children}</p>
    </div>
  );
}
