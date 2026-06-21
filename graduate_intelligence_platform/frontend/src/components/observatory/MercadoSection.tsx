import { Briefcase, Star } from 'lucide-react';

interface Skill {
  name: string;
  demandPercentage: number;
  salaryRangeMin: number;
  salaryRangeMax: number;
  experienceRequired: string;
  urgency: 'high' | 'medium' | 'low';
}

const skills: Skill[] = [
  {
    name: 'Python & Data Analysis',
    demandPercentage: 94,
    salaryRangeMin: 4500,
    salaryRangeMax: 7200,
    experienceRequired: '1-3 años',
    urgency: 'high',
  },
  {
    name: 'Agile & Scrum Methodologies',
    demandPercentage: 87,
    salaryRangeMin: 4800,
    salaryRangeMax: 7500,
    experienceRequired: '2-4 años',
    urgency: 'high',
  },
  {
    name: 'Cloud Architecture (AWS)',
    demandPercentage: 82,
    salaryRangeMin: 5200,
    salaryRangeMax: 8500,
    experienceRequired: '2-5 años',
    urgency: 'high',
  },
  {
    name: 'Machine Learning & AI',
    demandPercentage: 78,
    salaryRangeMin: 5500,
    salaryRangeMax: 9000,
    experienceRequired: '3-5 años',
    urgency: 'high',
  },
  {
    name: 'UI/UX Design Principles',
    demandPercentage: 71,
    salaryRangeMin: 4200,
    salaryRangeMax: 6800,
    experienceRequired: '1-3 años',
    urgency: 'medium',
  },
  {
    name: 'DevOps & CI/CD Pipelines',
    demandPercentage: 68,
    salaryRangeMin: 5000,
    salaryRangeMax: 8000,
    experienceRequired: '2-4 años',
    urgency: 'medium',
  },
];

export function MercadoSection() {
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
              {skills.map((skill, idx) => (
                <tr
                  key={idx}
                  className="border-b border-[var(--color-border)] hover:bg-[var(--color-background)] transition-colors"
                >
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <Star size={16} className="text-[var(--color-accent-red)]" strokeWidth={1.5} />
                      <span className="font-600 text-[var(--color-text-primary)]">{skill.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 max-w-xs h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[var(--color-success)] to-[var(--color-accent-red)]"
                          style={{ width: `${skill.demandPercentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-[var(--color-text-primary)] w-12 text-right">
                        {skill.demandPercentage}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-sm font-600 text-[var(--color-text-primary)]">
                      ${skill.salaryRangeMin.toLocaleString()} - ${skill.salaryRangeMax.toLocaleString()}
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-sm text-[var(--color-text-secondary)]">{skill.experienceRequired}</span>
                  </td>
                  <td className="px-6 py-5 text-center">
                    <span
                      className={`inline-block px-3 py-1.5 text-xs font-bold rounded-full ${
                        skill.urgency === 'high'
                          ? 'bg-[var(--color-error)] text-white'
                          : 'bg-[var(--color-warning)] text-white'
                      }`}
                    >
                      {skill.urgency === 'high' ? 'CRÍTICA' : 'MEDIA'}
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
            {skills.slice(0, 3).map((skill, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-red)] text-white text-xs font-bold flex-shrink-0">
                  {idx + 1}
                </span>
                <span className="text-[var(--color-text-primary)] font-500">{skill.name}</span>
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
