import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FlaskConical, Plus } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import {
  ForecastHorizonCard,
  MetricCard,
  ProgramPageHeader,
  ProgramSelectorStrip,
  ProgramTabs,
  SectionTitle,
  SkillRail,
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

function normalizeSkill(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function evidenceTablesLabel(value: unknown, fallback: string[]) {
  if (Array.isArray(value)) {
    const items = value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
    if (items.length) return items.join(', ');
  }
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }
  return fallback.join(', ') || 'Sin tablas adicionales';
}

export function ProgramSimulationPage() {
  const { programId: programIdParam } = useParams();
  const navigate = useNavigate();
  const programId = programIdFromParam(programIdParam);
  const { programs: programCatalog } = useProgramCatalog();
  const { program, programIntelligence, curriculumRisk, alignment, isLoading, error, suggestedSkills } = useProgramIntelligenceData(programId);
  const { observatoryAnswer, runQuery, isLoading: executiveAiLoading, error: executiveAiError } = useExecutiveAi(programId);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [draftSkill, setDraftSkill] = useState('');

  useEffect(() => {
    if (!selectedSkills.length && suggestedSkills.length) {
      setSelectedSkills(suggestedSkills.slice(0, 4));
    }
  }, [selectedSkills.length, suggestedSkills]);

  const proposedSkills = useMemo(() => selectedSkills, [selectedSkills]);
  const { simulations, isLoading: simulationsLoading, error: simulationsError } = useProgramSimulations(programId, proposedSkills, [6, 12, 24]);
  const currentSimulation = simulations[12];

  useEffect(() => {
    if (!programId || !selectedSkills.length) {
      return;
    }
    const question = `¿Qué ocurre si actualizamos el currículo con ${selectedSkills.slice(0, 4).join(', ')}?`;
    void runQuery(question, {
      selected_skills: selectedSkills,
      current_alignment: currentSimulation?.current_alignment_score,
      projected_alignment: currentSimulation?.projected_alignment_score,
      projected_risk: currentSimulation?.projected_risk_score,
      projected_employability: currentSimulation?.projected_employability_gain,
    });
  }, [
    currentSimulation?.current_alignment_score,
    currentSimulation?.projected_alignment_score,
    currentSimulation?.projected_employability_gain,
    currentSimulation?.projected_risk_score,
    programId,
    runQuery,
    selectedSkills,
  ]);

  if (!programId) {
    return <EmptyState title="Programa no válido" body="La ruta no contiene un identificador de programa válido." />;
  }

  if (isLoading) {
    return <LoadingState label="Cargando simulación curricular..." />;
  }

  const currentAlignment = alignment?.current_alignment ?? alignment?.alignment_score ?? program?.promedio_match_mercado ?? 0;
  const currentRisk = curriculumRisk?.risk_score ?? programIntelligence?.risk_score ?? Math.max(0, 100 - currentAlignment);
  const currentEmployability = Math.max(0, 100 - currentRisk);
  const defaultSkills = suggestedSkills.length ? suggestedSkills : program?.skills?.map((skill) => skill.nombre) ?? [];

  function toggleSkill(skill: string) {
    setSelectedSkills((current) => {
      const key = normalizeSkill(skill);
      const existing = current.find((item) => normalizeSkill(item) === key);
      if (existing) {
        return current.filter((item) => normalizeSkill(item) !== key);
      }
      return [...current, skill];
    });
  }

  function clearSkills() {
    setSelectedSkills([]);
  }

  function addCustomSkill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = draftSkill.trim();
    if (!value) return;
    toggleSkill(value);
    setDraftSkill('');
  }

  return (
    <div className="space-y-5">
      {error ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          No fue posible cargar toda la inteligencia base del programa. La pantalla continúa con la evidencia disponible.
        </section>
      ) : null}

      <ProgramPageHeader
        programId={programId}
        title={program?.nombre_especializacion || 'Simulación curricular'}
        subtitle="Simulador ejecutivo para estimar el impacto de skills recomendadas sobre alineación, riesgo y empleabilidad."
        updatedAt={currentSimulation?.generated_at}
        meta={[
          { label: 'Alineación base', value: `${currentAlignment.toFixed(1)}%` },
          { label: 'Riesgo base', value: `${currentRisk.toFixed(1)}%` },
          { label: 'Empleabilidad base', value: `${currentEmployability.toFixed(1)}%` },
          { label: 'Skills seleccionadas', value: `${selectedSkills.length}` },
        ]}
      />

      <ProgramSelectorStrip
        programs={programCatalog}
        selectedProgramId={programId}
        onChange={(nextProgramId) => navigate(`/programs/${nextProgramId}/simulation`)}
        helper="Selecciona un programa para simularlo uno a uno. Si el programa no tiene microcurrículo detallado, la simulación se apoya en competencias y skills del programa."
      />

      <ProgramTabs programId={programId} />

      <section className="grid gap-4 xl:grid-cols-3">
        <MetricCard label="Alineación base" value={`${currentAlignment.toFixed(1)}%`} detail="Lectura actual antes de aplicar cambios." tone="blue" />
        <MetricCard label="Riesgo base" value={`${currentRisk.toFixed(1)}%`} detail="Nivel de exposición curricular actual." tone={currentRisk >= 75 ? 'rose' : currentRisk >= 50 ? 'amber' : 'green'} />
        <MetricCard label="Empleabilidad base" value={`${currentEmployability.toFixed(1)}%`} detail="Índice derivado antes de incorporar habilidades nuevas." tone="green" />
      </section>

      <SkillRail
        skills={defaultSkills}
        selectedSkills={selectedSkills}
        onToggle={toggleSkill}
        onClear={clearSkills}
        label="Skills recomendadas para simular"
      />

      <article className="panel space-y-4">
        <SectionTitle
          title="Entrada de simulación"
          subtitle="Agrega skills recomendadas o elimina las que no quieras probar. Los resultados se calculan con el endpoint live del backend."
        />
        <form className="flex flex-col gap-3 md:flex-row" onSubmit={addCustomSkill}>
          <label className="flex-1">
            <span className="mb-2 block text-xs font900 uppercase tracking-[0.12em] text-muted">Skill manual</span>
            <input
              type="text"
              value={draftSkill}
              onChange={(event) => setDraftSkill(event.target.value)}
              placeholder="Ej. dbt, AWS, GenAI, DataOps"
              className="w-full rounded-lg border border-line bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-muted focus:border-brand"
            />
          </label>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand/90"
          >
            <Plus size={16} strokeWidth={1.9} />
            Agregar skill
          </button>
        </form>
        <div className="flex flex-wrap gap-2">
          {selectedSkills.length ? (
            selectedSkills.map((skill) => (
              <button
                key={skill}
                type="button"
                onClick={() => toggleSkill(skill)}
                className="rounded-full border border-brand/20 bg-brand/5 px-3 py-2 text-sm font-semibold text-brand"
              >
                {skill}
              </button>
            ))
          ) : (
            <span className="text-sm text-muted">Selecciona skills para ver la simulación.</span>
          )}
        </div>
      </article>

      {simulationsError ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          No se pudo calcular toda la simulación en este momento. Se muestran estados de respaldo con la información disponible.
        </section>
      ) : null}
      {simulationsLoading && <LoadingState label="Calculando impacto curricular..." />}

      {!simulationsLoading && !simulationsError && (
        <>
          <section className="grid gap-4 xl:grid-cols-3">
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
          </section>

          <section className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
            <article className="panel space-y-4">
              <SectionTitle
                title="Interpretación de impacto"
                subtitle="La simulación se calcula desde brechas, recomendaciones y forecast productivo, no desde supuestos manuales."
              />
              {currentSimulation ? (
                <div className="space-y-3">
                  <div className="rounded-lg border border-line bg-slate-50 p-4">
                    <div className="flex items-center justify-between text-sm text-muted">
                      <span>Brecha cubierta</span>
                      <strong className="text-ink">{currentSimulation.projected_gap_reduction.toFixed(1)}%</strong>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-slate-100">
                      <span className="block h-2 rounded-full bg-brand" style={{ width: `${Math.min(100, currentSimulation.projected_gap_reduction)}%` }} />
                    </div>
                  </div>
                  <p className="text-sm leading-7 text-ink">{currentSimulation.explanation}</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg border border-line bg-slate-50 p-4">
                      <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Evidencia</span>
                      <p className="mt-2 text-sm leading-6 text-muted">
                        {evidenceTablesLabel((currentSimulation.supporting_evidence as Record<string, unknown> | undefined)?.source_tables, currentSimulation.source_tables)}
                      </p>
                    </div>
                    <div className="rounded-lg border border-line bg-slate-50 p-4">
                      <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Confianza</span>
                      <p className="mt-2 text-sm leading-6 text-muted">{currentSimulation.confidence_score.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState title="Sin simulación" body="Selecciona skills para obtener una proyección real del programa." />
              )}
            </article>

            <article className="panel space-y-4">
              <SectionTitle
                title="Resumen académico"
                subtitle="Lectura de programa para comités y directores académicos."
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-line bg-slate-50 p-4">
                  <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Programa</span>
                  <strong className="mt-2 block text-sm font900 text-ink">{program?.nombre_especializacion || 'Programa en análisis'}</strong>
                </div>
                <div className="rounded-lg border border-line bg-slate-50 p-4">
                  <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Rol</span>
                  <strong className="mt-2 block text-sm font900 text-ink">{program?.rol || programIntelligence?.program_role || 'Sin rol definido'}</strong>
                </div>
                <div className="rounded-lg border border-line bg-slate-50 p-4">
                  <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Skills seleccionadas</span>
                  <strong className="mt-2 block text-sm font900 text-ink">{selectedSkills.length}</strong>
                </div>
                <div className="rounded-lg border border-line bg-slate-50 p-4">
                  <span className="block text-[0.72rem] font900 uppercase tracking-[0.12em] text-muted">Horizontes</span>
                  <strong className="mt-2 block text-sm font900 text-ink">6 / 12 / 24 meses</strong>
                </div>
              </div>
            </article>
          </section>

      <ExecutiveAiSection
        title="Simulación explicada por IA"
        subtitle="La explicación conecta las skills seleccionadas con la evidencia curricular y el impacto proyectado."
        body={
          selectedSkills.length
            ? observatoryAnswer?.answer
            : 'Simulación pendiente de datos suficientes. Selecciona skills para calcular impacto.'
        }
        evidenceSources={selectedSkills.length ? observatoryAnswer?.evidence_sources : []}
        confidence={selectedSkills.length ? observatoryAnswer?.confidence : null}
        model={selectedSkills.length ? observatoryAnswer?.model : 'deterministic-fallback'}
        loading={executiveAiLoading && selectedSkills.length > 0}
        error={selectedSkills.length ? executiveAiError : null}
        emptyTitle="No fue posible generar la explicación de simulación"
        emptyBody="La explicación ejecutiva todavía no está disponible, pero la simulación numérica sigue operativa."
        badgeLabel="Simulation AI"
      />

          <section className="rounded-lg border border-line bg-white px-4 py-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-ink">
              <FlaskConical size={16} strokeWidth={1.9} className="text-brand" />
              La simulación opera sobre datos productivos y se persiste en `curriculum_simulations`.
            </div>
          </section>
        </>
      )}
    </div>
  );
}
