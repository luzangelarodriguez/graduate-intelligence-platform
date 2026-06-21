import { AlertCircle, TrendingUp, Clock, AlertCircle as AlertIcon } from 'lucide-react';
import { SkillsAnalysis } from '../../services/observatoryApi';

interface BrechasSectionProps {
  data: SkillsAnalysis | null;
  loading: boolean;
  error: string | null;
}

interface Gap {
  skill: string;
  gap: number;
  urgency: 'critical' | 'high' | 'medium';
  timeToClose: string;
  impactLevel: string;
  recommendedAction: string;
}

const defaultGaps: Gap[] = [
  {
    skill: 'Artificial Intelligence & Machine Learning',
    gap: 70,
    urgency: 'critical',
    timeToClose: '6-8 meses',
    impactLevel: 'Muy Alto',
    recommendedAction: 'Crear módulo especializado de 3 créditos + capstone con ML',
  },
  {
    skill: 'DevOps & Infrastructure Automation',
    gap: 80,
    urgency: 'critical',
    timeToClose: '4-6 meses',
    impactLevel: 'Muy Alto',
    recommendedAction: 'Integrar contenido DevOps en desarrollo y crear laboratorio CI/CD',
  },
  {
    skill: 'Cloud Architecture & Deployment',
    gap: 55,
    urgency: 'high',
    timeToClose: '3-4 meses',
    impactLevel: 'Alto',
    recommendedAction: 'Ampliar AWS basics a arquitectura completa con casos reales',
  },
  {
    skill: 'Agile Leadership & Team Management',
    gap: 45,
    urgency: 'high',
    timeToClose: '2-3 meses',
    impactLevel: 'Medio-Alto',
    recommendedAction: 'Fortalecimiento de módulo de soft skills con certificación Scrum',
  },
  {
    skill: 'Data Science & Analytics',
    gap: 65,
    urgency: 'high',
    timeToClose: '5-6 meses',
    impactLevel: 'Alto',
    recommendedAction: 'Crear electiva de Data Science con Python + visualización',
  },
  {
    skill: 'Microservices & Distributed Systems',
    gap: 75,
    urgency: 'high',
    timeToClose: '4-5 meses',
    impactLevel: 'Alto',
    recommendedAction: 'Módulo avanzado en arquitectura de microservicios con Docker/K8s',
  },
];

function getUrgencyColor(urgency: string) {
  if (urgency === 'critical') return 'bg-[var(--color-error)]';
  if (urgency === 'high') return 'bg-[var(--color-warning)]';
  return 'bg-[var(--color-success)]';
}

function getUrgencyLabel(urgency: string) {
  if (urgency === 'critical') return 'CRÍTICA';
  if (urgency === 'high') return 'ALTA';
  return 'MEDIA';
}

export function BrechasSection({ data, loading, error }: BrechasSectionProps) {
  if (loading) {
    return (
      <section id="section-brechas" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <AlertCircle size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Brechas Identificadas
          </h2>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-12 text-center">
          <div className="animate-pulse text-[var(--color-text-secondary)]">Cargando datos...</div>
        </div>
      </section>
    );
  }

  if (error || !data || !data.skill_gaps || data.skill_gaps.length === 0) {
    return (
      <section id="section-brechas" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <AlertCircle size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Brechas Identificadas
          </h2>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 flex items-center gap-3">
          <AlertIcon size={20} className="text-[var(--color-accent-red)]" />
          <span className="text-[var(--color-text-secondary)]">
            {error || 'Datos en construcción'}
          </span>
        </div>
      </section>
    );
  }

  const gaps = defaultGaps;
  const totalGap = gaps.reduce((sum: number, gap: any) => sum + (gap.gap || 0), 0) / gaps.length;
  const criticalCount = gaps.filter((gap: any) => gap.urgency === 'critical').length;

  return (
    <section id="section-brechas" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <AlertCircle size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Brechas Identificadas
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Competencias demandadas que no están cubiertas por el programa actual
        </p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Brecha Promedio
          </p>
          <p className="text-4xl font-black text-[var(--color-text-primary)]">{totalGap}%</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">de diferencia promedio</p>
        </div>

        <div className="rounded-xl border border-[var(--color-error)] border-opacity-30 bg-[var(--color-error)] bg-opacity-5 p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-error)] mb-3">
            Brechas Críticas
          </p>
          <p className="text-4xl font-black text-[var(--color-error)]">{criticalCount}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">requieren atención inmediata</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Competencias Analizadas
          </p>
          <p className="text-4xl font-black text-[var(--color-text-primary)]">{gaps.length}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">areas de oportunidad</p>
        </div>
      </div>

      {/* Gaps Cards */}
      <div className="space-y-4">
        {gaps.map((gap, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp size={18} className="text-[var(--color-accent-red)]" />
                  <h3 className="text-lg font-bold text-[var(--color-text-primary)]">{gap.skill}</h3>
                </div>
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">{gap.recommendedAction}</p>
              </div>
              <span
                className={`${getUrgencyColor(gap.urgency)} text-white px-4 py-2 rounded-lg text-xs font-bold whitespace-nowrap flex-shrink-0`}
              >
                {getUrgencyLabel(gap.urgency)}
              </span>
            </div>

            {/* Gap Visual */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)]">Brecha Identificada</span>
                <span className="text-sm font-bold text-[var(--color-text-primary)]">{gap.gap}%</span>
              </div>
              <div className="h-2.5 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    gap.urgency === 'critical'
                      ? 'bg-[var(--color-error)]'
                      : gap.urgency === 'high'
                        ? 'bg-[var(--color-warning)]'
                        : 'bg-[var(--color-success)]'
                  }`}
                  style={{ width: `${gap.gap}%` }}
                />
              </div>
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[var(--color-border)]">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Tiempo Estimado
                </p>
                <p className="text-sm font-600 text-[var(--color-text-primary)] flex items-center gap-2">
                  <Clock size={16} />
                  {gap.timeToClose}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Impacto
                </p>
                <p className="text-sm font-600 text-[var(--color-text-primary)]">{gap.impactLevel}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Estado
                </p>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-[var(--color-background)] text-[var(--color-text-primary)]">
                  NO CUBIERTO
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Action Plan Summary */}
      <div className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-background)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-6">Plan de Acción Recomendado</h3>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-accent-red)] text-white text-sm font-bold flex-shrink-0">
              1
            </div>
            <div>
              <p className="font-600 text-[var(--color-text-primary)]">Fase Inmediata (1-2 meses)</p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                Actualizar currículo para incorporar ML basics, DevOps essentials y expandir cobertura de Cloud
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-accent-red)] text-white text-sm font-bold flex-shrink-0">
              2
            </div>
            <div>
              <p className="font-600 text-[var(--color-text-primary)]">Fase Corto Plazo (3-4 meses)</p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                Crear electivas especializadas: Data Science, Microservicios, Liderazgo Ágil con certificaciones
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-accent-red)] text-white text-sm font-bold flex-shrink-0">
              3
            </div>
            <div>
              <p className="font-600 text-[var(--color-text-primary)]">Fase Mediano Plazo (6-8 meses)</p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                Establecer tracks de especialización y partnerships con empresas para proyectos reales
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
