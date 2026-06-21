import { Lightbulb, CheckCircle2, Clock, Zap, AlertCircle } from 'lucide-react';
import { SkillsAnalysis } from '../../services/observatoryApi';

interface RecomendacionesSectionProps {
  data: SkillsAnalysis | null;
  loading: boolean;
  error: string | null;
}

interface Recommendation {
  title: string;
  description: string;
  priority: 'urgent' | 'high' | 'medium';
  impact: 'alto' | 'medio' | 'bajo';
  timeframe: string;
  owner: string;
  kpi: string;
  keyActions: string[];
}

const recommendations: Recommendation[] = [
  {
    title: 'Integrar Módulo de Machine Learning & AI',
    description: 'Crear contenido de ML/AI que cubra desde conceptos fundamentales hasta aplicaciones prácticas',
    priority: 'urgent',
    impact: 'alto',
    timeframe: '6-8 semanas',
    owner: 'Director Académico',
    kpi: 'Cobertura de IA sube de 30% a 85%',
    keyActions: [
      'Seleccionar framework (TensorFlow/PyTorch)',
      'Desarrollar 8 casos de estudio reales',
      'Crear laboratorios prácticos',
      'Certificación Google/AWS AI Associate',
    ],
  },
  {
    title: 'Implementar DevOps en Pipeline de Desarrollo',
    description: 'Establecer prácticas DevOps desde infraestructura hasta deployment continuo',
    priority: 'urgent',
    impact: 'alto',
    timeframe: '4-6 semanas',
    owner: 'Coordinador Técnico',
    kpi: 'DevOps coverage sube de 20% a 90%',
    keyActions: [
      'Laboratorio Docker/Kubernetes',
      'Pipeline CI/CD con GitHub Actions',
      'Monitoring y alerting systems',
      'Jenkins/GitLab CI setup',
    ],
  },
  {
    title: 'Expandir Cobertura de Cloud Computing',
    description: 'Profundizar en arquitecturas cloud, migración y optimización de costos',
    priority: 'high',
    impact: 'alto',
    timeframe: '4-5 semanas',
    owner: 'Especialista Cloud',
    kpi: 'Cloud coverage sube de 45% a 95%',
    keyActions: [
      'Crear 3 especialidades: AWS, Azure, GCP',
      'Proyecto capstone con aplicación real en cloud',
      'Certificación AWS Associate',
      'Workshops de arquitectura',
    ],
  },
  {
    title: 'Fortalecer Liderazgo Ágil & Soft Skills',
    description: 'Desarrollo de competencias blandas críticas para la empleabilidad',
    priority: 'high',
    impact: 'medio',
    timeframe: '3-4 semanas',
    owner: 'Coordinador HR',
    kpi: 'Soft skills score sube de 68% a 88%',
    keyActions: [
      'Certificación Scrum Master (PSM I)',
      'Coaching en comunicación y liderazgo',
      'Mentoring de ejecutivos',
      'Simulaciones de gestión de proyectos',
    ],
  },
  {
    title: 'Crear Especialización en Data Science',
    description: 'Track especializado en análisis de datos y estadística aplicada',
    priority: 'high',
    impact: 'medio',
    timeframe: '5-6 semanas',
    owner: 'Director Académico',
    kpi: 'Data Science coverage sube de 35% a 90%',
    keyActions: [
      'Crear electiva Data Science (3 créditos)',
      'Lab con datasets reales',
      'Herramientas: Python, R, Tableau',
      'Proyecto con empresa partner',
    ],
  },
  {
    title: 'Establecer Partnerships con Industria',
    description: 'Crear alianzas con empresas tech para proyectos reales y mentoría',
    priority: 'medium',
    impact: 'alto',
    timeframe: '8-12 semanas',
    owner: 'Vicerrector Relaciones Externas',
    kpi: 'Empleabilidad sube de 82% a 96%',
    keyActions: [
      'Identificar 10+ empresas target',
      'Negociar proyectos capstone',
      'Guest lectures mensuales',
      'Bolsa de empleos prioritaria',
    ],
  },
];

function getPriorityColor(priority: string) {
  if (priority === 'urgent') return 'bg-[var(--color-error)]';
  if (priority === 'high') return 'bg-[var(--color-warning)]';
  return 'bg-[var(--color-success)]';
}

function getPriorityLabel(priority: string) {
  if (priority === 'urgent') return 'URGENTE';
  if (priority === 'high') return 'ALTA';
  return 'MEDIA';
}

