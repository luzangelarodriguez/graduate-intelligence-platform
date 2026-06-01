import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Radar,
  RefreshCw,
  Target,
  TrendingUp,
  X,
} from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { ProgramObservatoryCards } from '../components/ProgramObservatoryCards';
import { ProgramSelectorStrip, getProgramDomainContext } from '../components/program-intelligence/ProgramIntelligenceBlocks';
import { Link } from 'react-router-dom';
import { useDashboardData } from '../hooks/useDashboardData';
import { useProgramIntelligenceData } from '../hooks/useProgramIntelligenceData';

type DrilldownId = 'pertinence' | 'skills' | 'roles' | 'trend' | 'digital' | 'update' | 'ranking';

const drilldownMeta: Record<DrilldownId, { title: string; subtitle: string }> = {
  pertinence: {
    title: 'Ãndice de pertinencia curricular',
    subtitle: 'Evidencia que explica la alineaciÃ³n actual del programa seleccionado.',
  },
  skills: {
    title: 'Skills crÃ­ticas faltantes',
    subtitle: 'Competencias priorizadas para revisar cobertura, profundidad o actualizaciÃ³n.',
  },
  roles: {
    title: 'Roles laborales con alta demanda',
    subtitle: 'Vacantes y roles usados como seÃ±al de demanda laboral relacionada.',
  },
  trend: {
    title: 'Tendencia de empleabilidad',
    subtitle: 'SeÃ±ales de match laboral con mayor intensidad en el mercado procesado.',
  },
  digital: {
    title: 'Cobertura de habilidades digitales',
    subtitle: 'Lectura de herramientas, skills tÃ©cnicas y capacidades digitales del programa.',
  },
  update: {
    title: 'SeÃ±al de actualizaciÃ³n curricular',
    subtitle: 'Recomendaciones automÃ¡ticas para orientar decisiones acadÃ©micas.',
  },
  ranking: {
    title: 'Ranking completo de pertinencia',
    subtitle: 'Comparativo ampliado de programas por alineaciÃ³n laboral.',
  },
};

