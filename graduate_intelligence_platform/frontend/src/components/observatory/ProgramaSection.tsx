import { BookOpen, CheckCircle2, AlertCircle } from 'lucide-react';

interface CurriculumArea {
  name: string;
  description: string;
  credits: number;
  percentage: number;
  subjects: string[];
  status: 'strong' | 'adequate' | 'weak';
}

const curriculumAreas: CurriculumArea[] = [
  {
    name: 'Fundamentos de Programación',
    description: 'Algoritmos, estructuras de datos y paradigmas',
    credits: 24,
    percentage: 100,
    subjects: ['Algoritmos', 'Estructuras de Datos', 'Programación Orientada a Objetos', 'Análisis de Complejidad'],
    status: 'strong',
  },
  {
    name: 'Desarrollo Web & Mobile',
    description: 'Frontend, backend y desarrollo multiplataforma',
    credits: 20,
    percentage: 92,
    subjects: ['Frontend (React)', 'Backend (Node.js)', 'Bases de Datos', 'APIs RESTful'],
    status: 'strong',
  },
  {
    name: 'Ingeniería de Software',
    description: 'Metodologías, testing y arquitectura de software',
    credits: 16,
    percentage: 75,
    subjects: ['Scrum/Agile', 'Testing Automatizado', 'Arquitectura de Software', 'Git & DevOps'],
    status: 'adequate',
  },
  {
    name: 'Tecnologías Emergentes',
    description: 'Cloud, AI/ML, Big Data y Blockchain',
    credits: 8,
    percentage: 35,
    subjects: ['Cloud Basics (AWS)', 'Machine Learning Intro', 'Big Data Concepts'],
    status: 'weak',
  },
  {
    name: 'Habilidades Profesionales',
    description: 'Liderazgo, comunicación y gestión de proyectos',
    credits: 12,
    percentage: 68,
    subjects: ['English Profesional', 'Liderazgo Ágil', 'Gestión de Proyectos'],
    status: 'adequate',
  },
];

function getStatusIcon(status: string) {
  if (status === 'strong') return <CheckCircle2 size={20} className="text-[var(--color-success)]" />;
  if (status === 'adequate') return <AlertCircle size={20} className="text-[var(--color-warning)]" />;
  return <AlertCircle size={20} className="text-[var(--color-error)]" />;
}

function getStatusColor(status: string) {
  if (status === 'strong') return 'bg-[var(--color-success)] bg-opacity-10 border-[var(--color-success)]';
  if (status === 'adequate') return 'bg-[var(--color-warning)] bg-opacity-10 border-[var(--color-warning)]';
  return 'bg-[var(--color-error)] bg-opacity-10 border-[var(--color-error)]';
}

function getStatusLabel(status: string) {
  if (status === 'strong') return 'Fortalecido';
  if (status === 'adequate') return 'Adecuado';
  return 'Débil';
}

export function ProgramaSection() {
  const totalCredits = curriculumAreas.reduce((sum, area) => sum + area.credits, 0);

  return (
    <section id="section-programa" className="scroll-mt-24 mb-16">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-[var(--color-text-primary)] flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-accent-red)] bg-opacity-10">
            <BookOpen size={24} className="text-[var(--color-accent-red)]" />
          </div>
          Qué Enseña el Programa
        </h2>
        <p className="text-lg text-[var(--color-text-secondary)]">
          Contenidos curriculares y estructura del programa académico
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
            Total de Créditos
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)]">{totalCredits}</p>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
            Áreas Curriculares
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)]">{curriculumAreas.length}</p>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
            Duración Estimada
          </p>
          <p className="text-3xl font-black text-[var(--color-text-primary)]">8 Semestres</p>
        </div>
      </div>

      {/* Curriculum Areas */}
      <div className="space-y-4">
        {curriculumAreas.map((area, idx) => (
          <div
            key={idx}
            className={`rounded-xl border-2 ${getStatusColor(area.status)} bg-[var(--color-surface)] p-6 transition-all hover:shadow-md`}
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  {getStatusIcon(area.status)}
                  <h3 className="text-lg font-bold text-[var(--color-text-primary)]">{area.name}</h3>
                </div>
                <p className="text-sm text-[var(--color-text-secondary)]">{area.description}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-2xl font-black text-[var(--color-text-primary)]">{area.credits}</p>
                <p className="text-xs text-[var(--color-text-secondary)]">créditos</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)]">
                  Cobertura del Currículo
                </span>
                <span className="text-xs font-bold text-[var(--color-text-primary)]">{area.percentage}%</span>
              </div>
              <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    area.status === 'strong'
                      ? 'bg-[var(--color-success)]'
                      : area.status === 'adequate'
                        ? 'bg-[var(--color-warning)]'
                        : 'bg-[var(--color-error)]'
                  }`}
                  style={{ width: `${area.percentage}%` }}
                />
              </div>
            </div>

            {/* Subjects */}
            <div className="pt-4 border-t border-[var(--color-border)]">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
                Asignaturas Ofertadas
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                {area.subjects.map((subject, sidx) => (
                  <div
                    key={sidx}
                    className="text-sm text-[var(--color-text-primary)] bg-[var(--color-background)] rounded-lg px-3 py-2 flex items-center gap-2"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-red)]" />
                    {subject}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Distribution Chart */}
      <div className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-6">Distribución por Área</h3>
        <div className="space-y-4">
          {curriculumAreas.map((area, idx) => {
            const percentage = (area.credits / totalCredits) * 100;
            return (
              <div key={idx}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-600 text-[var(--color-text-primary)]">{area.name}</span>
                  <span className="text-sm font-bold text-[var(--color-accent-red)]">{percentage.toFixed(0)}%</span>
                </div>
                <div className="h-3 bg-[var(--color-border)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[var(--color-accent-red)] to-[var(--color-navy)] rounded-full transition-all"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