export function RecomendacionesSection({ data, loading, error }: RecomendacionesSectionProps) {
  if (loading) {
    return (
      <section id="section-recomendaciones" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <Lightbulb size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Recomendaciones
          </h2>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-12 text-center">
          <div className="animate-pulse text-[var(--color-text-secondary)]">Cargando datos...</div>
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section id="section-recomendaciones" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <Lightbulb size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Recomendaciones
          </h2>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 flex items-center gap-3">
          <AlertCircle size={20} className="text-[var(--color-accent-red)]" />
          <span className="text-[var(--color-text-secondary)]">
            {error || 'Datos en construcción'}
          </span>
        </div>
      </section>
    );
  }

  const urgentCount = recommendations.filter((r: any) => r.priority === 'urgent').length;
  const highImpact = recommendations.filter((r: any) => r.impact === 'alto').length;

  return (
    <section id="section-recomendaciones" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <Lightbulb size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Recomendaciones Estratégicas
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Acciones prioritarias para mejorar la pertinencia y empleabilidad del programa
        </p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Acciones Urgentes
          </p>
          <p className="text-4xl font-black text-[var(--color-error)]">{urgentCount}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">requieren inicio inmediato</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Alto Impacto
          </p>
          <p className="text-4xl font-black text-[var(--color-success)]">{highImpact}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">iniciativas de alto impacto</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Timeframe Total
          </p>
          <p className="text-4xl font-black text-[var(--color-text-primary)]">8-12</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">semanas implementación</p>
        </div>
      </div>

      {/* Recommendations Cards */}
      <div className="space-y-4 mb-8">
        {recommendations.map((rec, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <Zap size={20} className="text-[var(--color-accent-red)]" />
                  <h3 className="text-lg font-bold text-[var(--color-text-primary)]">{rec.title}</h3>
                </div>
                <p className="text-[var(--color-text-secondary)] mb-4">{rec.description}</p>
              </div>
              <span
                className={`${getPriorityColor(rec.priority)} text-white px-4 py-2 rounded-lg text-xs font-bold whitespace-nowrap flex-shrink-0`}
              >
                {getPriorityLabel(rec.priority)}
              </span>
            </div>

            {/* KPI Highlight */}
            <div className="mb-4 p-4 rounded-lg bg-[var(--color-accent-red)] bg-opacity-5 border border-[var(--color-accent-red)] border-opacity-30">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                KPI de Éxito
              </p>
              <p className="text-sm font-600 text-[var(--color-text-primary)]">{rec.kpi}</p>
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-3 gap-4 mb-6 pt-4 border-t border-[var(--color-border)]">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Plazo
                </p>
                <p className="text-sm font-600 text-[var(--color-text-primary)] flex items-center gap-2">
                  <Clock size={16} />
                  {rec.timeframe}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Impacto
                </p>
                <p className="text-sm font-600 text-[var(--color-success)]">
                  {rec.impact === 'alto' ? 'Alto' : rec.impact === 'medio' ? 'Medio' : 'Bajo'}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                  Responsable
                </p>
                <p className="text-sm font-600 text-[var(--color-text-primary)]">{rec.owner}</p>
              </div>
            </div>

            {/* Actions */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
                Acciones Clave
              </p>
              <ul className="space-y-2">
                {rec.keyActions.map((action, aidx) => (
                  <li key={aidx} className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]">
                    <CheckCircle2 size={16} className="text-[var(--color-success)] mt-0.5 flex-shrink-0" />
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Implementation Timeline */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-8">Cronograma de Implementación</h3>

        <div className="space-y-6">
          {[
            {
              phase: 'Semanas 1-2: Inicio Rápido',
              color: 'bg-[var(--color-error)]',
              tasks: ['Formar equipo de implementación', 'Seleccionar herramientas y proveedores', 'Comunicar cambios a stakeholders'],
            },
            {
              phase: 'Semanas 3-6: Fase de Desarrollo',
              color: 'bg-[var(--color-warning)]',
              tasks: ['Crear contenidos de AI/ML', 'Setup de infraestructura DevOps', 'Iniciar partnerships con industria'],
            },
            {
              phase: 'Semanas 7-10: Piloto y Ajuste',
              color: 'bg-[var(--color-success)]',
              tasks: ['Piloto con primer cohorte', 'Recibir feedback y ajustar', 'Expandir a Cloud y Data Science'],
            },
            {
              phase: 'Semanas 11-12: Rollout Completo',
              color: 'bg-[var(--color-success)]',
              tasks: ['Lanzamiento oficial de cambios', 'Capacitación docente final', 'Medición y seguimiento'],
            },
          ].map((phase, idx) => (
            <div key={idx}>
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-3 h-3 rounded-full ${phase.color}`} />
                <h4 className="font-bold text-[var(--color-text-primary)]">{phase.phase}</h4>
              </div>
              <ul className="ml-6 space-y-1">
                {phase.tasks.map((task, tidx) => (
                  <li key={tidx} className="text-sm text-[var(--color-text-secondary)] flex items-center gap-2">
                    <span className="w-1 h-1 rounded-full bg-[var(--color-text-secondary)]" />
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Success Criteria */}
      <div className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-background)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-6">Criterios de Éxito</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-600 text-[var(--color-text-primary)] mb-3">Académicos</h4>
            <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                Pertinencia sube de 76% a 98%
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                Cobertura de emergentes de 30% a 90%+
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                Módulos de especialización implementados
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-600 text-[var(--color-text-primary)] mb-3">De Impacto</h4>
            <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                Empleabilidad egresados 82% → 96%
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                10+ partnerships activos con empresas
              </li>
              <li className="flex items-start gap-3">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
                Salarios iniciales +15-20% vs benchmark
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
