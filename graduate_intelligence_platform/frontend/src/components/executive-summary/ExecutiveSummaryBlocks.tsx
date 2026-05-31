import { AlertTriangle, ArrowRight, Building2, CheckCircle2, ChevronRight, Clock3, Lightbulb, Target, TrendingUp } from 'lucide-react';
import type { ReactNode } from 'react';

type Tone = 'blue' | 'green' | 'amber' | 'red' | 'slate';

const badgeToneClasses: Record<Tone, string> = {
  blue: 'bg-[#EAF2FB] text-[#003B71] ring-[#BFD5EE]',
  green: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  amber: 'bg-amber-50 text-amber-800 ring-amber-200',
  red: 'bg-red-50 text-red-800 ring-red-200',
  slate: 'bg-slate-100 text-slate-700 ring-slate-200',
};

const borderToneClasses: Record<Tone, string> = {
  blue: 'border-[#BFD5EE]',
  green: 'border-emerald-200',
  amber: 'border-amber-200',
  red: 'border-red-200',
  slate: 'border-slate-200',
};

export function SectionPanel({
  title,
  subtitle,
  children,
  action,
  className = '',
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-3xl border border-slate-200 bg-white px-6 py-6 shadow-[0_1px_0_rgba(15,23,42,0.02)] ${className}`.trim()}>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#64748B]">Observatorio</p>
          <h2 className="text-xl font-semibold text-[#1E293B]">{title}</h2>
          {subtitle ? <p className="max-w-3xl text-sm leading-6 text-[#64748B]">{subtitle}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function HeaderMetricCard({
  label,
  value,
  detail,
  interpretation,
  badge,
  tone = 'blue',
}: {
  label: string;
  value: string;
  detail: string;
  interpretation: string;
  badge: string;
  tone?: Tone;
}) {
  return (
    <article className={`rounded-2xl border ${borderToneClasses[tone]} bg-white p-5`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#64748B]">{label}</p>
          <strong className="mt-2 block text-3xl font-semibold tracking-tight text-[#1E293B]">{value}</strong>
        </div>
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[tone]}`}>{badge}</span>
      </div>
      <p className="text-sm font-medium text-[#1E293B]">{interpretation}</p>
      <p className="mt-2 text-sm leading-6 text-[#64748B]">{detail}</p>
    </article>
  );
}

export function NarrativeCard({
  title,
  narrative,
  caption,
}: {
  title: string;
  narrative: string;
  caption: string;
}) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-[#F8FAFC] p-6">
      <div className="flex items-center gap-2 text-[#003B71]">
        <Lightbulb size={18} />
        <span className="text-xs font-semibold uppercase tracking-[0.22em]">{title}</span>
      </div>
      <p className="mt-4 max-w-4xl text-[1.02rem] leading-8 text-[#1E293B]">{narrative}</p>
      <p className="mt-3 text-sm text-[#64748B]">{caption}</p>
    </article>
  );
}

