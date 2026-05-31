import { Link, useParams } from 'react-router-dom';
import { ArrowRight, BarChart3 } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import {
  ForecastHorizonCard,
  MetricCard,
  NarrativePanel,
  ProgramPageHeader,
  ProgramTabs,
  SectionTitle,
} from '../components/program-intelligence/ProgramIntelligenceBlocks';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useProgramIntelligenceData, useProgramSimulations } from '../hooks/useProgramIntelligenceData';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getText(value: unknown, fallback = 'Sin información suficiente') {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function toTextList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => toTextList(item));
  }
  if (typeof value === 'string') {
    return value.trim() ? [value.trim()] : [];
  }
  if (!value || typeof value !== 'object') return [];
  const record = value as Record<string, unknown>;
  const candidates: unknown[] = [
    record.skill,
    record.missing_skill,
    record.canonical_skill,
    record.name,
    record.title,
    record.recommendation_reasoning,
    record.recommendation,
  ];
  if (Array.isArray(record.evidence)) candidates.push(...record.evidence);
  if (Array.isArray(record.recommended_skills)) candidates.push(...record.recommended_skills);
  if (Array.isArray(record.top_skills)) candidates.push(...record.top_skills);
  return candidates.flatMap((candidate) => toTextList(candidate));
}

function firstText(value: unknown, fallback = 'Sin información suficiente') {
  const items = toTextList(value);
  return items[0] ?? fallback;
}

function recommendationSkills(value: unknown) {
  if (!value || typeof value !== 'object') return [];
  const record = value as Record<string, unknown>;
  const candidates: unknown[] = [
    record.skill,
    record.missing_skill,
    record.canonical_skill,
    record.canonical_skill_name,
    record.recommended_skill,
  ];
  const payload = record.recommendation_payload && typeof record.recommendation_payload === 'object' ? (record.recommendation_payload as Record<string, unknown>) : null;
  if (payload?.recommended_skills) {
    candidates.push(payload.recommended_skills);
  }
  if (Array.isArray(record.recommended_skills)) {
    candidates.push(record.recommended_skills);
  }
  return candidates.flatMap((candidate) => toTextList(candidate));
}

