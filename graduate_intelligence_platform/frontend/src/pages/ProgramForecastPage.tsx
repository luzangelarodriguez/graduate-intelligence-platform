import { useNavigate, useParams } from 'react-router-dom';
import { Activity, CalendarRange, Building2, Sparkles } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import {
  ForecastHorizonCard,
  MetricCard,
  ProgramPageHeader,
  ProgramSelectorStrip,
  ProgramTabs,
  SectionTitle,
  getProgramDomainContext,
} from '../components/program-intelligence/ProgramIntelligenceBlocks';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useProgramCatalog } from '../hooks/useProgramCatalog';
import { useProgramIntelligenceData, useProgramSimulations } from '../hooks/useProgramIntelligenceData';

function programIdFromParam(value?: string) {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function ProgramForecastPage() {
  const { programId: programIdParam } = useParams();
  const navigate = useNavigate();
  const programId = programIdFromParam(programIdParam);
  const { programs: programCatalog } = useProgramCatalog();
  const { program, programIntelligence, alignment, forecastSummary, criticalPrograms, isLoading, error, suggestedSkills } = useProgramIntelligenceData(programId);
  const { executiveNarrative, isLoading: executiveAiLoading, error: executiveAiError } = useExecutiveAi(programId);
  const selectedSkills = suggestedSkills.slice(0, 6);
  const { simulations, isLoading: simulationsLoading, error: simulationsError } = useProgramSimulations(programId, selectedSkills, [6, 12, 24]);
  const resolvedProgram = program ?? programCatalog.find((item) => item.especializacion_id === programId);
  const domainContext = getProgramDomainContext(programIntelligence);

  if (!programId) {
    return <EmptyState title="Programa no válido" body="La ruta no contiene un identificador de programa válido." />;
  }

  if (isLoading) {
    return <LoadingState label="Cargando forecast del programa..." />;
  }

  const currentAlignment = alignment?.current_alignment ?? alignment?.alignment_score ?? program?.promedio_match_mercado ?? 0;
  const currentRisk = simulations[12]?.current_risk_score ?? Math.max(0, 100 - currentAlignment);
  const currentEmployability = Math.max(0, 100 - currentRisk);
  const forecastSignals = (programIntelligence?.forecast_signals ?? []).filter((signal) => {
    const record = signal as Record<string, unknown>;
    return String(record.entity_type || '').toLowerCase() === 'skill';
  });
  const roleSignals = programIntelligence?.role_signals ?? [];
  const benchmarkEvidence = (programIntelligence?.supporting_evidence as Record<string, unknown> | undefined)?.domain_benchmark as
    | Record<string, unknown>
    | undefined;
  const benchmarkInstitutions = Array.isArray(benchmarkEvidence?.benchmark_institutions)
    ? benchmarkEvidence?.benchmark_institutions.slice(0, 4)
    : [];

  return (
    <div className="space-y-5">
      <ProgramPageHeader
        programId={programId}
        title={program?.nombre_especializacion || 'Forecast académico'}
        subtitle="Proyección ejecutiva de alineación, riesgo y empleabilidad para orientar decisiones curriculares."
        updatedAt={forecastSummary?.generated_at}
        meta={[
          { label: 'Alineación actual', value: `${currentAlignment.toFixed(1)}%` },
          { label: 'Riesgo actual', value: `${currentRisk.toFixed(1)}%` },
          { label: 'Empleabilidad actual', value: `${currentEmployability.toFixed(1)}%` },
          { label: 'Horizontes', value: '6 / 12 / 24 meses' },
        ]}
      />

      <ProgramSelectorStrip
        programs={programCatalog}
        selectedProgramId={programId}
        onChange={(nextProgramId) => navigate(`/programs/${nextProgramId}/forecast`)}
        domainLabel={domainContext.domainLabel}
        subdomainLabel={domainContext.subdomainLabel}
        benchmarkLabel={domainContext.benchmarkLabel}
        helper="Selecciona un programa para comparar horizontes 6/12/24 meses. El análisis de microcurrículo real sigue concentrado en Visual Analytics and Big Data."
      />

      <ProgramTabs programId={programId} />

      {error ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
          {error}. La vista sigue mostrando la evidencia disponible para no cortar el an?lisis ejecutivo.
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-3">
        <MetricCard
          label="Alineación actual"
          value={`${currentAlignment.toFixed(1)}%`}
          detail="Lectura base del programa sobre la evidencia viva del observatorio."
          tone="blue"
        />
        <MetricCard
          label="Riesgo base"
          value={`${currentRisk.toFixed(1)}%`}
          detail="Punto de partida para comparar los escenarios de actualización."
          tone={currentRisk >= 75 ? 'rose' : currentRisk >= 50 ? 'amber' : 'green'}
        />
        <MetricCard
          label="Empleabilidad base"
          value={`${currentEmployability.toFixed(1)}%`}
          detail="Índice derivado para lectura ejecutiva de impacto laboral."
          tone="green"
        />
      </section>

      <ExecutiveAiSection
        title="Lectura ejecutiva del forecast"
        subtitle="La explicación AI resume por qué la proyección cambia en 6, 12 y 24 meses y qué señales activan el riesgo."
        body={[executiveNarrative?.narrative, executiveNarrative?.why_at_risk].filter(Boolean).join(' ')}
        evidenceSources={executiveNarrative?.evidence_sources}
        confidence={executiveNarrative?.confidence}
        model={executiveNarrative?.model}
        loading={executiveAiLoading}
        error={executiveAiError}
        emptyTitle="No fue posible cargar la lectura ejecutiva"
        emptyBody="La narrativa del forecast todavía no está disponible, pero las proyecciones siguen operativas."
        badgeLabel="Forecast AI"
      />

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.95fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Forecast por horizonte"
            subtitle="Misma evidencia del programa proyectada en 6, 12 y 24 meses."
          />
          {simulationsError && <EmptyState title="No se pudo calcular el forecast" body={simulationsError} />}
          {simulationsLoading && <LoadingState label="Calculando proyecciones..." />}
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
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Se?ales del mercado"
            subtitle="Se?ales del programa y del benchmark disciplinar. No se mezclan se?ales gen?ricas de otras ?reas."
          />
          <div className="space-y-3">
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Skills emergentes</span>
              <ul className="mt-3 space-y-2">
                {forecastSignals.length ? (
                  forecastSignals.slice(0, 4).map((item, index) => {
                    const record = item as Record<string, unknown>;
                    const name = String(record.entity_name || 'Skill').trim();
                    const growth = Number(record.growth_velocity || 0);
                    const horizon = Number(record.horizon_months || 0);
                    return (
                      <li key={`${name}-${horizon}-${index}`} className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-ink">{name}</span>
                        <span className="text-muted">{(growth * 100).toFixed(1)}%</span>
                      </li>
                    );
                  })
                ) : (
                  <li className="text-sm text-muted">No hay skills emergentes espec?ficas para este programa.</li>
                )}
              </ul>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Roles de mercado</span>
              <ul className="mt-3 space-y-2">
                {roleSignals.length ? (
                  roleSignals.slice(0, 4).map((item, index) => {
                    const record = item as Record<string, unknown>;
                    const sourceRole = String(record.source_role || record.target_role || record.role || 'Role').trim();
                    const probability = Number(record.transition_probability || record.similarity_score || 0);
                    return (
                      <li key={`${sourceRole}-${probability}-${index}`} className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-ink">{sourceRole}</span>
                        <span className="text-muted">{(probability * 100).toFixed(1)}%</span>
                      </li>
                    );
                  })
                ) : (
                  <li className="text-sm text-muted">No hay roles de mercado espec?ficos suficientes para este programa.</li>
                )}
              </ul>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Benchmarks institucionales</span>
              <ul className="mt-3 space-y-2">
                {benchmarkInstitutions.length ? (
                  benchmarkInstitutions.map((item, index) => {
                    const record = item as Record<string, unknown>;
                    const institution = String(record.institution || record.program || 'Instituci?n').trim();
                    const programName = String(record.program || '').trim();
                    return (
                      <li key={`${institution}-${index}`} className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-ink">{institution}</span>
                        <span className="text-muted">{programName || 'Benchmark'}</span>
                      </li>
                    );
                  })
                ) : (
                  <li className="text-sm text-muted">No hay benchmark institucional adicional para este programa.</li>
                )}
              </ul>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Empresas observadas</span>
              <p className="mt-3 text-sm leading-6 text-muted">
                Para Criminolog?a la se?al laboral se concentra en roles y competencias. No se mezclan aqu? stacks globales de analytics.
              </p>
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Programas en riesgo"
            subtitle="Contexto institucional para evaluar si el programa se está acercando a un umbral crítico."
          />
          <div className="grid gap-3">
            {(criticalPrograms ?? []).slice(0, 6).map((item) => (
              <div key={`${item.program_id}-${item.horizon_months}`} className="rounded-lg border border-line bg-white px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <strong className="block text-sm font900 text-ink">{item.program_name || `Programa ${item.program_id}`}</strong>
                    <span className="block text-sm text-muted">{item.main_gap_driver || item.recommended_action || 'Sin driver principal definido'}</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-xs font900 uppercase tracking-[0.12em] text-muted">{item.risk_level}</span>
                    <strong className="block text-sm text-ink">{toNumber(item.risk_score).toFixed(1)}%</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Contexto del forecast"
            subtitle="La proyección nace de la misma evidencia que alimenta la simulación curricular."
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <CalendarRange size={16} strokeWidth={1.9} className="text-brand" />
                Horizonte activo
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">Las simulaciones se calculan sobre los horizontes 6, 12 y 24 meses.</p>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Activity size={16} strokeWidth={1.9} className="text-brand" />
                Señal compuesta
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">La tendencia integra gap observatory, program intelligence y market forecasts.</p>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Building2 size={16} strokeWidth={1.9} className="text-brand" />
                Demanda de compañías
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">El comportamiento de empresas aparece en el forecast y en company intelligence.</p>
            </div>
            <div className="rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Sparkles size={16} strokeWidth={1.9} className="text-brand" />
                Impacto esperado
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">La alineación proyectada es la base para el ajuste del plan académico.</p>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