export function RiskSegmentBar({
  aligned,
  observation,
  critical,
  total,
}: {
  aligned: number;
  observation: number;
  critical: number;
  total: number;
}) {
  const denominator = Math.max(total, 1);
  const alignedPct = (aligned / denominator) * 100;
  const observationPct = (observation / denominator) * 100;
  const criticalPct = (critical / denominator) * 100;

  const segments = [
    { label: 'Programas alineados', value: aligned, percentage: alignedPct, tone: 'green' as const },
    { label: 'Programas en observación', value: observation, percentage: observationPct, tone: 'amber' as const },
    { label: 'Programas críticos', value: critical, percentage: criticalPct, tone: 'red' as const },
  ];

  return (
    <div className="space-y-4">
      <div className="flex h-4 overflow-hidden rounded-full border border-slate-200 bg-slate-100">
        <div className="bg-emerald-600" style={{ width: `${alignedPct}%` }} />
        <div className="bg-amber-500" style={{ width: `${observationPct}%` }} />
        <div className="bg-red-600" style={{ width: `${criticalPct}%` }} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {segments.map((segment) => (
          <div key={segment.label} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-[#1E293B]">{segment.label}</span>
              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[segment.tone]}`}>{segment.value}</span>
            </div>
            <p className="mt-2 text-sm text-[#64748B]">{segment.percentage.toFixed(1)}% del portafolio analizado</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export type AttentionProgram = {
  programName: string;
  alignment: number;
  riskLevel: string;
  mainGapDriver: string;
  recommendedAction: string;
};

export function AttentionProgramList({ items }: { items: AttentionProgram[] }) {
  if (!items.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm text-[#64748B]">
        No se encontraron programas con riesgo suficiente para mostrar un ranking ejecutivo.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const tone: Tone = item.riskLevel === 'Crítico' ? 'red' : item.riskLevel === 'Observación' ? 'amber' : 'green';
        return (
          <article key={`${item.programName}-${index}`} className="rounded-2xl border border-slate-200 bg-white px-5 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-[#EAF2FB] text-xs font-semibold text-[#003B71]">{index + 1}</span>
                  <h3 className="text-base font-semibold text-[#1E293B]">{item.programName}</h3>
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[tone]}`}>{item.riskLevel}</span>
                </div>
                <p className="text-sm text-[#64748B]">Brecha principal: {item.mainGapDriver || 'Pendiente de consolidar'}</p>
              </div>
              <div className="text-right">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#64748B]">Alineación</p>
                <strong className="block text-2xl font-semibold text-[#003B71]">{item.alignment.toFixed(1)}%</strong>
              </div>
            </div>
            <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3">
              <p className="text-sm leading-6 text-[#1E293B]">
                <span className="font-semibold text-[#003B71]">Acción recomendada:</span> {item.recommendedAction || 'Definir actualización curricular prioritaria.'}
              </p>
            </div>
          </article>
        );
      })}
    </div>
  );
}

export type SignalItem = {
  label: string;
  value: string;
  detail: string;
  progress: number;
  tone?: Tone;
};