function programIdFromParam(value?: string) {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function ProgramIntelligenceDetailPage() {
  const { programId: programIdParam } = useParams();
  const programId = programIdFromParam(programIdParam);
  const { program, programIntelligence, curriculumRisk, alignment, forecastSummary, executiveObservatory, isLoading, error, suggestedSkills } =
    useProgramIntelligenceData(programId);
  const { programSummary, executiveNarrative, isLoading: executiveAiLoading, error: executiveAiError } = useExecutiveAi(programId);
  const selectedSkills = suggestedSkills.slice(0, 5);
  const { simulations, isLoading: simulationsLoading, error: simulationsError } = useProgramSimulations(programId, selectedSkills, [6, 12, 24]);

  if (!programId) {
    return <EmptyState title="Programa no válido" body="La ruta no contiene un identificador de programa válido." />;
  }

  if (isLoading) {
    return <LoadingState label="Cargando inteligencia del programa..." />;
  }

  if (error) {
    return <EmptyState title="No fue posible cargar el programa" body={error} />;
  }

  const currentAlignment =
    alignment?.current_alignment ?? alignment?.alignment_score ?? programIntelligence?.alignment_score ?? program?.promedio_match_mercado ?? 0;
  const riskScore = curriculumRisk?.risk_score ?? programIntelligence?.risk_score ?? Math.max(0, 100 - currentAlignment);
  const employabilityIndex = Math.max(0, 100 - riskScore);
  const topGaps = (programIntelligence?.top_gaps ?? []).slice(0, 5);
  const topRecommendations = (programIntelligence?.top_recommendations ?? []).slice(0, 5);
  const narrative =
    alignment?.explanation ||
    programIntelligence?.business_justification ||
    executiveObservatory?.executive_narrative ||
    'La inteligencia del programa se genera con señales reales de mercado, brechas curriculares y evidencia de observatorio.';
  const updatedAt = programIntelligence?.generated_at || executiveObservatory?.metrics?.[0]?.metric_period || 'Datos vivos';

  return (
    <div className="space-y-5">
      <ProgramPageHeader
        programId={programId}
        title={program?.nombre_especializacion || programIntelligence?.program_name || 'Programa en análisis'}
        subtitle={`Lectura ejecutiva del programa ${program?.rol || programIntelligence?.program_role || 'académico'} con riesgo, alineación, forecast y simulación de impacto.`}
        updatedAt={updatedAt}
        meta={[
          { label: 'Alineación actual', value: `${currentAlignment.toFixed(1)}%` },
          { label: 'Riesgo curricular', value: `${riskScore.toFixed(1)}%` },
          { label: 'Empleabilidad derivada', value: `${employabilityIndex.toFixed(1)}%` },
          { label: 'Brechas activas', value: `${programIntelligence?.gap_count ?? topGaps.length}` },
        ]}
      />

      <ProgramTabs programId={programId} />

      <NarrativePanel
        title="Lectura institucional"
        narrative={narrative}
        evidence={[
          ...(curriculumRisk?.risk_drivers?.map((driver) => `${driver.driver}: ${driver.value.toFixed(2)}`) ?? []),
          ...(alignment?.missing_skills ?? []).slice(0, 3),
          ...(forecastSummary?.top_skills ?? []).slice(0, 2).map((item) => item.entity_name),
        ].filter(Boolean)}
      />

      <section className="grid gap-4 xl:grid-cols-3">
        <MetricCard
          label="Alineación curricular"
          value={`${currentAlignment.toFixed(1)}%`}
          detail={alignment?.explanation || 'Alineación calculada desde señales curriculares y laborales reales.'}
          tone="blue"
        />
        <MetricCard
          label="Riesgo curricular"
          value={`${riskScore.toFixed(1)}%`}
          detail={curriculumRisk?.risk_level ? `Nivel ${curriculumRisk.risk_level}` : 'Riesgo estimado desde el observatorio.'}
          tone={riskScore >= 75 ? 'rose' : riskScore >= 50 ? 'amber' : 'green'}
        />
        <MetricCard
          label="Índice de empleabilidad"
          value={`${employabilityIndex.toFixed(1)}%`}
          detail="Índice derivado de la señal de riesgo para soportar decisiones académicas."
          tone="green"
        />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.3fr_0.9fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Top gaps"
            subtitle="Las brechas se extraen del observatorio de programa y conservan la evidencia de mercado asociada."
          />
          <div className="space-y-3">
            {topGaps.length ? (
              topGaps.map((gap, index) => {
                const record = gap as Record<string, unknown>;
                const skill = firstText(record.skill ?? record.missing_skill ?? record.canonical_skill ?? record.name, 'Brecha no tipificada');
                const cluster = firstText(record.cluster_name ?? record.occupational_cluster ?? record.cluster, 'Cluster no definido');
                const status = getText(record.coverage_status, 'gap');
                const recommendation = getText(record.recommendation || record.recommendation_reasoning, 'Sin recomendación explícita.');
                const demand = toNumber(record.evidence_weight ?? record.market_demand_score ?? record.market_weight);
                const urgency = toNumber(record.urgency_score ?? record.confidence_score);

                return (
                  <div key={`${skill}-${index}`} className="rounded-lg border border-line bg-slate-50 px-4 py-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <strong className="text-sm font900 text-ink">{skill}</strong>
                          <span className="rounded-full border border-brand/15 bg-brand/5 px-2.5 py-1 text-[0.72rem] font900 uppercase tracking-[0.12em] text-brand">
                            {status}
                          </span>
                        </div>
                        <p className="text-sm text-muted">{cluster}</p>
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2 text-xs font-semibold text-muted">
                        <span className="rounded-full border border-line bg-white px-3 py-1">Demanda {demand.toFixed(1)}</span>
                        <span className="rounded-full border border-line bg-white px-3 py-1">Urgencia {urgency.toFixed(1)}</span>
                      </div>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-ink">{recommendation}</p>
                  </div>
                );
              })
            ) : (
              <EmptyState title="Sin brechas visibles" body="No se encontraron gaps priorizados para este programa con la evidencia disponible." />
            )}
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Top recomendaciones"
            subtitle="Acciones académicas priorizadas con trazabilidad hacia el mercado y el observatorio."
          />
          <div className="space-y-3">
            {topRecommendations.length ? (
              topRecommendations.map((recommendation, index) => {
                const record = recommendation as Record<string, unknown>;
                const title = firstText(record.target_role ?? record.target_entity ?? record.recommendation_type, `Recomendación ${index + 1}`);
                const skills = recommendationSkills(record).slice(0, 3);
                const reasoning = getText(record.recommendation_reasoning ?? record.business_justification, 'Recomendación basada en señales reales del mercado.');
                const confidence = toNumber(record.recommendation_confidence ?? record.confidence);
                const impact = toNumber(record.estimated_alignment_increase ?? record.recommendation_score ?? record.market_alignment_score);

                return (
                  <div key={`${title}-${index}`} className="rounded-lg border border-line bg-white px-4 py-4 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">
                          {getText(record.recommendation_type, 'recommendation')}
                        </span>
                        <strong className="mt-1 block text-sm font900 text-ink">{title}</strong>
                      </div>
                      <span className="rounded-full border border-brand/15 bg-brand/5 px-3 py-1 text-xs font-semibold text-brand">
                        Impacto {impact.toFixed(1)}%
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-muted">{reasoning}</p>
                    {skills.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {skills.map((skill) => (
                          <span key={skill} className="rounded-full border border-line bg-slate-50 px-2.5 py-1 text-xs font-semibold text-ink">
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="mt-3 text-xs font-semibold text-muted">Confianza {confidence.toFixed(2)}</div>
                  </div>
                );
              })
            ) : (
              <EmptyState title="Sin recomendaciones" body="No hay recomendaciones priorizadas para este programa con la evidencia disponible." />
            )}
          </div>
        </article>
      </section>

      <section className="panel space-y-5">
        <SectionTitle
          title="Forecast 6/12/24 meses"
          subtitle="Proyección por horizonte con el mismo programa y el conjunto de skills priorizadas derivadas del observatorio."
        />
        {simulationsError && <EmptyState title="No se pudo calcular el forecast" body={simulationsError} />}
        {simulationsLoading && <LoadingState label="Calculando proyecciones del programa..." />}
        {!simulationsLoading && !simulationsError && (
          <div className="grid gap-4 xl:grid-cols-3">
            {[6, 12, 24].map((horizon) => {
              const simulation = simulations[horizon];
              return simulation ? (
                <ForecastHorizonCard
                  key={horizon}
                  horizon={horizon}
                  currentAlignment={simulation.current_alignment_score}
                  projectedAlignment={simulation.projected_alignment_score}
                  projectedRisk={simulation.projected_risk_score}
                  projectedEmployability={simulation.projected_employability_gain}
                  projectedGapReduction={simulation.projected_gap_reduction}
                  explanation={simulation.explanation}
                />
              ) : (
                <div key={horizon} className="panel">
                  <p className="text-sm text-muted">Sin simulación disponible para {horizon} meses.</p>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Señales de mercado"
            subtitle="Contexto adicional desde el forecast summary para explicar el programa sin salir de datos productivos."
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Skills top</span>
              <ul className="mt-3 space-y-2">
                {(forecastSummary?.top_skills ?? []).slice(0, 4).map((item) => (
                  <li key={`${item.entity_name}-${item.horizon_months}`} className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-ink">{item.entity_name}</span>
                    <span className="text-muted">{(item.growth_velocity * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Tecnologías</span>
              <ul className="mt-3 space-y-2">
                {(forecastSummary?.top_technologies ?? []).slice(0, 4).map((item) => (
                  <li key={`${item.entity_name}-${item.horizon_months}`} className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-ink">{item.entity_name}</span>
                    <span className="text-muted">{(item.growth_velocity * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Navegación ejecutiva"
            subtitle="Accesos rápidos a las demás capas del programa."
          />
          <div className="grid gap-3">
            <Link className="flex items-center justify-between rounded-lg border border-line bg-slate-50 px-4 py-3 transition hover:border-brand/40 hover:bg-brand/5" to={`/programs/${programId}/microcurriculum`}>
              <div>
                <strong className="block text-sm font900 text-ink">Microcurriculum</strong>
                <span className="block text-sm text-muted">Cobertura, demanda y brechas por microcurrículo.</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.9} className="text-brand" />
            </Link>
            <Link className="flex items-center justify-between rounded-lg border border-line bg-slate-50 px-4 py-3 transition hover:border-brand/40 hover:bg-brand/5" to={`/programs/${programId}/forecast`}>
              <div>
                <strong className="block text-sm font900 text-ink">Forecast</strong>
                <span className="block text-sm text-muted">Proyección 6/12/24 meses y señales del mercado.</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.9} className="text-brand" />
            </Link>
            <Link className="flex items-center justify-between rounded-lg border border-line bg-slate-50 px-4 py-3 transition hover:border-brand/40 hover:bg-brand/5" to={`/programs/${programId}/simulation`}>
              <div>
                <strong className="block text-sm font900 text-ink">Simulación</strong>
                <span className="block text-sm text-muted">Prueba el impacto de skills recomendadas.</span>
              </div>
              <ArrowRight size={16} strokeWidth={1.9} className="text-brand" />
            </Link>
          </div>
        </article>
      </section>

      <section className="rounded-lg border border-line bg-white px-4 py-3 text-sm text-muted">
        <div className="flex flex-wrap items-center gap-3">
          <BarChart3 size={16} strokeWidth={1.9} className="text-brand" />
          <span>
            Programa analizado con datos vivos de programas, gap observatory, recommendations, market forecasts y curriculum simulator.
          </span>
        </div>
      </section>

      <ExecutiveAiSection
        title="Estado institucional explicado"
        subtitle="Narrativa ejecutiva construida desde program intelligence, microcurriculum, gaps, recomendaciones y forecast productivo."
        body={
          [
            executiveNarrative?.narrative || programSummary?.summary,
            executiveNarrative?.why_at_risk || programSummary?.why_at_risk,
          ]
            .filter(Boolean)
            .join(' ')
        }
        evidenceSources={executiveNarrative?.evidence_sources || programSummary?.evidence_sources}
        confidence={executiveNarrative?.confidence || programSummary?.confidence}
        loading={executiveAiLoading}
        error={executiveAiError}
        emptyTitle="No fue posible cargar la explicación ejecutiva"
        emptyBody="La narrativa ejecutiva todavía no está disponible, pero el análisis del programa sigue operativo."
        badgeLabel="Narrativa AI"
      />
    </div>
  );
}
