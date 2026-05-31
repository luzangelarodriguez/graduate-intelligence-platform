import { ArrowUpRight, BarChart3, BriefcaseBusiness, GraduationCap, Layers3 } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { useDashboardData } from '../hooks/useDashboardData';

export function ProgramsPage() {
  const { programs, isLoading, error } = useDashboardData();

  if (isLoading) return <LoadingState label="Cargando inteligencia curricular..." />;
  if (error) return <EmptyState title="No se pudo cargar inteligencia curricular" body={error} />;

  const totalPrograms = programs.length;
  const programsWithLaborSignal = programs.filter((program) => Number(program.total_empleos_relacionados || 0) > 0).length;
  const averageMatch =
    programs.reduce((total, program) => total + Number(program.promedio_match_mercado || 0), 0) / Math.max(1, programs.length);

  const sortedPrograms = [...programs]
    .sort((a, b) => Number(b.promedio_match_mercado || 0) - Number(a.promedio_match_mercado || 0))
    .slice(0, 18);

  return (
    <section className="curriculum-intelligence-page">
      <div className="curriculum-hero panel">
        <div>
          <span>Observatorio SNIES · Inteligencia competitiva virtual</span>
          <h2>Inteligencia curricular</h2>
          <p>
            Benchmark competitivo universitario virtual para analizar pertinencia academica, posicionamiento curricular
            y señales de empleabilidad.
          </p>
        </div>
        <div className="curriculum-summary-grid">
          <article>
            <GraduationCap size={17} strokeWidth={1.8} />
            <span>Programas</span>
            <strong>{totalPrograms}</strong>
          </article>
          <article>
            <BriefcaseBusiness size={17} strokeWidth={1.8} />
            <span>Con señal laboral</span>
            <strong>{programsWithLaborSignal}</strong>
          </article>
          <article>
            <BarChart3 size={17} strokeWidth={1.8} />
            <span>Match promedio</span>
            <strong>{averageMatch.toFixed(1)}%</strong>
          </article>
        </div>
      </div>

      <div className="panel curriculum-benchmark-panel">
        <div className="section-head">
          <div>
            <h3>Benchmark competitivo universitario virtual</h3>
            <p>Programas priorizados por pertinencia, cobertura de capacidades y posicionamiento estrategico.</p>
          </div>
        </div>

        <div className="curriculum-list">
          {sortedPrograms.map((program, index) => {
            const score = Number(program.promedio_match_mercado || 0);
            const skills = Number(program.total_skills_programa || 0);
            const jobs = Number(program.total_empleos_relacionados || 0);

            return (
            <Link className="curriculum-list-item" key={program.especializacion_id} to={`/programs/${program.especializacion_id}`}>
              <div className="curriculum-rank">{String(index + 1).padStart(2, '0')}</div>
              <div className="curriculum-item-main">
                <strong>{program.nombre_especializacion}</strong>
                <span>{program.rol || 'Perfil academico en analisis comparativo'}</span>
              </div>
                <div className="curriculum-item-metrics">
                  <span>
                    <Layers3 size={14} strokeWidth={1.8} />
                    {skills} skills
                  </span>
                  <span>
                    <BriefcaseBusiness size={14} strokeWidth={1.8} />
                    {jobs} señales
                  </span>
                  <strong>{score.toFixed(1)}%</strong>
                </div>
              <ArrowUpRight className="curriculum-item-action" size={16} strokeWidth={1.8} />
            </Link>
          );
        })}
      </div>
    </div>
    </section>
  );
}
