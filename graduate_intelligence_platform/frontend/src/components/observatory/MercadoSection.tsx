import { Briefcase, Star, AlertCircle } from 'lucide-react';
import { SkillsAnalysis } from '../../services/observatoryApi';

interface MercadoSectionProps {
  data: SkillsAnalysis | null;
  loading: boolean;
  error: string | null;
}

export function MercadoSection({ data, loading, error }: MercadoSectionProps) {
  if (loading) {
    return (
      <section id="section-mercado" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <Briefcase size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Qué Demanda el Mercado
          </h2>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-12 text-center">
          <div className="animate-pulse text-[var(--color-text-secondary)]">Cargando datos...</div>
        </div>
      </section>
    );
  }

  if (error || !data || !data.market_demanded_skills || data.market_demanded_skills.length === 0) {
    return (
      <section id="section-mercado" className="scroll-mt-24 mb-16">
        <div className="mb-8">
          <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
              <Briefcase size={24} className="text-[var(--color-accent-red)]" />
            </div>
            Qué Demanda el Mercado
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
  return (
    <section id="section-mercado" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <Briefcase size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Qué Demanda el Mercado
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Competencias más demandadas en el mercado laboral colombiano 2024
        </p>
      </div>

      {/* Skills Table */}
      <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-background)]">
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Competencia
                </th>
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Demanda
                </th>
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Salario Mensual (COP)
                </th>
                <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Experiencia
                </th>
                <th className="text-center px-6 py-4 text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Urgencia
                </th>
              </tr>
            </thead>
            <tbody>
              {data.market_demanded_skills.map((skill, idx) => (
                <tr
                  key={idx}
                  className="border-b border-[var(--color-border)] hover:bg-[var(--color-background)] transition-colors"
                >
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <Star size={16} className="text-[var(--color-accent-red)]" strokeWidth={1.5} />
                      <span className="font-600 text-[var(--color-text-primary)]">{skill.skill}</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 max-w-xs h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[var(--color-success)] to-[var(--color-accent-red)]"
                          style={{ width: `${skill.demand_level === 'high' ? 90 : skill.demand_level === 'medium' ? 70 : 50}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-[var(--color-text-primary)] w-12 text-right">
                        {skill.demand_level === 'high' ? '90%' : skill.demand_level === 'medium' ? '70%' : '50%'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-sm font-600 text-[var(--color-text-primary)]">
                      {skill.salary_range}
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-sm text-[var(--color-text-secondary)]">{skill.demand_level}</span>
                  </td>
                  <td className="px-6 py-5 text-center">
                    <span
                      className={`inline-block px-3 py-1.5 text-xs font-bold rounded-full ${
                        skill.demand_level === 'high'
                          ? 'bg-[var(--color-error)] text-white'
                          : 'bg-[var(--color-warning)] text-white'
                      }`}
                    >
                      {skill.demand_level === 'high' ? 'CRÍTICA' : 'MEDIA'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Market Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <h3 className="font-bold text-[var(--color-text-primary)] mb-4">Top 3 Skills Críticas</h3>
          <ol className="space-y-3">
            {data.market_demanded_skills.slice(0, 3).map((skill, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-red)] text-white text-xs font-bold flex-shrink-0">
                  {idx + 1}
                </span>
                <span className="text-[var(--color-text-primary)] font-500">{skill.skill}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <h3 className="font-bold text-[var(--color-text-primary)] mb-4">Insights del Mercado</h3>
          <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
              <span>
                <strong className="text-[var(--color-text-primary)]">Crecimiento de demanda:</strong> Skills en IA y Cloud crecen 45% YoY
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)] mt-1.5 flex-shrink-0" />
              <span>
                <strong className="text-[var(--color-text-primary)]">Salarios competitivos:</strong> Profesionales con skill stack completo ganan 60% más
              </span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
