import { Zap, TrendingUp, BarChart3 } from 'lucide-react';

interface Scenario {
  name: string;
  description: string;
  pertinenceGain: number;
  employabilityGain: number;
  timeframe: string;
  investment: string;
  roi: number;
  actions: string[];
}

const scenarios: Scenario[] = [
  {
    name: 'Expansión Fundamental',
    description: 'Añadir módulos de tecnologías emergentes',
    pertinenceGain: 15,
    employabilityGain: 12,
    timeframe: '3 meses',
    investment: 'Bajo',
    roi: 280,
    actions: [
      'Crear módulo AI/ML (1 crédito)',
      'Expandir DevOps basics',
      'Fortalecer Cloud services',
    ],
  },
  {
    name: 'Transformación Completa',
    description: 'Rediseño curricular integral',
    pertinenceGain: 22,
    employabilityGain: 18,
    timeframe: '6-8 meses',
    investment: 'Medio-Alto',
    roi: 420,
    actions: [
      'Arquitectura modular nueva',
      'Especialización en 3 tracks',
      'Labs modernos con partner empresas',
      'Certificaciones integradas',
    ],
  },
  {
    name: 'Optimización Selectiva',
    description: 'Mejoras puntuales sin reingeniería',
    pertinenceGain: 8,
    employabilityGain: 10,
    timeframe: '1-2 meses',
    investment: 'Muy Bajo',
    roi: 180,
    actions: [
      'Actualizar syllabus existentes',
      'Casos de estudio reales',
      'Guest lectures de industria',
    ],
  },
];

export function SimulacionSection() {
  const basePerti = 76;
  const baseEmpl = 82;

  return (
    <section id="section-simulacion" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <Zap size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Simulación de Mejora
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Impacto proyectado de diferentes estrategias de intervención curricular
        </p>
      </div>

      {/* Scenarios Comparison */}
      <div className="space-y-6 mb-8">
        {scenarios.map((scenario, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden hover:shadow-md transition-all"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-[var(--color-accent-red)] bg-opacity-5 to-transparent p-6 border-b border-[var(--color-border)]">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-xl font-bold text-[var(--color-text-primary)] mb-2">{scenario.name}</h3>
                  <p className="text-[var(--color-text-secondary)]">{scenario.description}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-3xl font-black text-[var(--color-accent-red)]">{scenario.roi}%</div>
                  <p className="text-xs text-[var(--color-text-secondary)]">ROI Proyectado</p>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="p-6">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                    Pertinencia
                  </p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-2xl font-black text-[var(--color-text-primary)]">{basePerti + scenario.pertinenceGain}%</p>
                    <p className="text-sm font-bold text-[var(--color-success)]">+{scenario.pertinenceGain}%</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                    Empleabilidad
                  </p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-2xl font-black text-[var(--color-text-primary)]">{baseEmpl + scenario.employabilityGain}%</p>
                    <p className="text-sm font-bold text-[var(--color-success)]">+{scenario.employabilityGain}%</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                    Timeframe
                  </p>
                  <p className="text-lg font-black text-[var(--color-text-primary)]">{scenario.timeframe}</p>
                </div>

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                    Inversión
                  </p>
                  <p className="text-lg font-black text-[var(--color-accent-red)]">{scenario.investment}</p>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-6 border-t border-[var(--color-border)]">
                <p className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-4">
                  Acciones Requeridas
                </p>
                <ul className="space-y-2">
                  {scenario.actions.map((action, aidx) => (
                    <li key={aidx} className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]">
                      <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Comparison Chart */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-8">Proyección de Impacto</h3>

        <div className="space-y-8">
          {/* Pertinencia */}
          <div>
            <h4 className="font-600 text-[var(--color-text-primary)] mb-6">Cobertura de Pertinencia</h4>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[var(--color-text-secondary)]">Estado Actual</span>
                  <span className="text-sm font-bold text-[var(--color-text-primary)]">76%</span>
                </div>
                <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--color-warning)] rounded-full" style={{ width: '76%' }} />
                </div>
              </div>

              {scenarios.map((s, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[var(--color-text-secondary)]">{s.name}</span>
                    <span className="text-sm font-bold text-[var(--color-success)]">{76 + s.pertinenceGain}%</span>
                  </div>
                  <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-success)] rounded-full"
                      style={{ width: `${76 + s.pertinenceGain}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Employability */}
          <div>
            <h4 className="font-600 text-[var(--color-text-primary)] mb-6">Tasa de Empleabilidad</h4>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[var(--color-text-secondary)]">Estado Actual</span>
                  <span className="text-sm font-bold text-[var(--color-text-primary)]">82%</span>
                </div>
                <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--color-success)] rounded-full" style={{ width: '82%' }} />
                </div>
              </div>

              {scenarios.map((s, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[var(--color-text-secondary)]">{s.name}</span>
                    <span className="text-sm font-bold text-[var(--color-success)]">{82 + s.employabilityGain}%</span>
                  </div>
                  <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-success)] rounded-full"
                      style={{ width: `${82 + s.employabilityGain}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="mt-8 rounded-xl border border-[var(--color-success)] border-opacity-30 bg-[var(--color-success)] bg-opacity-5 p-8">
        <div className="flex items-start gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-success)]">
            <TrendingUp size={20} className="text-white" />
          </div>
          <div>
            <h3 className="font-bold text-[var(--color-text-primary)] mb-2">Recomendación Estratégica</h3>
            <p className="text-[var(--color-text-secondary)] mb-3">
              Se recomienda la <strong>Transformación Completa</strong> para maximizar el impacto. Aunque requiere mayor inversión inicial,
              proyecta el mayor ROI (420%) y cierra las brechas críticas de forma integral. Se sugiere implementación gradual en 3 fases:
            </p>
            <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
                <strong>Fase 1 (Mes 1-2):</strong> Actualizar fundamentales y crear electivas en AI/ML
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
                <strong>Fase 2 (Mes 3-4):</strong> Implementar especialización DevOps y Cloud
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
                <strong>Fase 3 (Mes 5-8):</strong> Establecer tracks, laboratorios y partnerships
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