export function DashboardPage() {
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
    isProgramLoading,
    error,
  } = useDashboardData();
  const { programIntelligence: selectedProgramIntelligence } = useProgramIntelligenceData(selectedProgramId ?? null);
  const [activeDrilldown, setActiveDrilldown] = useState<DrilldownId | null>(null);
  const selectedDomain = getProgramDomainContext(selectedProgramIntelligence);

  const contextualKpis = programDashboard?.kpis;
  const contextualInsights = programDashboard?.insights;
  const missingSkills = programDashboard?.missing_skills ?? [];
  const activeAlignment = Number(contextualKpis?.alignment_score ?? selectedProgram?.promedio_match_mercado ?? 0);
  const evidenceMatches = matches;
  const missingCriticalSkills = Number(contextualKpis?.missing_critical_skills ?? missingSkills.length);
  const topDemandRoles = Number(contextualKpis?.high_demand_roles ?? 0);
  const selectedDigitalCoverage = Number(contextualKpis?.digital_coverage ?? 0);
  const employabilityTrend = Number(contextualKpis?.employability_trend ?? 0);
  const updateSignal = contextualKpis?.curricular_update_signal ?? 'Sin seÃ±al';
  const programName = selectedProgram?.nombre_especializacion ?? 'Selecciona un programa acadÃ©mico';
  const competitorAverage = relatedUniversityPrograms.length
    ? relatedUniversityPrograms.reduce((total, item) => total + Number(item.similitud || 0) * 100, 0) /
      relatedUniversityPrograms.length
    : 0;
  const competitorGap = activeAlignment - competitorAverage;
  const comparativeRank =
    competitorGap >= 8 ? 'Superior' : competitorGap >= -8 ? 'En paridad' : 'Brecha competitiva';

  const drilldownRows = useMemo(() => {
    if (activeDrilldown === 'ranking') {
      return [...programs]
        .sort((a, b) => b.promedio_match_mercado - a.promedio_match_mercado)
        .slice(0, 25)
        .map((program, index) => ({
          title: program.nombre_especializacion,
          metric: `#${index + 1} · ${Number(program.promedio_match_mercado || 0).toFixed(1)}%`,
          detail: `${program.total_empleos_relacionados || 0} señales laborales relacionadas`,
        }));
    }

    if (activeDrilldown === 'roles' || activeDrilldown === 'trend') {
      return evidenceMatches.slice(0, 12).map((match) => ({
        title: match.titulo_empleo,
        metric: `${Number(match.porcentaje_match || 0).toFixed(1)}%`,
        detail: `${match.skills_en_comun} skills compartidas de ${match.total_skills_empleo} requeridas`,
      }));
    }

    if (activeDrilldown === 'skills' || activeDrilldown === 'digital') {
      const rows = activeDrilldown === 'skills' ? missingSkills : selectedProgram?.skills ?? [];
      return rows.slice(0, 22).map((skill) => ({
        title: skill.nombre,
        metric: skill.conteo ? `${skill.conteo}` : 'Skill',
        detail:
          activeDrilldown === 'skills'
            ? 'Skill demandada por el mercado y ausente en el programa activo.'
            : 'Skill o herramienta presente en el programa activo.',
      }));
    }

    if (activeDrilldown === 'update') {
      const academicRecommendations = contextualInsights?.ai_recommends ?? [];
      return academicRecommendations.map((item, index) => ({
        title: `RecomendaciÃ³n ${index + 1}`,
        metric: updateSignal,
        detail: item,
      }));
    }

    return [
      {
        title: programName,
        metric: `${activeAlignment.toFixed(1)}%`,
        detail: 'AlineaciÃ³n contextual entre competencias curriculares y seÃ±ales laborales.',
      },
      {
        title: 'Roles laborales relacionados',
        metric: `${selectedProgram?.total_empleos_relacionados ?? evidenceMatches.length}`,
        detail: 'Volumen de vacantes asociadas al programa seleccionado.',
      },
      {
        title: 'Skills crÃ­ticas faltantes',
        metric: `${missingCriticalSkills}`,
        detail: 'Skills de mercado detectadas como brecha para este programa.',
      },
    ];
  }, [
    activeAlignment,
    activeDrilldown,
    contextualInsights,
    evidenceMatches,
    missingCriticalSkills,
    missingSkills,
    programName,
    programs,
    selectedProgram,
    updateSignal,
  ]);

  if (isLoading) {
    return <LoadingState />;
  }

  const strategicKpis = [
    {
      id: 'skills',
      label: 'Skills crÃ­ticas faltantes',
      value: missingCriticalSkills,
      detail: 'Brechas curriculares prioritarias.',
      icon: AlertTriangle,
      tone: 'amber',
    },
    {
      id: 'roles',
      label: 'Roles con alta demanda',
      value: topDemandRoles,
      detail: 'Vacantes con seÃ±al relevante.',
      icon: BriefcaseBusiness,
      tone: 'green',
    },
    {
      id: 'trend',
      label: 'Tendencia de empleabilidad',
      value: `${employabilityTrend.toFixed(1)}%`,
      detail: 'Mejor seÃ±al del programa.',
      icon: TrendingUp,
      tone: 'violet',
    },
    {
      id: 'digital',
      label: 'Cobertura digital',
      value: `${selectedDigitalCoverage.toFixed(1)}%`,
      detail: 'Herramientas y capacidades.',
      icon: Radar,
      tone: 'cyan',
    },
    {
      id: 'update',
      label: 'ActualizaciÃ³n curricular',
      value: updateSignal,
      detail: 'Prioridad acadÃ©mica.',
      icon: RefreshCw,
      tone: 'slate',
    },
  ] as const;

  return (
    <div className="space-y-5">
      {error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
          {error}. La vista continúa mostrando el selector, el ranking y la evidencia disponible.
        </div>
      ) : null}

      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4 rounded-3xl border border-line bg-white p-6 shadow-sm">
          <div className="institutional-mark">
            <BarChart3 size={17} strokeWidth={1.8} />
            <span>Observatorio ejecutivo de pertinencia académica</span>
          </div>
          <div className="space-y-3">
            <h2 className="text-balance text-3xl font-semibold leading-tight text-ink md:text-4xl">{programName}</h2>
            <p className="max-w-3xl text-sm leading-7 text-muted md:text-base">
              Lectura institucional de alineación curricular, demanda laboral y brechas de habilidades para orientar
              decisiones académicas.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              className="inline-flex items-center justify-center rounded-full border border-brand/15 bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand/90"
              to="/programas"
            >
              Explorar ranking
            </Link>
            {selectedProgramId && (
              <Link
                className="inline-flex items-center justify-center rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:border-brand/40 hover:text-brand"
                to={`/programs/${selectedProgramId}`}
              >
                Abrir detalle ejecutivo
              </Link>
            )}
          </div>
        </div>

        <ProgramSelectorStrip
          programs={programs}
          selectedProgramId={selectedProgramId ?? programs[0]?.especializacion_id ?? null}
          onChange={setSelectedProgramId}
          domainLabel={selectedDomain.domainLabel}
          subdomainLabel={selectedDomain.subdomainLabel}
          benchmarkLabel={selectedDomain.benchmarkLabel}
          label="Especialización seleccionada"
          helper="Selecciona un programa para analizarlo uno a uno. El microcurrículo detallado real solo está cargado para Visual Analytics and Big Data."
          note="El análisis de los demás programas se hace con competencias, skills del programa y señales de mercado."
          primaryActionLabel="Analizar especialización"
          primaryActionHref={selectedProgramId ? `/programs/${selectedProgramId}` : undefined}
          secondaryActionLabel="Generar microcurrículo actualizado"
          secondaryActionHref={selectedProgramId ? `/programs/${selectedProgramId}/microcurriculum` : undefined}
        />
      </section>

      {isProgramLoading && <div className="context-refresh">Actualizando lectura contextual del programa...</div>}

      <section className="intelligence-layer">
        <button className="kpi-hero-card interactive" type="button" onClick={() => setActiveDrilldown('pertinence')}>
          <div className="kpi-icon-orbit">
            <Target size={24} strokeWidth={1.8} />
          </div>
          <span>Lectura estratÃ©gica</span>
          <strong>{activeAlignment.toFixed(1)}%</strong>
          <h3>Ãndice de pertinencia curricular</h3>
          <p>
            {contextualInsights?.detected ??
              'Lectura contextual del ajuste entre currÃ­culo y demanda laboral del programa activo.'}
          </p>
          <div className="kpi-hero-meter">
            <span style={{ width: `${Math.min(100, Math.max(0, activeAlignment))}%` }} />
          </div>
        </button>

        <div className="strategic-kpi-grid">
          {strategicKpis.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={`strategic-kpi-card interactive ${item.tone}`}
                key={item.label}
                type="button"
                onClick={() => setActiveDrilldown(item.id)}
              >
                <div className="strategic-kpi-icon">
                  <Icon size={18} strokeWidth={1.8} />
                </div>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <p>{item.detail}</p>
              </button>
            );
          })}
        </div>
      </section>

      <section className="dashboard-core-grid">
        <article className="panel observatory-section">
          <div className="section-head">
            <div>
              <h3>Benchmarking de pertinencia curricular</h3>
              <p>Top 5 por alineaciÃ³n laboral y evidencia de mercado.</p>
            </div>
          </div>
          <ProgramObservatoryCards
            programs={topPrograms}
            selectedProgramId={selectedProgramId}
            onSelectProgram={setSelectedProgramId}
            onViewFullRanking={() => setActiveDrilldown('ranking')}
          />
        </article>

        <article className="panel related-programs-panel">
          <div className="section-head">
            <div>
              <h3>Benchmark competitivo virtual</h3>
              <p>Competidores estrategicos virtuales priorizados en SNIES.</p>
            </div>
          </div>

          <div className="competitive-kpis">
            <div>
              <span>Posicion competitiva</span>
              <strong>{comparativeRank}</strong>
            </div>
            <div>
              <span>Promedio competidores</span>
              <strong>{competitorAverage.toFixed(1)}%</strong>
            </div>
            <div>
              <span>Diferencia virtual</span>
              <strong>
                {competitorGap >= 0 ? '+' : ''}
                {competitorGap.toFixed(1)} pts
              </strong>
            </div>
          </div>

          <div className="related-programs-list">
            {relatedUniversityPrograms.map((item) => (
              <article className="related-program-card" key={`${item.universidad}-${item.programa}`}>
                <div className="related-program-card-head">
                  <strong>{item.competidor || item.universidad}</strong>
                  <span>{`${Math.round(Number(item.similitud || 0) * 100)}%`}</span>
                </div>
                {item.competidor && <small className="related-program-institution">{item.universidad}</small>}
                <p>{item.programa}</p>
                <div className="related-program-meta">
                  <span>{item.ciudad || 'Nacional'}</span>
                  <span>{item.modalidad || 'Virtual'}</span>
                  {item.duracion && <span>{`${item.duracion} periodos`}</span>}
                </div>
              </article>
            ))}

            {!relatedUniversityPrograms.length && (
              <EmptyState
                title="Sin equivalencias suficientes"
                body="El SNIES no registra una oferta virtual activa cercana para este programa con el umbral actual."
              />
            )}
          </div>
        </article>
      </section>

      {activeDrilldown && (
        <div className="drilldown-overlay" role="presentation" onClick={() => setActiveDrilldown(null)}>
          <aside className="drilldown-drawer" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="drilldown-head">
              <div>
                <span>Detalle analÃ­tico</span>
                <h3>{drilldownMeta[activeDrilldown].title}</h3>
                <p>{drilldownMeta[activeDrilldown].subtitle}</p>
              </div>
              <button type="button" aria-label="Cerrar detalle" onClick={() => setActiveDrilldown(null)}>
                <X size={18} strokeWidth={1.8} />
              </button>
            </div>

            <div className="drilldown-program">
              <span>Programa analizado</span>
              <strong>{programName}</strong>
            </div>

            <div className="drilldown-list">
              {drilldownRows.length ? (
                drilldownRows.map((row, index) => (
                  <article className="drilldown-row" key={`${row.title}-${index}`}>
                    <div>
                      <strong>{row.title}</strong>
                      <p>{row.detail}</p>
                    </div>
                    <span>{row.metric}</span>
                  </article>
                ))
              ) : (
                <EmptyState
                  title="Sin evidencia suficiente"
                  body="El programa activo todavÃ­a no tiene datos normalizados para este nivel de anÃ¡lisis."
                />
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}



