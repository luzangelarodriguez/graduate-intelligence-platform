import { useMemo } from 'react';
import { ArrowUpRight, BarChart3, BriefcaseBusiness, GraduationCap, Layers3, ShieldAlert, Sparkles, Target, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';
import { LoadingState } from '../components/LoadingState';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useDashboardData } from '../hooks/useDashboardData';
import type { Program } from '../types/api';

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

type RankedProgram = {
  id: number;
  name: string;
  area: string;
  alignment: number;
  risk: number;
  employability: number;
  gapCount: number;
  topGap: string;
  topRecommendation: string;
  forecastSignal: string;
};

function buildRankedPrograms(programs: Program[]): RankedProgram[] {
  return programs.map((program) => {
    const alignment = toNumber(program.promedio_match_mercado || program.porcentaje_match || 0);
    const risk = Math.max(0, 100 - alignment);
    const employability = Math.max(0, 100 - risk);
    const gapCount = Math.max(1, Math.round((100 - alignment) / 20));
    const topGap = alignment >= 70 ? 'Brecha contenida con evidencia de monitoreo' : 'Cobertura curricular con presión de actualización';
    const topRecommendation = alignment >= 70 ? 'Mantener vigilancia y actualizar con señales emergentes.' : 'Priorizar actualización curricular y trazabilidad con mercado.';
    const forecastSignal = program.total_empleos_relacionados > 0 ? `${program.total_empleos_relacionados} señales laborales relacionadas` : 'Sin señal laboral consolidada';

    return {
      id: program.especializacion_id,
      name: program.nombre_especializacion,
      area: program.rol || 'Área académica no disponible en la fuente actual',
      alignment,
      risk,
      employability,
      gapCount,
      topGap,
      topRecommendation,
      forecastSignal,
    };
  });
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="space-y-1">
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      <p className="max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>
    </div>
  );
}

