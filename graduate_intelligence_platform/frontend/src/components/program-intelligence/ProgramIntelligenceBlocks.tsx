import { Link, NavLink } from 'react-router-dom';
import { ArrowRight, BarChart3, BookOpen, FlaskConical, LineChart, Target } from 'lucide-react';
import type { ReactNode } from 'react';

interface ProgramHeaderProps {
  programId: number;
  title: string;
  subtitle: string;
  updatedAt?: string;
  meta?: Array<{ label: string; value: string }>;
}

interface MetricCardProps {
  label: string;
  value: string;
  detail: string;
  tone?: 'blue' | 'green' | 'amber' | 'rose' | 'slate';
}

interface SectionTitleProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

interface ForecastHorizonCardProps {
  horizon: number;
  currentAlignment: number;
  projectedAlignment: number;
  projectedRisk: number;
  projectedEmployability: number;
  projectedGapReduction: number;
  explanation?: string;
}

interface SkillRailProps {
  skills: string[];
  selectedSkills?: string[];
  onToggle?: (skill: string) => void;
  onClear?: () => void;
  label?: string;
}

interface ProgramTabItem {
  to: `/programs/${number}` | `/programs/${number}/microcurriculum` | `/programs/${number}/forecast` | `/programs/${number}/simulation`;
  label: string;
  icon: typeof Target;
  end?: boolean;
}

const toneClass: Record<NonNullable<MetricCardProps['tone']>, string> = {
  blue: 'border-brand/20 bg-brand/5 text-brand',
  green: 'border-emerald/20 bg-emerald/5 text-emerald',
  amber: 'border-amber/20 bg-amber/5 text-amber',
  rose: 'border-rose/20 bg-rose/5 text-rose',
  slate: 'border-line bg-slate-50 text-ink',
};

export function ProgramPageHeader({ programId, title, subtitle, updatedAt, meta = [] }: ProgramHeaderProps) {
  return (
    <section className="panel space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand/15 bg-brand/5 px-3 py-1 text-[0.72rem] font900 uppercase tracking-[0.12em] text-brand">
            <BarChart3 size={15} strokeWidth={1.9} />
            Programa {String(programId).padStart(3, '0')}
          </div>
          <div>
            <h1 className="text-balance text-3xl font900 leading-[0.98] text-ink md:text-4xl">{title}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted md:text-base">{subtitle}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {updatedAt && (
            <span className="rounded-full border border-line bg-slate-50 px-3 py-2 font-semibold text-muted">
              Actualizado: {updatedAt}
            </span>
          )}
          <Link
            className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand/90"
            to="/programas"
          >
            Volver al listado
            <ArrowRight size={15} strokeWidth={1.9} />
          </Link>
        </div>
      </div>

      {meta.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {meta.map((item) => (
            <div key={item.label} className="rounded-lg border border-line bg-slate-50/80 px-4 py-3">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">{item.label}</span>
              <strong className="mt-1 block text-sm font900 text-ink">{item.value}</strong>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ProgramTabs({ programId }: { programId: number }) {
  const tabs: ProgramTabItem[] = [
    { to: `/programs/${programId}`, label: 'Resumen', icon: Target, end: true },
    { to: `/programs/${programId}/microcurriculum`, label: 'Microcurriculum', icon: BookOpen },
    { to: `/programs/${programId}/forecast`, label: 'Forecast', icon: LineChart },
    { to: `/programs/${programId}/simulation`, label: 'Simulación', icon: FlaskConical },
  ];

  return (
    <nav className="flex flex-wrap gap-2">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              [
                'inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition',
                isActive
                  ? 'border-brand bg-brand text-white shadow-sm'
                  : 'border-line bg-white text-ink hover:border-brand/40 hover:text-brand',
              ].join(' ')
            }
          >
            <Icon size={15} strokeWidth={1.9} />
            {tab.label}
          </NavLink>
        );
      })}
    </nav>
  );
}

export function MetricCard({ label, value, detail, tone = 'slate' }: MetricCardProps) {
  return (
    <article className={`rounded-lg border p-4 shadow-sm ${toneClass[tone]}`}>
      <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em]">{label}</span>
      <strong className="mt-3 block text-3xl font900 leading-none">{value}</strong>
      <p className="mt-3 text-sm leading-6 text-muted">{detail}</p>
    </article>
  );
}

