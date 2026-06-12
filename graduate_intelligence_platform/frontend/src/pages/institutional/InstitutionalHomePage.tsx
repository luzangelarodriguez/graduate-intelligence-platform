import { Link } from 'react-router-dom';

import {
  DataTable,
  EmptyDiagnostic,
  LoadingPanel,
  MetricCard,
  PageHero,
  QuickLink,
  SectionCard,
  StatusBadge,
} from '../../components/institutional/InstitutionalPrimitives';
import { useInstitutionalSnapshot } from '../../hooks/useInstitutionalSnapshot';
import { average, numberLabel, pct, programEvidence, skillName } from './institutionalData';

export function InstitutionalHomePage() {
  const snapshot = useInstitutionalSnapshot();

  const alignments = snapshot.programIntelligence.map((program) => Number(program.alignment_score || 0));
  const risks = snapshot.programIntelligence.map((program) => Number(program.risk_score || 0));
  const criticalGaps = snapshot.programIntelligence.reduce((total, program) => total + Number(program.gap_count || 0), 0);
  const comparableUniversities = snapshot.programIntelligence.reduce((total, program) => {
    const { benchmark } = programEvidence(program);
    const institutions = Array.isArray(benchmark.benchmark_institutions) ? benchmark.benchmark_institutions.length : 0;
    return total + institutions;
  }, 0);
  const priorityPrograms = [...snapshot.programIntelligence]
    .sort((left, right) => Number(right.risk_score || 0) - Number(left.risk_score || 0))
    .slice(0, 5);
  const priorityGaps = snapshot.programIntelligence
    .flatMap((program) => programEvidence(program).gaps.map((gap) => ({ program: program.program_name, gap })))
    .slice(0, 6);

  return (
    <section className="institutional-page">
      <PageHero
        eyebrow="Inicio ejecutivo"
        title="Observatorio Institucional de Inteligencia Curricular"
        subtitle="Análisis de pertinencia académica basado en currículo, mercado laboral, skills, SNIES, simulación y recomendaciones."
      >
        <div className="institutional-actions">
          <QuickLink to="/diagnostico">Ver diagnóstico institucional</QuickLink>
          <QuickLink to="/skills-brechas">Ver brechas</QuickLink>
          <QuickLink to="/simulacion">Ejecutar simulación</QuickLink>
        </div>
      </PageHero>

      {snapshot.isLoading ? <LoadingPanel label="Cargando inicio ejecutivo institucional..." /> : null}

      <div className="institutional-grid four">
        <MetricCard label="Programas analizados" value={snapshot.isLoading ? 'Cargando...' : numberLabel(snapshot.programs.length)} detail="Programas disponibles en el catálogo académico." />
        <MetricCard label="Alineación promedio" value={snapshot.isLoading ? 'Cargando...' : pct(average(alignments))} detail="Promedio calculado desde inteligencia curricular por programa." />
        <MetricCard label="Riesgo curricular promedio" value={snapshot.isLoading ? 'Cargando...' : pct(average(risks))} detail="Riesgo promedio observado en programas con inteligencia disponible." />
        <MetricCard label="Brechas críticas" value={snapshot.isLoading ? 'Cargando...' : numberLabel(criticalGaps)} detail="Brechas activas agregadas desde program-intelligence." />
        <MetricCard label="Skills emergentes" value={snapshot.isLoading ? 'Cargando...' : numberLabel(snapshot.emergingSkills.length)} detail="Skills detectadas por el observatorio laboral." />
        <MetricCard label="Vacantes analizadas" value={snapshot.isLoading ? 'Cargando...' : numberLabel(snapshot.jobs.length)} detail="Vacantes entregadas por el endpoint laboral." />
        <MetricCard label="Universidades comparables" value={snapshot.isLoading ? 'Cargando...' : numberLabel(comparableUniversities)} detail="Instituciones SNIES o benchmark embebidas en evidencia de programa." />
        <MetricCard label="Recomendaciones activas" value={snapshot.isLoading ? 'Cargando...' : numberLabel(snapshot.recommendations.length)} detail="Recomendaciones institucionales del endpoint predictivo." />
      </div>

      <div className="institutional-grid two">
        <SectionCard title="Qué está ocurriendo" subtitle="Lectura ejecutiva para rectoría, vicerrectorías y comités académicos.">
          <p>
            {snapshot.isLoading
              ? 'La plataforma está consolidando el catálogo institucional y las señales de mercado. En cuanto termine el snapshot, se mostrarán programas, alineación, riesgo, brechas y evidencia laboral reales.'
              : `La institución cuenta con ${numberLabel(snapshot.programs.length)} programas en el catálogo y ${numberLabel(snapshot.programIntelligence.length)} registros de inteligencia curricular. La alineación promedio observada es ${pct(average(alignments))} y el riesgo curricular promedio es ${pct(average(risks))}. La principal decisión consiste en priorizar programas con brechas activas y evidencia laboral suficiente antes de convertir recomendaciones preliminares en acciones curriculares.`}
          </p>
        </SectionCard>

        <SectionCard title="Dónde actuar primero" subtitle="Programas y brechas con mayor presión curricular.">
          {snapshot.isLoading ? (
            <LoadingPanel label="Consolidando programas prioritarios..." />
          ) : priorityPrograms.length ? (
            <div className="grid gap-3">
              {priorityPrograms.map((program) => (
                <Link className="institutional-card shadow-none" key={program.program_id} to={`/programas/${program.program_id}`}>
                  <span className="institutional-card-label">Programa priorizado</span>
                  <h3>{program.program_name}</h3>
                  <p className="m-0 text-sm">Riesgo {pct(program.risk_score)} · Alineación {pct(program.alignment_score)} · Brechas {program.gap_count}</p>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyDiagnostic
              title="No hay programas priorizados."
              cause="El backend no entregó registros de inteligencia curricular para priorizar intervención."
              endpoint="/program-intelligence"
              action="Ejecute el pipeline de inteligencia de programas y valide las tablas de brechas."
            />
          )}
        </SectionCard>
      </div>

      <DataTable
        title="Evidencia disponible"
        subtitle="Estado de las principales entidades usadas para tomar decisiones."
        columns={['Entidad', 'Endpoint', 'Estado', 'Registros', 'Acción recomendada']}
        rows={snapshot.qualityRows.map((row) => [
          row.entity,
          row.endpoint,
          <StatusBadge status={row.status} />,
          numberLabel(row.records),
          row.action,
        ])}
        empty={
          <EmptyDiagnostic
            title="No hay diagnóstico de calidad de datos."
            cause="No se pudo construir el snapshot de calidad."
            endpoint="dataQualityService"
            action="Revise conectividad con backend y configuración de VITE_API_BASE_URL."
          />
        }
      />

      <DataTable
        title="Brechas prioritarias observadas"
        subtitle="Primeras brechas detectadas para orientar conversación académica."
        columns={['Programa', 'Skill o brecha', 'Demanda laboral', 'Cobertura curricular', 'Acción sugerida']}
        rows={priorityGaps.map(({ program, gap }) => [
          program,
          skillName(gap),
          pct(gap.market_demand_score),
          pct(gap.curriculum_coverage_score),
          String(gap.recommendation || 'Revisar profundidad curricular y evidencia laboral antes de priorizar.'),
        ])}
        empty={
          <EmptyDiagnostic
            title="No se encontraron brechas curriculares."
            cause="El endpoint respondió sin registros de gaps agregados."
            endpoint="/program-intelligence"
            action="Valide la carga de microcurrículos, la normalización de skills y curriculum_gap_observatory."
          />
        }
      />
    </section>
  );
}






