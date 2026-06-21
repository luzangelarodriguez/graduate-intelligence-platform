import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KPICard {
  label: string;
  value: string;
  percentage: number;
  trend: 'up' | 'down' | 'stable';
  change: string;
  color: string;
}

const kpis: KPICard[] = [
  {
    label: 'Pertinencia General',
    value: '76%',
    percentage: 76,
    trend: 'up',
    change: '+5% vs último año',
    color: 'bg-[var(--color-success)]',
  },
  {
    label: 'Cobertura Curricular',
    value: '68%',
    percentage: 68,
    trend: 'down',
    change: '-2% vs último año',
    color: 'bg-[var(--color-warning)]',
  },
  {
    label: 'Empleabilidad Egresados',
    value: '82%',
    percentage: 82,
    trend: 'up',
    change: '+8% vs último año',
    color: 'bg-[var(--color-success)]',
  },
];

export function EstadoSection() {
  return (
    <section id="section-estado" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <TrendingUp size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Estado de Pertinencia
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Diagnóstico integral del programa respecto a demandas del mercado laboral
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {kpis.map((kpi, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7 hover:border-[var(--color-accent-red)] hover:border-opacity-30 transition-all"
          >
            <div className="flex items-start justify-between mb-6">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                {kpi.label}
              </p>
              <div className="flex items-center gap-1">
                {kpi.trend === 'up' && (
                  <TrendingUp size={16} className="text-[var(--color-success)]" strokeWidth={2.5} />
                )}
                {kpi.trend === 'down' && (
                  <TrendingDown size={16} className="text-[var(--color-error)]" strokeWidth={2.5} />
                )}
                {kpi.trend === 'stable' && (
                  <Minus size={16} className="text-[var(--color-text-secondary)]" strokeWidth={2.5} />
                )}
              </div>
            </div>

            <p className="text-4xl font-black text-[var(--color-text-primary)] mb-2">{kpi.value}</p>
            <p className={`text-xs font-bold mb-6 ${
              kpi.trend === 'up'
                ? 'text-[var(--color-success)]'
                : kpi.trend === 'down'
                  ? 'text-[var(--color-error)]'
                  : 'text-[var(--color-text-secondary)]'
            }`}>
              {kpi.change}
            </p>

            {/* Progress Bar */}
            <div className="relative h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
              <div
                className={`h-full ${kpi.color} rounded-full transition-all duration-700`}
                style={{ width: `${kpi.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary Box */}
      <div className="rounded-xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-background)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-4">Resumen Ejecutivo</h3>
        <div className="space-y-3 text-[var(--color-text-secondary)]">
          <p className="flex items-start gap-3">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-accent-red)] mt-2 flex-shrink-0" />
            <span>El programa mantiene una pertinencia general sólida del 76%, con tendencia creciente en empleabilidad</span>
          </p>
          <p className="flex items-start gap-3">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-accent-red)] mt-2 flex-shrink-0" />
            <span>Requiere fortalecimiento inmediato en cobertura curricular de tecnologías emergentes</span>
          </p>
          <p className="flex items-start gap-3">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-accent-red)] mt-2 flex-shrink-0" />
            <span>Egresados muestran buena empleabilidad, indicador de alineación con mercado</span>
          </p>
        </div>
      </div>
    </section>
  );
}