export function SectionTitle({ title, subtitle, action }: SectionTitleProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-line pb-3 md:flex-row md:items-end md:justify-between">
      <div>
        <h2 className="text-lg font900 text-ink">{title}</h2>
        {subtitle && <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function NarrativePanel({
  title,
  narrative,
  evidence = [],
}: {
  title: string;
  narrative: string;
  evidence?: string[];
}) {
  return (
    <article className="panel space-y-4">
      <SectionTitle title={title} subtitle="Lectura ejecutiva generada desde señales reales del mercado y del currículum." />
      <p className="max-w-4xl text-sm leading-7 text-ink md:text-[0.95rem]">{narrative}</p>
      {evidence.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {evidence.map((item) => (
            <span key={item} className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-semibold text-muted">
              {item}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

export function SkillRail({ skills, selectedSkills = [], onToggle, onClear, label = 'Skills priorizadas' }: SkillRailProps) {
  return (
    <article className="panel space-y-4">
      <SectionTitle
        title={label}
        subtitle="Las selecciones salen de brechas y señales reales del backend. Puedes activarlas o quitarlas para recalcular la simulación."
        action={
          onClear ? (
            <button
              type="button"
              className="rounded-full border border-line bg-white px-3 py-2 text-sm font-semibold text-muted transition hover:border-brand/40 hover:text-brand"
              onClick={onClear}
            >
              Limpiar
            </button>
          ) : null
        }
      />
      <div className="flex flex-wrap gap-2">
        {skills.length ? (
          skills.map((skill) => {
            const active = selectedSkills.some((item) => item.toLowerCase() === skill.toLowerCase());
            return (
              <button
                key={skill}
                type="button"
                onClick={() => onToggle?.(skill)}
                className={[
                  'rounded-full border px-3 py-2 text-sm font-semibold transition',
                  active
                    ? 'border-brand bg-brand text-white shadow-sm'
                    : 'border-line bg-slate-50 text-ink hover:border-brand/40 hover:text-brand',
                ].join(' ')}
              >
                {skill}
              </button>
            );
          })
        ) : (
          <span className="text-sm text-muted">No hay skills sugeridas suficientes para mostrar.</span>
        )}
      </div>
    </article>
  );
}

export function ForecastHorizonCard({
  horizon,
  currentAlignment,
  projectedAlignment,
  projectedRisk,
  projectedEmployability,
  projectedGapReduction,
  explanation,
}: ForecastHorizonCardProps) {
  const gapWidth = Math.min(100, Math.max(0, projectedGapReduction));
  return (
    <article className="panel space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Horizonte</span>
          <strong className="block text-2xl font900 text-ink">{horizon} meses</strong>
        </div>
        <div className="rounded-full border border-brand/15 bg-brand/5 px-3 py-1 text-sm font-semibold text-brand">
          {projectedGapReduction.toFixed(1)}% reducción de brecha
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between text-sm text-muted">
            <span>Alineación actual</span>
            <strong className="text-ink">{currentAlignment.toFixed(1)}%</strong>
          </div>
          <div className="mt-2 h-2 rounded-full bg-slate-100">
            <span className="block h-2 rounded-full bg-slate-300" style={{ width: `${Math.min(100, currentAlignment)}%` }} />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-sm text-muted">
            <span>Alineación proyectada</span>
            <strong className="text-brand">{projectedAlignment.toFixed(1)}%</strong>
          </div>
          <div className="mt-2 h-2 rounded-full bg-slate-100">
            <span className="block h-2 rounded-full bg-brand" style={{ width: `${Math.min(100, projectedAlignment)}%` }} />
          </div>
        </div>
      </div>

      <dl className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-line bg-slate-50 p-3">
          <dt className="text-xs font900 uppercase tracking-[0.12em] text-muted">Riesgo proyectado</dt>
          <dd className="mt-2 text-xl font900 text-ink">{projectedRisk.toFixed(1)}%</dd>
        </div>
        <div className="rounded-lg border border-line bg-slate-50 p-3">
          <dt className="text-xs font900 uppercase tracking-[0.12em] text-muted">Empleabilidad</dt>
          <dd className="mt-2 text-xl font900 text-ink">{projectedEmployability.toFixed(1)}%</dd>
        </div>
        <div className="rounded-lg border border-line bg-slate-50 p-3">
          <dt className="text-xs font900 uppercase tracking-[0.12em] text-muted">Brecha cubierta</dt>
          <dd className="mt-2 text-xl font900 text-ink">{gapWidth.toFixed(1)}%</dd>
        </div>
      </dl>

      {explanation && <p className="text-sm leading-7 text-muted">{explanation}</p>}
    </article>
  );
}
