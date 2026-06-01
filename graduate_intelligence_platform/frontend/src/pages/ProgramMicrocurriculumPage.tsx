import { useParams } from 'react-router-dom';
import { Layers3 } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { MetricCard, ProgramPageHeader, ProgramSelectorStrip, ProgramTabs, SectionTitle } from '../components/program-intelligence/ProgramIntelligenceBlocks';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useProgramCatalog } from '../hooks/useProgramCatalog';
import { useProgramIntelligenceData } from '../hooks/useProgramIntelligenceData';
import { useNavigate } from 'react-router-dom';

function programIdFromParam(value?: string) {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function skillLabel(value: unknown) {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return String(record.nombre ?? record.skill ?? record.name ?? 'Skill').trim();
  }
  return 'Skill';
}

export function ProgramMicrocurriculumPage() {
  const { programId: programIdParam } = useParams();
  const navigate = useNavigate();
  const programId = programIdFromParam(programIdParam);
  const { programs: programCatalog } = useProgramCatalog();
  const { program, programIntelligence, curriculumRisk, alignment, isLoading, error } = useProgramIntelligenceData(programId);
  const { programSummary, isLoading: executiveAiLoading, error: executiveAiError } = useExecutiveAi(programId);

  if (!programId) {
    return <EmptyState title="Programa no válido" body="La ruta no contiene un identificador de programa válido." />;
  }

  if (isLoading) {
    return <LoadingState label="Cargando análisis de microcurrículum..." />;
  }

  if (error) {
    return <EmptyState title="No fue posible cargar el microcurrículum" body={error} />;
  }

  const microcurriculumName = program?.rol || program?.nombre_especializacion || programIntelligence?.program_role || 'Microcurrículum en análisis';
  const coveredSkills = program?.skills ?? [];
  const marketDemand =
    ((alignment?.company_demand_score ?? 0) + (alignment?.labor_demand_score ?? 0) + (alignment?.forecasted_demand_score ?? 0)) / 3;
  const gapScore = curriculumRisk?.risk_score ?? programIntelligence?.risk_score ?? Math.max(0, 100 - (alignment?.alignment_score ?? 0));
  const recommendationCount = programIntelligence?.top_recommendations?.length ?? curriculumRisk?.recommended_actions?.length ?? 0;
  const topGaps = (programIntelligence?.top_gaps ?? []).slice(0, 6);

  return (
    <div className="space-y-5">
      <ProgramPageHeader
        programId={programId}
        title={microcurriculumName}
        subtitle="Análisis del microcurrículo que alimenta la brecha académica, la cobertura de skills y la señal de mercado."
        updatedAt={programIntelligence?.generated_at}
        meta={[
          { label: 'Skills cubiertas', value: `${coveredSkills.length}` },
          { label: 'Demanda del mercado', value: `${marketDemand.toFixed(1)}%` },
          { label: 'Gap score', value: `${gapScore.toFixed(1)}%` },
          { label: 'Recomendaciones', value: `${recommendationCount}` },
        ]}
      />

      <ProgramSelectorStrip
        programs={programCatalog}
        selectedProgramId={programId}
        onChange={(nextProgramId) => navigate(`/programs/${nextProgramId}/microcurriculum`)}
        helper="Cambia de programa para comparar uno por uno. La trazabilidad microcurricular detallada real solo está cargada para Visual Analytics and Big Data."
      />

      <ProgramTabs programId={programId} />

      <section className="grid gap-4 xl:grid-cols-3">
        <MetricCard
          label="Cobertura del microcurrículo"
          value={`${coveredSkills.length}`}
          detail="Skills y herramientas presentes en el programa analizado."
          tone="blue"
        />
        <MetricCard
          label="Demanda de mercado"
          value={`${marketDemand.toFixed(1)}%`}
          detail="Promedio de señal laboral, demanda corporativa y forecast."
          tone="green"
        />
        <MetricCard
          label="Brecha del microcurrículo"
          value={`${gapScore.toFixed(1)}%`}
          detail="Riesgo curricular derivado de la señal de mercado y observatorio."
          tone={gapScore >= 75 ? 'rose' : gapScore >= 50 ? 'amber' : 'green'}
        />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Skills cubiertas"
            subtitle="Competencias visibles en el microcurrículo y presentes en el programa actual."
          />
          <div className="flex flex-wrap gap-2">
            {coveredSkills.length ? (
              coveredSkills.map((skill) => (
                <span key={skill.skill_id} className="rounded-full border border-line bg-slate-50 px-3 py-2 text-sm font-semibold text-ink">
                  {skill.nombre}
                  {skill.conteo ? <span className="ml-2 text-muted">· {skill.conteo}</span> : null}
                </span>
              ))
            ) : (
              <EmptyState title="Sin skills cubiertas" body="El programa no expone un listado de skills suficiente para este análisis." />
            )}
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Señal de mercado"
            subtitle="Lectura contextual para explicar por qué el microcurrículo genera brechas o cobertura."
          />
          <div className="space-y-3">
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center justify-between text-sm text-muted">
                <span>Demanda laboral</span>
                <strong className="text-ink">{toNumber(alignment?.labor_demand_score).toFixed(1)}%</strong>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <span className="block h-2 rounded-full bg-brand" style={{ width: `${Math.min(100, toNumber(alignment?.labor_demand_score))}%` }} />
              </div>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center justify-between text-sm text-muted">
                <span>Demanda por compañías</span>
                <strong className="text-ink">{toNumber(alignment?.company_demand_score).toFixed(1)}%</strong>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <span className="block h-2 rounded-full bg-emerald" style={{ width: `${Math.min(100, toNumber(alignment?.company_demand_score))}%` }} />
              </div>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center justify-between text-sm text-muted">
                <span>Forecast de demanda</span>
                <strong className="text-ink">{toNumber(alignment?.forecasted_demand_score).toFixed(1)}%</strong>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <span className="block h-2 rounded-full bg-amber" style={{ width: `${Math.min(100, toNumber(alignment?.forecasted_demand_score))}%` }} />
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="panel space-y-4">
        <SectionTitle
          title="Brechas asociadas"
          subtitle="Las brechas vinculadas al microcurrículo muestran qué contenidos deberían revisarse primero."
        />
        <div className="grid gap-3 md:grid-cols-2">
          {topGaps.length ? (
            topGaps.map((gap, index) => {
              const record = gap as Record<string, unknown>;
              const skill = skillLabel(record.skill ?? record.missing_skill ?? record.canonical_skill ?? `Gap ${index + 1}`);
              const recommendation = String(record.recommendation ?? record.recommendation_reasoning ?? 'Revisión curricular prioritaria.').trim();
              const urgency = toNumber(record.urgency_score ?? record.confidence_score);

              return (
                <article key={`${skill}-${index}`} className="rounded-lg border border-line bg-white px-4 py-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Gap {index + 1}</span>
                      <strong className="mt-1 block text-sm font900 text-ink">{skill}</strong>
                    </div>
                    <span className="rounded-full border border-brand/15 bg-brand/5 px-3 py-1 text-xs font-semibold text-brand">
                      Urgencia {urgency.toFixed(1)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted">{recommendation}</p>
                </article>
              );
            })
          ) : (
            <EmptyState title="Sin brechas visibles" body="No se encontraron brechas priorizadas para este microcurrículo con la evidencia disponible." />
          )}
        </div>
      </section>

      <ExecutiveAiSection
        title="Microcurrículo trazable"
        subtitle="La explicación AI conecta el programa con el microcurrículo, las brechas y la demanda de mercado detectada."
        body={
          programSummary?.microcurriculum_traceability
            ? [programSummary.summary, programSummary.why_at_risk].filter(Boolean).join(' ')
            : undefined
        }
        evidenceSources={programSummary?.evidence_sources}
        confidence={programSummary?.confidence}
        model={programSummary?.model}
        loading={executiveAiLoading}
        error={executiveAiError}
        emptyTitle="No fue posible cargar la trazabilidad ejecutiva"
        emptyBody="La explicación del microcurrículo todavía no está disponible, pero el análisis curricular sigue operativo."
        badgeLabel="Microcurrículo AI"
      />

      <section className="rounded-lg border border-line bg-white px-4 py-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-base font900 text-ink">Interpretación ejecutiva</h3>
            <p className="mt-1 text-sm leading-6 text-muted">
              Este microcurrículo muestra qué contenidos ya están cubiertos, cuáles tienen presión del mercado y qué
              decisiones deberían revisarse en comité académico.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-line bg-slate-50 px-3 py-2 text-sm font-semibold text-muted">
            <Layers3 size={15} strokeWidth={1.9} />
            {coveredSkills.length} skills visibles
          </div>
        </div>
      </section>
    </div>
  );
}
