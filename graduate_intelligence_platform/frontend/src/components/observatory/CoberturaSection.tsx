import { CheckCircle2, BarChart3, AlertCircle } from 'lucide-react';
import { SkillsAnalysis } from '../../services/observatoryApi';

interface CoberturaSectionProps {
  data: SkillsAnalysis | null;
  loading: boolean;
  error: string | null;
}

interface CoverageTopic {
  name: string;
  coverage: number;
  status: 'covered' | 'partial' | 'missing';
  importance: number;
  remarks: string;
}

const defaultCoverageTopics: CoverageTopic[] = [
  { name: 'Python & Scripting', coverage: 100, status: 'covered', importance: 95, remarks: 'Completamente integrado' },
  { name: 'Web Development (React)', coverage: 90, status: 'covered', importance: 92, remarks: 'Requiere modernización' },
  { name: 'Backend Systems (Node.js)', coverage: 85, status: 'partial', importance: 88, remarks: 'Bases sólidas' },
  { name: 'Cloud Services (AWS)', coverage: 45, status: 'partial', importance: 90, remarks: 'Urgente ampliar' },
  { name: 'Artificial Intelligence/ML', coverage: 30, status: 'missing', importance: 92, remarks: 'Crítico: No cubierto' },
  { name: 'DevOps & Deployment', coverage: 20, status: 'missing', importance: 85, remarks: 'Crítico: Mínimo cubierto' },
  { name: 'Data Science & Analytics', coverage: 35, status: 'missing', importance: 75, remarks: 'Necesario adicionar' },
  { name: 'Security & Encryption', coverage: 55, status: 'partial', importance: 82, remarks: 'Ampliar cobertura' },
];

export function CoberturaSection({ data, loading, error }: CoberturaSectionProps) {
  if (loading) {
    return (
      <section id="section-cobertura" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <CheckCircle2 size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Cobertura Curricular
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
      <section id="section-cobertura" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <CheckCircle2 size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Cobertura Curricular
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

  const coverageTopics = defaultCoverageTopics;
  const totalCoverage = Math.round(coverageTopics.reduce((sum, t) => sum + t.coverage, 0) / coverageTopics.length);
  const criticalGaps = coverageTopics.filter(t => t.coverage < 50 && t.importance > 80).length;

  return (
    <section id="section-cobertura" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <CheckCircle2 size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Cobertura Curricular
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Análisis de alineación entre oferta académica y competencias del mercado
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Cobertura Promedio
          </p>
          <div className="flex items-end gap-4">
            <p className="text-4xl font-black text-[var(--color-text-primary)]">{totalCoverage}%</p>
            <div className="flex-1 flex items-end gap-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className={`h-8 rounded-t flex-1 ${i <= (totalCoverage / 20) ? 'bg-[var(--color-success)]' : 'bg-[var(--color-border)]'}`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--color-error)] border-opacity-30 bg-[var(--color-error)] bg-opacity-5 p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-error)] mb-3">
            Brechas Críticas
          </p>
          <p className="text-4xl font-black text-[var(--color-error)]">{criticalGaps}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">competencias vitales no cubiertas</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Temas Evaluados
          </p>
          <p className="text-4xl font-black text-[var(--color-text-primary)]">{coverageTopics.length}</p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">áreas clave del sector</p>
        </div>
      </div>

      {/* Coverage Matrix */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-background)]">
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Competencia
                </th>
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Cobertura
                </th>
                <th className="text-center px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Importancia
                </th>
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Observaciones
                </th>
              </tr>
            </thead>
            <tbody>
              {coverageTopics.map((topic, idx) => {
                const statusColor = topic.status === 'covered' ? 'bg-[var(--color-success)]' : topic.status === 'partial' ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-error)]';
                return (
                  <tr key={idx} className="border-b border-[var(--color-border)] hover:bg-[var(--color-background)] transition-colors">
                    <td className="px-6 py-5">
                      <span className="font-600 text-[var(--color-text-primary)]">{topic.name}</span>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 max-w-xs h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                          <div className={`h-full ${statusColor} rounded-full`} style={{ width: `${topic.coverage}%` }} />
                        </div>
                        <span className="text-sm font-bold text-[var(--color-text-primary)] w-12 text-right">
                          {topic.coverage}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-center">
                      <span className="inline-flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <span
                            key={i}
                            className={`w-2 h-2 rounded-full ${
                              i <= Math.round(topic.importance / 20) ? 'bg-[var(--color-accent-red)]' : 'bg-[var(--color-border)]'
                            }`}
                          />
                        ))}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className="text-sm text-[var(--color-text-secondary)]">{topic.remarks}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Key Findings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <div className="rounded-xl border border-[var(--color-success)] border-opacity-30 bg-[var(--color-success)] bg-opacity-5 p-6">
          <h3 className="font-bold text-[var(--color-success)] mb-4 flex items-center gap-2">
            <CheckCircle2 size={20} />
            Fortalezas
          </h3>
          <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
              <span>Cobertura completa (100%) en fundamentales de programación</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
              <span>Desarrollo web bien estructurado (90%) con frameworks modernos</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 flex-shrink-0" />
              <span>Backend y bases de datos sólidamente cubiertos (85%)</span>
            </li>
          </ul>
        </div>

        <div className="rounded-xl border border-[var(--color-error)] border-opacity-30 bg-[var(--color-error)] bg-opacity-5 p-6">
          <h3 className="font-bold text-[var(--color-error)] mb-4 flex items-center gap-2">
            <BarChart3 size={20} />
            Áreas de Oportunidad
          </h3>
          <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-error)] mt-1.5 flex-shrink-0" />
              <span>AI/ML apenas cubierto (30%) - demanda crítica del mercado</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-error)] mt-1.5 flex-shrink-0" />
              <span>DevOps minimamente tratado (20%) - deficiencia grave</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-error)] mt-1.5 flex-shrink-0" />
              <span>Cloud computing (45%) requiere expansión inmediata</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