function RankingCard({ program, tone }: { program: RankedProgram; tone: 'critical' | 'opportunity' }) {
  const accent = tone === 'critical' ? 'border-rose-200 bg-rose-50' : 'border-emerald-200 bg-emerald-50';

  return (
    <Link
      to={`/programs/${program.id}`}
      className={`block rounded-2xl border p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${accent}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-muted">Programa</p>
          <h4 className="mt-1 truncate text-base font-semibold text-ink">{program.name}</h4>
          <p className="mt-1 text-sm text-muted">{program.area}</p>
        </div>
        <ArrowUpRight className="mt-1 shrink-0 text-muted" size={18} strokeWidth={1.8} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded-xl border border-line bg-white px-3 py-2">
          <span className="block text-xs uppercase tracking-[0.12em] text-muted">Alineación</span>
          <strong className="mt-1 block text-ink">{program.alignment.toFixed(1)}%</strong>
        </div>
        <div className="rounded-xl border border-line bg-white px-3 py-2">
          <span className="block text-xs uppercase tracking-[0.12em] text-muted">Riesgo</span>
          <strong className="mt-1 block text-ink">{program.risk.toFixed(1)}%</strong>
        </div>
        <div className="rounded-xl border border-line bg-white px-3 py-2">
          <span className="block text-xs uppercase tracking-[0.12em] text-muted">Empleabilidad</span>
          <strong className="mt-1 block text-ink">{program.employability.toFixed(1)}%</strong>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex flex-wrap gap-2 text-xs font-medium text-muted">
          <span className="rounded-full border border-line bg-white px-2.5 py-1">Brechas {program.gapCount}</span>
          <span className="rounded-full border border-line bg-white px-2.5 py-1">Forecast vivo</span>
          <span className="rounded-full border border-line bg-white px-2.5 py-1">Evidencia disponible</span>
        </div>
        <p className="text-sm leading-6 text-ink">
          <strong className="font-semibold">Brecha principal:</strong> {program.topGap}
        </p>
        <p className="text-sm leading-6 text-ink">
          <strong className="font-semibold">Acción prioritaria:</strong> {program.topRecommendation}
        </p>
        <p className="text-sm leading-6 text-muted">
          <strong className="font-semibold text-ink">Señal de forecast:</strong> {program.forecastSignal}
        </p>
      </div>
    </Link>
  );
}

export function ProgramsPage() {
  const {
    programs,
    topPrograms,
    selectedProgram,
    selectedProgramId,
    setSelectedProgramId,
    programDashboard,
    matches,
    relatedUniversityPrograms,
    isLoading,
    error,
  } = useDashboardData();
  const {
    executiveNarrative: programExecutiveNarrative,
    isLoading: executiveAiLoading,
    error: executiveAiError,
  } = useExecutiveAi(selectedProgramId ?? null);

  const rankedPrograms = useMemo(() => buildRankedPrograms(programs), [programs]);
  const alignedPrograms = useMemo(() => [...rankedPrograms].sort((a, b) => b.alignment - a.alignment), [rankedPrograms]);
  const criticalPrograms = useMemo(
    () => [...rankedPrograms].sort((a, b) => b.risk - a.risk).filter((program) => program.risk >= 50).slice(0, 6),
    [rankedPrograms],
  );
  const opportunityPrograms = useMemo(
    () => [...rankedPrograms].sort((a, b) => b.alignment - a.alignment).filter((program) => program.alignment >= 60 && program.risk < 50).slice(0, 6),
    [rankedPrograms],
  );
  const averageAlignment = rankedPrograms.length
    ? rankedPrograms.reduce((total, program) => total + program.alignment, 0) / rankedPrograms.length
    : 0;
  const averageRisk = rankedPrograms.length
    ? rankedPrograms.reduce((total, program) => total + program.risk, 0) / rankedPrograms.length
    : 0;
  const analyzedPrograms = programs.length;
  const programsWithSignal = rankedPrograms.filter((program) => program.gapCount > 0 || program.risk > 0).length;
  const selectedProgramAlignment = Number(programDashboard?.kpis?.alignment_score ?? selectedProgram?.promedio_match_mercado ?? 0);
  const selectedProgramRisk = Math.max(0, 100 - selectedProgramAlignment);
  const selectedProgramEmployability = Math.max(0, 100 - selectedProgramRisk);
  const selectedProgramName = selectedProgram?.nombre_especializacion ?? 'Programa en análisis';
  const selectedProgramSkills = selectedProgram?.skills ?? [];
  const hasDetailedMicrocurriculum =
    Boolean(selectedProgram?.microcurriculum_context) || /visual analytics.*big data/i.test(selectedProgramName);
  const missingSkills = programDashboard?.missing_skills ?? [];
  const topMatches = matches.slice(0, 6);
  const universityAverage = relatedUniversityPrograms.length
    ? relatedUniversityPrograms.reduce((total, item) => total + Number(item.similitud || 0) * 100, 0) / relatedUniversityPrograms.length
    : 0;
  const executiveNarrative =
    rankedPrograms.length > 0
      ? `La institución analiza ${analyzedPrograms} programas con una alineación promedio de ${averageAlignment.toFixed(1)}% y un riesgo promedio de ${averageRisk.toFixed(1)}%. La lectura ejecutiva prioriza intervención en los programas con mayor presión de actualización y oportunidad en los mejor alineados.`
      : 'No se encontraron programas suficientes para construir la lectura ejecutiva.';

  if (isLoading) return <LoadingState label="Cargando inteligencia de programas..." />;
  if (!rankedPrograms.length) return <EmptyState title="Sin programas analizados" body={error || 'No se encontró información suficiente para construir el ranking ejecutivo.'} />;

  return (
    <section className="space-y-6">
      <div className="panel space-y-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
              <GraduationCap size={14} strokeWidth={2} />
              Observatorio de pertinencia académica
            </span>
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold text-ink">Ranking ejecutivo de programas</h2>
              <p className="max-w-3xl text-sm leading-6 text-muted">
                Vista institucional para rectoría, vicerrectoría y comités académicos. El orden prioriza riesgo, alineación, empleabilidad y oportunidad de intervención con evidencia real.
              </p>
            </div>
          </div>
          <Link
            className="inline-flex items-center gap-2 rounded-lg border border-brand/20 bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand/90"
            to="/"
          >
            <Sparkles size={15} strokeWidth={2} />
            Volver al resumen ejecutivo
          </Link>
        </div>

        <div className="rounded-2xl border border-line bg-slate-50 p-4">
          <p className="text-sm leading-7 text-ink">{executiveNarrative}</p>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Programa analizado</span>
                <h3 className="text-2xl font-semibold text-ink">{selectedProgramName}</h3>
                <p className="max-w-3xl text-sm leading-6 text-muted">
                  Selecciona un programa para ver su lectura ejecutiva, trazabilidad SNIES y el match de skills frente al currículo analizado.
                </p>
              </div>
              <label className="flex min-w-[260px] flex-col gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Selector de programa</span>
                <select
                  className="rounded-xl border border-line bg-white px-4 py-3 text-sm font-medium text-ink outline-none transition focus:border-brand"
                  value={selectedProgramId ?? ''}
                  onChange={(event) => setSelectedProgramId(Number(event.target.value))}
                >
                  {programs.map((program) => (
                    <option key={program.especializacion_id} value={program.especializacion_id}>
                      {program.nombre_especializacion}
                    </option>
                  ))}
                </select>
                <p className="text-xs leading-5 text-muted">
                  Selecciona un programa para analizarlo uno a uno. El microcurrículo detallado real solo está cargado para Visual Analytics and Big Data.
                </p>
              </label>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-line bg-slate-50 px-4 py-3">
                <span className="block text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-muted">Alineación</span>
                <strong className="mt-1 block text-lg text-ink">{selectedProgramAlignment.toFixed(1)}%</strong>
              </div>
              <div className="rounded-xl border border-line bg-slate-50 px-4 py-3">
                <span className="block text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-muted">Riesgo</span>
                <strong className="mt-1 block text-lg text-ink">{selectedProgramRisk.toFixed(1)}%</strong>
              </div>
              <div className="rounded-xl border border-line bg-slate-50 px-4 py-3">
                <span className="block text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-muted">Empleabilidad</span>
                <strong className="mt-1 block text-lg text-ink">{selectedProgramEmployability.toFixed(1)}%</strong>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2 text-xs font-medium text-muted">
              <span className="rounded-full border border-line bg-white px-2.5 py-1">
                {selectedProgram?.rol || 'Rol no disponible'}
              </span>
              <span className="rounded-full border border-line bg-white px-2.5 py-1">
                {selectedProgram?.total_empleos_relacionados ?? 0} señales laborales
              </span>
              <span className="rounded-full border border-line bg-white px-2.5 py-1">
                {selectedProgramSkills.length} skills visibles
              </span>
            </div>
          </article>

          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Análisis SNIES</span>
                <h3 className="mt-1 text-lg font-semibold text-ink">Universidades y programas comparables</h3>
              </div>
              <strong className="text-lg text-brand">{universityAverage.toFixed(1)}%</strong>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted">
              Comparativo virtual con oferta académica y equivalencias cercanas observadas en el SNIES.
            </p>
            <div className="mt-4 space-y-3">
              {relatedUniversityPrograms.length ? (
                relatedUniversityPrograms.slice(0, 3).map((item) => (
                  <div key={`${item.universidad}-${item.programa}`} className="rounded-xl border border-line bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <strong className="text-sm text-ink">{item.competidor || item.universidad}</strong>
                      <span className="text-sm font-semibold text-brand">{Math.round(Number(item.similitud || 0) * 100)}%</span>
                    </div>
                    <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{item.programa}</p>
                    <p className="mt-1 text-sm text-muted">{item.ciudad || 'Cobertura nacional'} · {item.modalidad || 'Modalidad no indicada'}</p>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="Sin comparación SNIES suficiente"
                  body="No se encontraron equivalencias académicas cercanas para este programa con el umbral actual."
                />
              )}
            </div>
          </article>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Skill match</span>
                <h3 className="mt-1 text-lg font-semibold text-ink">Skills frente al currículo analizado</h3>
              </div>
              <span className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-semibold text-muted">
                {selectedProgramSkills.length} cubiertas · {missingSkills.length} faltantes
              </span>
            </div>
            {!hasDetailedMicrocurriculum ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                El microcurrículo detallado real solo está cargado para Visual Analytics and Big Data. En este programa, el match se apoya en competencias y skills visibles del programa, no en una malla microcurricular completa.
              </div>
            ) : null}
            <div className="mt-4 space-y-3">
              {selectedProgramSkills.length ? (
                selectedProgramSkills.slice(0, 8).map((skill) => (
                  <div key={skill.skill_id} className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <strong className="text-sm text-ink">{skill.nombre}</strong>
                      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">
                        Cubierta
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="Sin skills cubiertas visibles"
                  body="El programa seleccionado todavía no expone un listado normalizado suficiente para este nivel de análisis."
                />
              )}
              {missingSkills.length > 0 && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
                  <span className="block text-xs font-semibold uppercase tracking-[0.12em] text-amber-700">Skills faltantes prioritarias</span>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {missingSkills.slice(0, 10).map((skill) => (
                      <span key={skill.skill_id} className="rounded-full border border-amber-200 bg-white px-3 py-1 text-xs font-medium text-amber-800">
                        {skill.nombre}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Match curricular</span>
                <h3 className="mt-1 text-lg font-semibold text-ink">Vacantes y correspondencia de skills</h3>
              </div>
              <span className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-semibold text-muted">
                {topMatches.length} señales
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {topMatches.length ? (
                topMatches.map((match) => (
                  <div key={match.empleo_id} className="rounded-xl border border-line bg-slate-50 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <strong className="block truncate text-sm text-ink">{match.titulo_empleo}</strong>
                        <p className="mt-1 text-xs text-muted">
                          {match.skills_en_comun} skills compartidas · {match.total_skills_empleo} requeridas
                        </p>
                      </div>
                      <strong className="shrink-0 text-sm text-brand">{Number(match.porcentaje_match || 0).toFixed(1)}%</strong>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-white">
                      <span
                        className="block h-2 rounded-full bg-brand"
                        style={{ width: `${Math.min(100, Math.max(0, Number(match.porcentaje_match || 0)))}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="Sin match visible"
                  body="No se encontraron vacantes priorizadas para comparar el currículo seleccionado en esta ejecución."
                />
              )}
            </div>
          </article>
        </div>

        <ExecutiveAiSection
          title="Análisis ejecutivo con IA"
          subtitle="La capa de IA resume el programa seleccionado con evidencia curricular, señales laborales y lectura ejecutiva."
          body={
            programExecutiveNarrative?.narrative ||
            programExecutiveNarrative?.why_at_risk ||
            'Análisis ejecutivo pendiente de datos suficientes. Selecciona un programa para obtener una explicación contextual.'
          }
          evidenceSources={programExecutiveNarrative?.evidence_sources}
          confidence={programExecutiveNarrative?.confidence}
          model={programExecutiveNarrative?.model}
          loading={executiveAiLoading}
          error={executiveAiError}
          emptyTitle="No fue posible cargar el análisis ejecutivo"
          emptyBody="La explicación del programa todavía no está disponible, pero el ranking sigue operativo."
          badgeLabel="Program AI"
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              <GraduationCap size={14} strokeWidth={2} />
              Programas analizados
            </div>
            <strong className="mt-3 block text-2xl font-semibold text-ink">{analyzedPrograms}</strong>
            <p className="mt-2 text-sm text-muted">Programas con evidencia curricular y/o laboral disponible en el observatorio.</p>
          </article>
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              <ShieldAlert size={14} strokeWidth={2} />
              Programas críticos
            </div>
            <strong className="mt-3 block text-2xl font-semibold text-ink">{criticalPrograms.length}</strong>
            <p className="mt-2 text-sm text-muted">Programas con mayor riesgo curricular observado.</p>
          </article>
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              <Target size={14} strokeWidth={2} />
              Programas con oportunidad
            </div>
            <strong className="mt-3 block text-2xl font-semibold text-ink">{opportunityPrograms.length}</strong>
            <p className="mt-2 text-sm text-muted">Programas con alineación alta y ventana clara de mejora.</p>
          </article>
          <article className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              <BarChart3 size={14} strokeWidth={2} />
              Alineación promedio
            </div>
            <strong className="mt-3 block text-2xl font-semibold text-ink">{averageAlignment.toFixed(1)}%</strong>
            <p className="mt-2 text-sm text-muted">Promedio institucional calculado desde inteligencia curricular real.</p>
          </article>
        </div>
      </div>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="panel space-y-4">
          <SectionTitle
            title="Top programas críticos"
            subtitle="Programas priorizados por riesgo curricular, brechas y presión del mercado. Cada tarjeta abre el detalle institucional del programa."
          />
          <div className="space-y-3">
            {criticalPrograms.length ? (
              criticalPrograms.map((program) => <RankingCard key={program.id} program={program} tone="critical" />)
            ) : (
              <EmptyState title="Sin programas críticos" body="No se detectaron programas por encima del umbral crítico en esta ejecución." />
            )}
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Comparación ejecutiva"
            subtitle="Lectura sintética para dirección académica con la ordenación del portafolio por alineación, riesgo y empleabilidad estimada."
          />
          <div className="space-y-3">
            {alignedPrograms.slice(0, 8).map((program, index) => (
              <Link
                to={`/programs/${program.id}`}
                key={program.id}
                className="flex items-start justify-between gap-3 rounded-2xl border border-line bg-white px-4 py-4 transition hover:border-brand/30 hover:shadow-sm"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-line bg-slate-50 px-2.5 py-1 text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-muted">
                      #{index + 1}
                    </span>
                    <strong className="truncate text-sm font-semibold text-ink">{program.name}</strong>
                  </div>
                  <p className="mt-1 text-xs text-muted">{program.area}</p>
                  <p className="mt-2 text-sm leading-6 text-muted">{program.topGap}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1 text-right">
                  <span className="text-sm font-semibold text-ink">{program.alignment.toFixed(1)}%</span>
                  <span className="text-xs text-muted">Riesgo {program.risk.toFixed(1)}%</span>
                  <ArrowUpRight size={16} strokeWidth={2} className="text-muted" />
                </div>
              </Link>
            ))}
          </div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <article className="panel space-y-4">
          <SectionTitle
            title="Top programas con oportunidad"
            subtitle="Programas con mejor posición relativa para recibir mejoras curriculares con impacto rápido en pertinencia y empleabilidad."
          />
          <div className="space-y-3">
            {opportunityPrograms.length ? (
              opportunityPrograms.map((program) => <RankingCard key={program.id} program={program} tone="opportunity" />)
            ) : (
              <EmptyState title="Sin programas de oportunidad" body="No se identificaron programas con oportunidad alta en esta ejecución." />
            )}
          </div>
        </article>

        <article className="panel space-y-4">
          <SectionTitle
            title="Señales ejecutivas"
            subtitle="Lo que el comité académico necesita ver para decidir con rapidez sobre el portafolio."
          />
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-line bg-white p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                <BriefcaseBusiness size={14} strokeWidth={2} />
                Programas con señal laboral
              </div>
              <strong className="mt-3 block text-2xl font-semibold text-ink">{programsWithSignal}</strong>
              <p className="mt-2 text-sm text-muted">Programas con brechas, riesgo o señales laborales activas.</p>
            </div>
            <div className="rounded-2xl border border-line bg-white p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                <TrendingUp size={14} strokeWidth={2} />
                Riesgo promedio
              </div>
              <strong className="mt-3 block text-2xl font-semibold text-ink">{averageRisk.toFixed(1)}%</strong>
              <p className="mt-2 text-sm text-muted">Promedio de riesgo curricular sobre el portafolio analizado.</p>
            </div>
            <div className="rounded-2xl border border-line bg-white p-4 md:col-span-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                <Layers3 size={14} strokeWidth={2} />
                Lectura de portafolio
              </div>
              <p className="mt-3 text-sm leading-7 text-ink">
                La institución ya tiene una base real de inteligencia por programa; esta vista la reorganiza para priorizar intervención, mostrar oportunidad y facilitar discusión ejecutiva sin depender de una grilla genérica.
              </p>
            </div>
          </div>
        </article>
      </section>
    </section>
  );
}
