import { Users, TrendingUp, Briefcase } from 'lucide-react';

interface JobRole {
  role: string;
  alignment: number;
  vacanciesPerYear: number;
  avgSalary: number;
  growthRate: number;
  requiredSkills: string[];
  matchLevel: 'excellent' | 'good' | 'fair';
}

const jobRoles: JobRole[] = [
  {
    role: 'Software Developer / Engineer',
    alignment: 94,
    vacanciesPerYear: 1200,
    avgSalary: 5800,
    growthRate: 22,
    requiredSkills: ['OOP', 'APIs', 'Testing', 'Git'],
    matchLevel: 'excellent',
  },
  {
    role: 'Full Stack Developer',
    alignment: 91,
    vacanciesPerYear: 950,
    avgSalary: 6200,
    growthRate: 25,
    requiredSkills: ['Frontend', 'Backend', 'Databases', 'Deployment'],
    matchLevel: 'excellent',
  },
  {
    role: 'Frontend Developer / React Specialist',
    alignment: 88,
    vacanciesPerYear: 720,
    avgSalary: 5400,
    growthRate: 18,
    requiredSkills: ['React', 'CSS', 'JavaScript', 'UI/UX'],
    matchLevel: 'good',
  },
  {
    role: 'Backend Developer',
    alignment: 89,
    vacanciesPerYear: 650,
    avgSalary: 5700,
    growthRate: 20,
    requiredSkills: ['Node.js', 'Databases', 'APIs', 'Architecture'],
    matchLevel: 'good',
  },
  {
    role: 'QA Automation Engineer',
    alignment: 78,
    vacanciesPerYear: 380,
    avgSalary: 4900,
    growthRate: 15,
    requiredSkills: ['Testing', 'Automation', 'CI/CD', 'Python'],
    matchLevel: 'good',
  },
  {
    role: 'DevOps Engineer',
    alignment: 45,
    vacanciesPerYear: 420,
    avgSalary: 6500,
    growthRate: 35,
    requiredSkills: ['AWS/Cloud', 'CI/CD', 'Docker', 'Linux'],
    matchLevel: 'fair',
  },
  {
    role: 'Data Scientist / Analyst',
    alignment: 42,
    vacanciesPerYear: 380,
    avgSalary: 6100,
    growthRate: 40,
    requiredSkills: ['Python', 'SQL', 'ML', 'Visualization'],
    matchLevel: 'fair',
  },
  {
    role: 'Cloud Architect',
    alignment: 38,
    vacanciesPerYear: 180,
    avgSalary: 7200,
    growthRate: 45,
    requiredSkills: ['AWS/Azure', 'Architecture', 'DevOps', 'Security'],
    matchLevel: 'fair',
  },
];

function getMatchColor(match: string) {
  if (match === 'excellent') return 'bg-[var(--color-success)]';
  if (match === 'good') return 'bg-[var(--color-warning)]';
  return 'bg-[var(--color-error)]';
}

function getMatchLabel(match: string) {
  if (match === 'excellent') return 'EXCELENTE';
  if (match === 'good') return 'BUENO';
  return 'REGULAR';
}

export function EmpleosSection() {
  const topJobs = jobRoles.filter(j => j.alignment > 85);
  const totalVacancies = jobRoles.reduce((sum, j) => sum + j.vacanciesPerYear, 0);

  return (
    <section id="section-empleos" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <Users size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Empleos Compatibles
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Roles laborales para los cuales el programa prepara adecuadamente a los egresados
        </p>
      </div>

      {/* Market Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Vacantes Anuales
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)] mb-2">
            {(totalVacancies / 1000).toFixed(1)}K+
          </p>
          <p className="text-xs text-[var(--color-text-secondary)]">oportunidades de empleo</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Roles Mejor Alineados
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)] mb-2">{topJobs.length}</p>
          <p className="text-xs text-[var(--color-text-secondary)]">con alineación 85%+</p>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
            Salario Promedio
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)] mb-2">
            ${Math.round(jobRoles.reduce((sum, j) => sum + j.avgSalary, 0) / jobRoles.length)}K
          </p>
          <p className="text-xs text-[var(--color-text-secondary)]">salario mensual COP (miles)</p>
        </div>
      </div>

      {/* Job Roles Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {jobRoles.map((job, idx) => (
          <div
            key={idx}
            className={`rounded-xl border-2 bg-[var(--color-surface)] p-6 transition-all hover:shadow-md ${
              job.matchLevel === 'excellent'
                ? 'border-[var(--color-success)] border-opacity-30'
                : job.matchLevel === 'good'
                  ? 'border-[var(--color-warning)] border-opacity-30'
                  : 'border-[var(--color-error)] border-opacity-30'
            }`}
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Briefcase size={18} className="text-[var(--color-accent-red)]" />
                  <h3 className="text-base font-bold text-[var(--color-text-primary)]">{job.role}</h3>
                </div>
              </div>
              <span
                className={`${getMatchColor(job.matchLevel)} text-white px-3 py-1 rounded-lg text-xs font-bold whitespace-nowrap`}
              >
                {getMatchLabel(job.matchLevel)}
              </span>
            </div>

            {/* Alignment Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)]">Alineación con Programa</span>
                <span className="text-sm font-bold text-[var(--color-text-primary)]">{job.alignment}%</span>
              </div>
              <div className="h-2.5 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${getMatchColor(job.matchLevel)}`}
                  style={{ width: `${job.alignment}%` }}
                />
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[var(--color-border)] mb-4">
              <div>
                <p className="text-xs text-[var(--color-text-secondary)] mb-1">Vacantes/Año</p>
                <p className="text-lg font-black text-[var(--color-text-primary)]">{job.vacanciesPerYear}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-secondary)] mb-1">Crecimiento</p>
                <p className="text-lg font-black text-[var(--color-success)] flex items-center gap-1">
                  <TrendingUp size={16} />
                  {job.growthRate}%
                </p>
              </div>
            </div>

            {/* Skills Required */}
            <div className="pt-4 border-t border-[var(--color-border)]">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
                Skills Requeridas
              </p>
              <div className="flex flex-wrap gap-2">
                {job.requiredSkills.map((skill, sidx) => (
                  <span
                    key={sidx}
                    className="text-xs bg-[var(--color-background)] text-[var(--color-text-primary)] rounded-full px-3 py-1.5 font-600"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Career Pathways */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-6">Rutas de Carrera Recomendadas</h3>
        <div className="space-y-6">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-success)] text-white font-bold text-sm">
                1
              </div>
              <h4 className="font-bold text-[var(--color-text-primary)]">Especialista en Backend</h4>
            </div>
            <div className="ml-11 flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Backend Developer</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Senior Engineer</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Architect</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-warning)] text-white font-bold text-sm">
                2
              </div>
              <h4 className="font-bold text-[var(--color-text-primary)]">Full Stack Developer</h4>
            </div>
            <div className="ml-11 flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Full Stack Dev</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Tech Lead</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Product Manager</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--color-accent-red)] text-white font-bold text-sm">
                3
              </div>
              <h4 className="font-bold text-[var(--color-text-primary)]">Especialista DevOps/Cloud</h4>
            </div>
            <div className="ml-11 flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Backend + DevOps</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">DevOps Engineer</span>
              <span className="text-[var(--color-text-primary)] font-bold">→</span>
              <span className="px-3 py-1 bg-[var(--color-background)] rounded-full">Cloud Architect</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