export function SignalColumn({
  title,
  icon: Icon,
  items,
  emptyMessage,
}: {
  title: string;
  icon: typeof AlertTriangle;
  items: SignalItem[];
  emptyMessage: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2 text-[#003B71]">
        <Icon size={18} />
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em]">{title}</h3>
      </div>
      {items.length ? (
        <div className="mt-4 space-y-4">
          {items.map((item) => (
            <div key={`${item.label}-${item.value}`} className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[#1E293B]">{item.label}</p>
                  <p className="text-sm text-[#64748B]">{item.detail}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[item.tone || 'blue']}`}>{item.value}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${
                    item.tone === 'green'
                      ? 'bg-emerald-600'
                      : item.tone === 'amber'
                        ? 'bg-amber-500'
                        : item.tone === 'red'
                          ? 'bg-red-600'
                          : 'bg-[#003B71]'
                  }`}
                  style={{ width: `${Math.max(4, Math.min(100, item.progress))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-[#64748B]">{emptyMessage}</div>
      )}
    </div>
  );
}

export type ComparisonRow = {
  label: string;
  marketDemand: string;
  curriculumCoverage: string;
  gapStatus: 'alto' | 'medio' | 'bajo';
};

export function MarketComparisonMatrix({ rows }: { rows: ComparisonRow[] }) {
  const gapTone: Record<ComparisonRow['gapStatus'], Tone> = {
    alto: 'red',
    medio: 'amber',
    bajo: 'green',
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="grid grid-cols-[1.4fr_1fr_1fr_0.7fr] gap-0 border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-[#64748B]">
        <div>Skill / Tecnología</div>
        <div>Market demand</div>
        <div>Curriculum coverage</div>
        <div>Gap</div>
      </div>
      <div className="divide-y divide-slate-200">
        {rows.length ? (
          rows.map((row) => (
            <div key={row.label} className="grid grid-cols-1 gap-3 px-4 py-4 md:grid-cols-[1.4fr_1fr_1fr_0.7fr] md:items-center">
              <div className="font-medium text-[#1E293B]">{row.label}</div>
              <div className="text-sm text-[#64748B]">{row.marketDemand}</div>
              <div className="text-sm text-[#64748B]">{row.curriculumCoverage}</div>
              <div>
                <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[gapTone[row.gapStatus]]}`}>
                  {row.gapStatus === 'alto' ? 'Alto' : row.gapStatus === 'medio' ? 'Medio' : 'Bajo'}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="px-4 py-6 text-sm text-[#64748B]">No hay suficientes señales de mercado y currículo para construir la matriz.</div>
        )}
      </div>
    </div>
  );
}

export type ImpactScenario = {
  currentAlignment: number;
  projectedAlignment: number;
  expectedImprovement: number;
  rationale: string;
};

export function ScenarioPanel({ scenario }: { scenario: ImpactScenario | null }) {
  if (!scenario) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm text-[#64748B]">
        Simulación pendiente de cálculo predictivo.
      </div>
    );
  }

  const current = Math.max(0, Math.min(100, scenario.currentAlignment));
  const projected = Math.max(current, Math.min(100, scenario.projectedAlignment));
  return (
    <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 text-[#003B71]">
          <TrendingUp size={18} />
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em]">Impacto proyectado</h3>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#64748B]">Alineación actual</p>
            <strong className="mt-2 block text-3xl font-semibold text-[#1E293B]">{current.toFixed(1)}%</strong>
          </div>
          <div className="rounded-2xl bg-[#EAF2FB] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#003B71]">Alineación proyectada</p>
            <strong className="mt-2 block text-3xl font-semibold text-[#003B71]">{projected.toFixed(1)}%</strong>
          </div>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-[#003B71]" style={{ width: `${current}%` }} />
          <div className="-mt-3 h-3 rounded-full bg-emerald-600/70" style={{ marginLeft: `${current}%`, width: `${Math.max(projected - current, 0)}%` }} />
        </div>
        <p className="mt-3 text-sm text-[#64748B]">
          <span className="font-semibold text-[#1E293B]">Mejora esperada:</span> {scenario.expectedImprovement.toFixed(1)} puntos porcentuales.
        </p>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
        <div className="flex items-center gap-2 text-[#003B71]">
          <Clock3 size={18} />
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em]">Fundamento</h3>
        </div>
        <p className="mt-4 text-sm leading-7 text-[#1E293B]">{scenario.rationale}</p>
      </div>
    </div>
  );
}

export type RecommendationItem = {
  priority: string;
  affectedProgram: string;
  title: string;
  academicRationale: string;
  marketEvidence: string;
  expectedImpact: string;
  confidence: number;
};

export function RecommendationStack({ items }: { items: RecommendationItem[] }) {
  if (!items.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm text-[#64748B]">
        No hay recomendaciones institucionales suficientes para consolidar un top 3 ejecutivo.
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {items.slice(0, 3).map((item) => {
        const tone: Tone = item.priority.toLowerCase().includes('alta') ? 'red' : item.priority.toLowerCase().includes('media') ? 'amber' : 'green';
        return (
          <article key={`${item.priority}-${item.affectedProgram}-${item.title}`} className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between gap-2">
              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[tone]}`}>{item.priority}</span>
              <ChevronRight size={17} className="text-[#64748B]" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-[#1E293B]">{item.title}</h3>
            <p className="mt-2 text-sm text-[#64748B]">Programa afectado: <span className="font-medium text-[#1E293B]">{item.affectedProgram}</span></p>
            <div className="mt-4 space-y-3 text-sm leading-6 text-[#1E293B]">
              <p>
                <span className="font-semibold text-[#003B71]">Racional académico:</span> {item.academicRationale}
              </p>
              <p>
                <span className="font-semibold text-[#003B71]">Evidencia de mercado:</span> {item.marketEvidence}
              </p>
              <p>
                <span className="font-semibold text-[#003B71]">Impacto esperado:</span> {item.expectedImpact}
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
              <div className="flex items-center gap-2 text-[#003B71]">
                <Target size={16} />
                <span className="text-sm font-medium">Confianza</span>
              </div>
              <strong className="text-base text-[#1E293B]">{item.confidence.toFixed(2)}</strong>
            </div>
          </article>
        );
      })}
    </div>
  );
}

export function FindingsFooter({ findings }: { findings: string[] }) {
  if (!findings.length) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white px-6 py-6">
      <div className="flex items-center gap-2 text-[#003B71]">
        <CheckCircle2 size={18} />
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em]">Hallazgos ejecutivos</h2>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {findings.slice(0, 4).map((item) => (
          <div key={item} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-6 text-[#1E293B]">
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}

export function TopLevelEmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#EAF2FB] text-[#003B71]">
        <Building2 size={22} />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-[#1E293B]">{title}</h3>
      <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-[#64748B]">{body}</p>
    </div>
  );
}

export function InlineAlert({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <span className="font-semibold">Cargue parcial:</span> {message}
    </div>
  );
}

export function RiskBadge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${badgeToneClasses[tone]}`}>{children}</span>;
}
