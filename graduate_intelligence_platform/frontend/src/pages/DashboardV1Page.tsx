import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import {
  DataTable,
  EmptyDiagnostic,
  LoadingPanel,
  MetricCard,
  PageHero,
  SectionCard,
} from '../components/institutional/InstitutionalPrimitives';
import { ProgramObservatoryCards } from '../components/ProgramObservatoryCards';
import { ProgramSelectorStrip } from '../components/program-intelligence/ProgramIntelligenceBlocks';
import {
  getDashboardKpis,
  getEmpleos,
  getEmpleoDetail,
  getMatches,
  getProgramDashboard,
  getProgramMarketAlignment,
  getProgramRecommendedJobs,
  getProgramSkillGaps,
  getProgramMatches,
  getProgramas,
} from '../services/api';
import type {
  DashboardKpis,
  Job,
  Match,
  Program,
  ProgramDashboardResponse,
  UniversityMarketAlignmentResponse,
} from '../types/api';

type ProgramSkillGapsResponse = { program_id: number; program_name: string; missing_skills: unknown[]; taught_not_demanded?: unknown[] };
type ProgramRecommendedJobsResponse = {
  program_id: number;
  program_name: string;
  recommended_jobs: unknown[];
  nearest_jobs?: unknown[];
  nearest_programs?: unknown[];
};
type MarketSignal = {
  entity_name: string;
  growth_velocity: number;
  horizon_months?: number;
  market_phase?: string;
};

function normalizeText(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function firstString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
}

function formatPercent(value: number) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function humanizeLabel(value: string) {
  const cleaned = value.replace(/[_-]+/g, ' ').trim();
  if (!cleaned) return '';
  return cleaned
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function getProgramEvidenceContext(program?: Program | null) {
  const evidence = (program?.microcurriculum_context || {}) as Record<string, unknown>;
  const taxonomy = (evidence.domain_taxonomy || {}) as Record<string, unknown>;
  const benchmark = (evidence.domain_benchmark || {}) as Record<string, unknown>;
  const benchmarkInstitutions = Array.isArray(benchmark.benchmark_institutions) ? benchmark.benchmark_institutions : [];
  const domainKey = typeof taxonomy.domain_key === 'string' ? taxonomy.domain_key : '';
  const subdomainKey = typeof taxonomy.subdomain === 'string' ? taxonomy.subdomain : '';

  return {
    domainLabel: domainKey ? humanizeLabel(domainKey) : 'Dominio no disponible',
    subdomainLabel: subdomainKey ? humanizeLabel(subdomainKey) : 'Subdominio no disponible',
    benchmarkLabel:
      benchmarkInstitutions.length > 0
        ? `${benchmarkInstitutions.length} instituciones comparables`
        : 'Benchmark no disponible',
  };
}

function extractSkillLabel(value: unknown): string {
  if (typeof value === 'string') return value.trim();
  if (Array.isArray(value)) return value.map((item) => extractSkillLabel(item)).find(Boolean) || '';
  if (!value || typeof value !== 'object') return '';
  const record = value as Record<string, unknown>;
  return firstString(
    record.skill,
    record.missing_skill,
    record.canonical_skill,
    record.canonical_skill_name,
    record.nombre,
    record.name,
    record.title,
    record.label,
  );
}

function extractFrequency(value: unknown): number {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 1;
  const record = value as Record<string, unknown>;
  const count = Number(record.conteo ?? record.frequency ?? record.count ?? record.weight ?? record.priority ?? 1);
  return Number.isFinite(count) && count > 0 ? count : 1;
}

function buildRankedSignals(values: string[], phaseLabel: string): MarketSignal[] {
  const registry = new Map<string, { label: string; count: number }>();
  values.forEach((value) => {
    const label = value.trim();
    if (!label) return;
    const key = normalizeText(label);
    const current = registry.get(key) || { label, count: 0 };
    current.count += 1;
    registry.set(key, current);
  });

  const maxCount = Math.max(...[...registry.values()].map((item) => item.count), 1);

  return [...registry.values()]
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
    .slice(0, 8)
    .map((item) => ({
      entity_name: item.label,
      growth_velocity: item.count / maxCount,
      horizon_months: item.count,
      market_phase: phaseLabel,
    }));
}

function logEndpointProbe(label: string, url: string, result: PromiseSettledResult<unknown>, consumed: Record<string, unknown>) {
  const status = result.status === 'fulfilled' ? '200' : 'error';
  const payload = result.status === 'fulfilled' ? result.value : result.reason;
  console.groupCollapsed(`[DashboardV1Page] ${label}`);
  console.info('URL llamada:', url);
  console.info('Status HTTP:', status);
  console.info('Payload recibido:', payload);
  console.info('Campo exacto que consume React:', consumed);
  console.groupEnd();
}

function MarketSeriesCard({
  title,
  subtitle,
  items,
  color,
  emptyTitle,
  emptyBody,
}: {
  title: string;
  subtitle: string;
  items: MarketSignal[];
  color: string;
  emptyTitle: string;
  emptyBody: string;
}) {
  const chartData = items.slice(0, 8).map((item) => ({
    name: item.entity_name,
    value: Math.max(0, Number(item.growth_velocity || 0) * 100),
  }));

  return (
    <SectionCard title={title} subtitle={subtitle}>
      {chartData.length ? (
        <div className="h-[290px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={130}
                tick={{ fontSize: 11, fill: '#516170' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip />
              <Bar dataKey="value" radius={[0, 8, 8, 0]} fill={color}>
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyDiagnostic
          title={emptyTitle}
          cause="La fuente real no devolvió señales visibles para este eje."
          endpoint="/api/empleos"
          action={emptyBody}
        />
      )}

      {chartData.length ? (
        <ul className="mt-4 space-y-2 text-sm text-muted">
          {chartData.slice(0, 5).map((item) => (
            <li key={`${title}-${item.name}`} className="flex items-center justify-between gap-4 rounded-xl border border-line bg-slate-50 px-3 py-2">
              <span className="min-w-0 truncate font-medium text-ink">{item.name}</span>
              <span className="shrink-0 font-semibold text-ink">{item.value.toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      ) : null}
    </SectionCard>
  );
}

export function DashboardV1Page() {
  const [marketState, setMarketState] = useState<{
    dashboardKpis: DashboardKpis | null;
    jobs: { empleo_id: string; titulo?: string; empresa?: string; skills?: string[] }[];
    matches: Match[];
    programs: Program[];
    isLoading: boolean;
    error: string | null;
  }>({
    dashboardKpis: null,
    jobs: [],
    matches: [],
    programs: [],
    isLoading: true,
    error: null,
  });

  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [selectedProgramState, setSelectedProgramState] = useState<{
    programDashboard: ProgramDashboardResponse | null;
    alignment: UniversityMarketAlignmentResponse | null;
    skillGaps: ProgramSkillGapsResponse | null;
    recommendedJobs: ProgramRecommendedJobsResponse | null;
    matches: Match[];
    jobDetails: Record<string, Job>;
    isLoading: boolean;
    error: string | null;
  }>({
    programDashboard: null,
    alignment: null,
    skillGaps: null,
    recommendedJobs: null,
    matches: [],
    jobDetails: {},
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadMarketData() {
      try {
        setMarketState((current) => ({ ...current, isLoading: true, error: null }));
        const [kpisResult, programsResult, jobsResult, matchesResult] = await Promise.allSettled([
          getDashboardKpis(),
          getProgramas(100),
          getEmpleos(100),
          getMatches(100),
        ]);

        if (cancelled) return;

        setMarketState({
          dashboardKpis: kpisResult.status === 'fulfilled' ? kpisResult.value.kpis : null,
          jobs: jobsResult.status === 'fulfilled' ? jobsResult.value.items ?? [] : [],
          matches: matchesResult.status === 'fulfilled' ? matchesResult.value.items ?? [] : [],
          programs: programsResult.status === 'fulfilled' ? programsResult.value.items ?? [] : [],
          isLoading: false,
          error: [kpisResult, programsResult, jobsResult, matchesResult].some((result) => result.status === 'rejected')
            ? 'No fue posible cargar una parte del observatorio. La vista continúa con el resto de los datos reales disponibles.'
            : null,
        });
        logEndpointProbe('/api/dashboard/kpis', '/api/dashboard/kpis', kpisResult, {
          dashboardKpis: kpisResult.status === 'fulfilled' ? kpisResult.value.kpis : null,
          consumedBy: 'marketState.dashboardKpis',
        });
        logEndpointProbe('/api/programas', '/api/programas', programsResult, {
          itemsLength: programsResult.status === 'fulfilled' ? programsResult.value.items?.length ?? 0 : 0,
          consumedBy: 'marketState.programs',
        });
        logEndpointProbe('/api/empleos', '/api/empleos', jobsResult, {
          itemsLength: jobsResult.status === 'fulfilled' ? jobsResult.value.items?.length ?? 0 : 0,
          consumedBy: 'marketState.jobs',
        });
        logEndpointProbe('/api/matches', '/api/matches', matchesResult, {
          itemsLength: matchesResult.status === 'fulfilled' ? matchesResult.value.items?.length ?? 0 : 0,
          consumedBy: 'marketState.matches',
        });
      } catch (cause) {
        if (!cancelled) {
          setMarketState((current) => ({
            ...current,
            isLoading: false,
            error: cause instanceof Error ? cause.message : 'No fue posible cargar los datos del mercado.',
          }));
        }
      }
    }

    void loadMarketData();
    return () => {
      cancelled = true;
    };
  }, []);

  const visiblePrograms = useMemo(() => marketState.programs, [marketState.programs]);

  useEffect(() => {
    if (!selectedProgramId && visiblePrograms.length > 0) {
      setSelectedProgramId(visiblePrograms[0].especializacion_id);
    }
  }, [visiblePrograms, selectedProgramId]);

  useEffect(() => {
    if (selectedProgramId == null) return;
    const programId = selectedProgramId;

    let cancelled = false;

    async function loadSelectedProgram() {
      try {
        setSelectedProgramState((current) => ({
          ...current,
          isLoading: true,
          error: null,
          matches: [],
          jobDetails: {},
          programDashboard: null,
          alignment: null,
          skillGaps: null,
          recommendedJobs: null,
        }));
        const [dashboardResult, alignmentResult, gapsResult, recommendationsResult, matchesResult] = await Promise.allSettled([
          getProgramDashboard(programId),
          getProgramMarketAlignment(programId),
          getProgramSkillGaps(programId),
          getProgramRecommendedJobs(programId),
          getProgramMatches(programId, 20),
        ]);

        const resolvedMatches = matchesResult.status === 'fulfilled' ? matchesResult.value.items ?? [] : [];
        const jobDetailsEntries = await Promise.all(
          resolvedMatches.slice(0, 12).map(async (match) => {
            const detail = await getEmpleoDetail(match.empleo_id).catch(() => null);
            return [String(match.empleo_id), detail] as const;
          }),
        );

        if (cancelled) return;

        setSelectedProgramState({
          programDashboard: dashboardResult.status === 'fulfilled' ? dashboardResult.value : null,
          alignment: alignmentResult.status === 'fulfilled' ? alignmentResult.value : null,
          skillGaps: gapsResult.status === 'fulfilled' ? gapsResult.value : null,
          recommendedJobs: recommendationsResult.status === 'fulfilled' ? recommendationsResult.value : null,
          matches: resolvedMatches,
          jobDetails: Object.fromEntries(jobDetailsEntries.filter((entry): entry is readonly [string, Job] => Boolean(entry[1]))),
          isLoading: false,
          error: [dashboardResult, alignmentResult, gapsResult, recommendationsResult, matchesResult].some((result) => result.status === 'rejected')
            ? 'El detalle del programa cargó parcialmente, pero la vista conserva la evidencia disponible.'
            : null,
        });
        logEndpointProbe(
          `/api/programas/${programId}`,
          `/api/dashboard/programa/${programId}`,
          dashboardResult,
          {
            programId,
            consumedFields: {
              program: 'selectedProgramState.programDashboard.program',
              kpis: 'selectedProgramState.programDashboard.kpis',
              status: 'selectedProgramState.programDashboard.status',
              missingSkills: 'selectedProgramState.programDashboard.missing_skills',
              matches: 'selectedProgramState.programDashboard.matches',
              recommendations: 'selectedProgramState.programDashboard.recommendations',
              insights: 'selectedProgramState.programDashboard.insights',
            },
          },
        );
        logEndpointProbe(`/api/programas/${programId}/market-alignment`, `/api/programas/${programId}/market-alignment`, alignmentResult, {
          programId,
          alignmentScore: alignmentResult.status === 'fulfilled' ? alignmentResult.value.alignment_score : null,
          currentAlignment: alignmentResult.status === 'fulfilled' ? alignmentResult.value.current_alignment : null,
          projectedAlignmentIfAdded: alignmentResult.status === 'fulfilled' ? alignmentResult.value.projected_alignment_if_added : null,
          missingSkills: alignmentResult.status === 'fulfilled' ? alignmentResult.value.missing_skills : null,
          consumedField: 'selectedAlignmentScore',
        });
        logEndpointProbe(`/api/programas/${programId}/skill-gaps`, `/api/programas/${programId}/skill-gaps`, gapsResult, {
          programId,
          missingSkills: gapsResult.status === 'fulfilled' ? gapsResult.value.missing_skills : null,
          taughtNotDemanded: gapsResult.status === 'fulfilled' ? gapsResult.value.taught_not_demanded : null,
          consumedFields: {
            selectedGapRows: 'selectedProgramState.skillGaps.missing_skills -> selectedGapRows',
            selectedMissingCriticalSkills: 'selectedProgramState.skillGaps.missing_skills.length',
          },
        });
        logEndpointProbe(
          `/api/programas/${programId}/recommended-jobs`,
          `/api/programas/${programId}/recommended-jobs`,
          recommendationsResult,
          {
            programId,
            recommendedJobsLength: recommendationsResult.status === 'fulfilled' ? recommendationsResult.value.recommended_jobs?.length ?? 0 : 0,
            nearestJobsKeys: recommendationsResult.status === 'fulfilled' ? Object.keys(recommendationsResult.value.nearest_jobs || {}) : [],
            nearestProgramsKeys: recommendationsResult.status === 'fulfilled' ? Object.keys(recommendationsResult.value.nearest_programs || {}) : [],
            consumedField: 'selectedProgramState.recommendedJobs.recommended_jobs',
          },
        );
        logEndpointProbe(`/api/matches/programa/${programId}`, `/api/matches/programa/${programId}`, matchesResult, {
          programId,
          matchesLength: matchesResult.status === 'fulfilled' ? matchesResult.value.items?.length ?? 0 : 0,
          consumedField: 'selectedProgramState.matches',
        });
      } catch (cause) {
        if (!cancelled) {
          setSelectedProgramState((current) => ({
            ...current,
            isLoading: false,
            error: cause instanceof Error ? cause.message : 'No fue posible cargar el detalle del programa.',
          }));
        }
      }
    }

    void loadSelectedProgram();
    return () => {
      cancelled = true;
    };
  }, [selectedProgramId]);

  const selectedProgram = useMemo(
    () => visiblePrograms.find((program) => program.especializacion_id === selectedProgramId) || visiblePrograms[0] || null,
    [visiblePrograms, selectedProgramId],
  );

  const selectedProgramDashboard = selectedProgramState.programDashboard;
  const selectedProgramName =
    selectedProgram?.nombre_especializacion ?? selectedProgramDashboard?.program?.nombre_especializacion ?? 'Selecciona un programa';
  const selectedProgramDomain = getProgramEvidenceContext(selectedProgramDashboard?.program || selectedProgram);
  const selectedAlignmentScore = Number(
    selectedProgramState.alignment?.alignment_score ??
      selectedProgramState.alignment?.current_alignment ??
      selectedProgramDashboard?.kpis?.alignment_score ??
      selectedProgram?.promedio_match_mercado ??
      0,
  );
  const selectedCoverageScore = Number(
    selectedProgramState.alignment?.current_alignment ??
      selectedProgramDashboard?.kpis?.digital_coverage ??
      selectedProgram?.promedio_match_mercado ??
      0,
  );
  const selectedGapScore = Math.max(0, 100 - selectedCoverageScore);
  const selectedMissingCriticalSkills = Number(
    selectedProgramState.alignment?.missing_skills?.length ??
      selectedProgramState.skillGaps?.missing_skills?.length ??
      selectedProgramDashboard?.kpis?.missing_critical_skills ??
      0,
  );

  const selectedRecommendationRows = useMemo(() => {
    const recommendedJobs = (selectedProgramState.recommendedJobs?.recommended_jobs || []) as Record<string, unknown>[];
    const rows = recommendedJobs.map((item) => {
      const jobId = firstString(item.job_id, item.empleo_id, item.id, item.job, '');
      const detail = jobId ? selectedProgramState.jobDetails[jobId] : null;
      const title = firstString(item.job_title, item.titulo_empleo, item.nombre, item.title, detail?.titulo, jobId || 'Sin título');
      const company = firstString(item.company, item.empresa, detail?.empresa, 'Sin empresa detectada');
      const matchValue = Number(item.match_score ?? item.match ?? item.porcentaje_match ?? item.score ?? 0);
      const commonSkills = Number(item.skills_en_comun ?? item.shared_skills ?? item.total_skills_comunes ?? 0);
      const url = firstString(item.url, detail?.url, '');
      const titleNode = url ? (
        <a className="font-semibold text-brand underline decoration-brand/30 underline-offset-2 hover:decoration-brand" href={url} rel="noreferrer" target="_blank">
          {title}
        </a>
      ) : (
        <span className="font-medium text-ink">{title}</span>
      );
      return [selectedProgramName, titleNode, company, formatPercent(matchValue), commonSkills > 0 ? String(commonSkills) : 'N/D'];
    });

    if (rows.length > 0) return rows.slice(0, 12);

    return selectedProgramState.matches.slice(0, 12).map((match) => {
      const job = selectedProgramState.jobDetails[match.empleo_id];
      const title = firstString(job?.titulo, match.titulo_empleo, match.empleo_id);
      const company = firstString(job?.empresa, 'Sin empresa detectada');
      const url = firstString(job?.url, '');
      const titleNode = url ? (
        <a className="font-semibold text-brand underline decoration-brand/30 underline-offset-2 hover:decoration-brand" href={url} rel="noreferrer" target="_blank">
          {title}
        </a>
      ) : (
        <span className="font-medium text-ink">{title}</span>
      );
      return [selectedProgramName, titleNode, company, formatPercent(Number(match.porcentaje_match || 0)), `${Number(match.skills_en_comun || 0)} / ${Number(match.total_skills_empleo || 0)}`];
    });
  }, [selectedProgramName, selectedProgramState.jobDetails, selectedProgramState.matches, selectedProgramState.recommendedJobs?.recommended_jobs]);

  const selectedGapRows = useMemo(() => {
    const gaps =
      (selectedProgramState.skillGaps?.missing_skills || []).flatMap((item) => {
        const label = extractSkillLabel(item);
        return label ? [label] : [];
      }) || [];
    const fallback = selectedProgramDashboard?.missing_skills?.map((skill) => skill.nombre).filter(Boolean) || [];
    const values = gaps.length > 0 ? gaps : fallback;
    return values.slice(0, 10).map((skill) => [skill, 1, selectedProgramName]);
  }, [selectedProgramDashboard?.missing_skills, selectedProgramName, selectedProgramState.skillGaps?.missing_skills]);

  const jobSkillUniverse = useMemo(() => {
    const jobSkills = marketState.jobs.flatMap((job) => (job.skills || []).map((skill) => skill.trim()).filter(Boolean));
    return new Set(jobSkills.map((skill) => normalizeText(skill)).filter(Boolean)).size;
  }, [marketState.jobs]);

  const recommendationCount = useMemo(() => {
    const totalFromKpis = Number(marketState.dashboardKpis?.total_empleos_relacionados || 0);
    const selectedRecommendations = selectedProgramState.recommendedJobs?.recommended_jobs?.length || 0;
    return Math.max(totalFromKpis, selectedRecommendations, selectedRecommendationRows.length);
  }, [marketState.dashboardKpis?.total_empleos_relacionados, selectedProgramState.recommendedJobs?.recommended_jobs, selectedRecommendationRows.length]);

  const companyCount = useMemo(() => {
    const companies = marketState.jobs.map((job) => firstString(job.empresa, '')).filter(Boolean);
    return new Set(companies.map((value) => normalizeText(value)).filter(Boolean)).size;
  }, [marketState.jobs]);

  const topSkillSignals = useMemo(() => buildRankedSignals(marketState.jobs.flatMap((job) => job.skills || []), 'Skills de mercado'), [marketState.jobs]);
  const topCompanySignals = useMemo(
    () => buildRankedSignals(marketState.jobs.map((job) => firstString(job.empresa, '')).filter(Boolean), 'Empresas observadas'),
    [marketState.jobs],
  );
  const topRoleSignals = useMemo(
    () => buildRankedSignals([...marketState.jobs.map((job) => firstString(job.titulo, '')), ...marketState.matches.map((match) => firstString(match.titulo_empleo, ''))].filter(Boolean), 'Cargos observados'),
    [marketState.jobs, marketState.matches],
  );

  const loading = marketState.isLoading;
  const effectiveProgramsError = marketState.error || selectedProgramState.error;
  const selectedInsights = selectedProgramDashboard?.insights;
  const selectedStatus = selectedProgramDashboard?.status;
  const selectedKpis = selectedProgramDashboard?.kpis;

  const sections = [
    { id: 'resumen', label: 'Resumen Ejecutivo' },
    { id: 'pertinencia', label: 'Pertinencia Académica' },
    { id: 'recomendaciones', label: 'Recomendaciones' },
    { id: 'brechas', label: 'Brechas' },
    { id: 'mercado', label: 'Mercado Laboral' },
  ];

  if (loading) {
    return <LoadingPanel label="Cargando dashboard académico con datos reales..." />;
  }

  return (
    <div className="space-y-5">
      {effectiveProgramsError ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
          {effectiveProgramsError}. El dashboard continúa mostrando únicamente datos reales del warehouse y del observatorio.
        </div>
      ) : null}

      <PageHero
        eyebrow="Dashboard académico v1"
        title="Pertinencia académica, brechas y mercado laboral en una sola vista"
        subtitle="Vista ejecutiva construida con datos reales del warehouse, programas con microcurrículo cargado y recomendaciones laborales validadas."
      >
        <div className="flex flex-wrap gap-2">
          <a
            className="inline-flex items-center justify-center rounded-full border border-brand/15 bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand/90"
            href="#resumen"
          >
            Ver resumen
          </a>
          <a
            className="inline-flex items-center justify-center rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:border-brand/40 hover:text-brand"
            href="#mercado"
          >
            Ver mercado
          </a>
        </div>
      </PageHero>

      <nav className="flex flex-wrap gap-2 rounded-2xl border border-line bg-white p-3 shadow-sm">
        {sections.map((section) => (
          <a
            key={section.id}
            className="rounded-full border border-line bg-slate-50 px-4 py-2 text-sm font-semibold text-ink transition hover:border-brand/40 hover:text-brand"
            href={`#${section.id}`}
          >
            {section.label}
          </a>
        ))}
      </nav>

      <section id="resumen" className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="space-y-5">
          <SectionCard title="Resumen ejecutivo" subtitle="KPIs reales del warehouse y del observatorio para lectura rápida de la operación.">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard
                label="Empleos capturados"
                value={marketState.dashboardKpis?.total_empleos ?? marketState.jobs.length}
                detail="Vacantes reales cargadas desde el warehouse."
              />
              <MetricCard label="Empresas" value={companyCount} detail="Empresas detectadas en vacantes reales." />
              <MetricCard
                label="Skills"
                value={marketState.dashboardKpis?.total_skills_mercado ?? jobSkillUniverse}
                detail="Skills canónicas observadas en mercado real."
              />
              <MetricCard label="Programas" value={visiblePrograms.length} detail="Programas visibles en el universo vigente del backend." />
              <MetricCard label="Recomendaciones" value={recommendationCount} detail="Recomendaciones curriculares y laborales vigentes." />
            </div>
          </SectionCard>

          <SectionCard title="Ranking de programas" subtitle="Solo programas con microcurrículo procesado.">
            <ProgramObservatoryCards
              programs={visiblePrograms.slice().sort((a, b) => b.promedio_match_mercado - a.promedio_match_mercado).slice(0, 5)}
              selectedProgramId={selectedProgramId}
              onSelectProgram={setSelectedProgramId}
              onViewFullRanking={() => {
                document.getElementById('pertinencia')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            />
          </SectionCard>
        </div>

        <ProgramSelectorStrip
          programs={visiblePrograms}
          selectedProgramId={selectedProgramId ?? visiblePrograms[0]?.especializacion_id ?? null}
          onChange={setSelectedProgramId}
          hasEvidence={Boolean(selectedProgramState.programDashboard?.program?.microcurriculum_context || selectedProgram?.microcurriculum_context)}
          domainLabel={selectedProgramDomain.domainLabel}
          subdomainLabel={selectedProgramDomain.subdomainLabel}
          benchmarkLabel={selectedProgramDomain.benchmarkLabel}
          note="El dashboard consume el universo visible del backend y usa el detalle del programa seleccionado para enriquecer la lectura."
          helper="Selecciona una especialización para recalcular pertinencia, recomendaciones y brechas desde el matching validado."
          primaryActionLabel="Abrir detalle del programa"
          primaryActionHref={selectedProgramId ? `/programas/${selectedProgramId}` : undefined}
          secondaryActionLabel="Abrir microcurrículo"
          secondaryActionHref={selectedProgramId ? `/programs/${selectedProgramId}/microcurriculum` : undefined}
        />
      </section>

      <section id="pertinencia" className="scroll-mt-24">
        <SectionCard title="Pertinencia académica" subtitle="Alineación, brecha y cobertura para programas con microcurrículo cargado.">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Alignment score" value={formatPercent(selectedAlignmentScore)} detail="Score de alineación laboral-académica validado." />
            <MetricCard label="Coverage score" value={formatPercent(selectedCoverageScore)} detail="Cobertura observada frente a la demanda real." />
            <MetricCard label="Gap score" value={formatPercent(selectedGapScore)} detail="Brecha residual después del matching disciplinar." />
            <MetricCard label="Skills críticas" value={selectedMissingCriticalSkills} detail="Skills ausentes o de prioridad alta para intervención." />
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
            <div className="rounded-2xl border border-line bg-slate-50 p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-xl border border-line bg-white px-3 py-2">
                  <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-muted">Estado curricular</span>
                  <strong className="mt-1 block text-sm text-ink">{selectedStatus?.curricular_status || 'Sin dato'}</strong>
                </div>
                <div className="rounded-xl border border-line bg-white px-3 py-2">
                  <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-muted">Señal IA</span>
                  <strong className="mt-1 block text-sm text-ink">{selectedStatus?.ai_signal || 'Sin señal'}</strong>
                </div>
                <div className="rounded-xl border border-line bg-white px-3 py-2">
                  <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-muted">Tendencia</span>
                  <strong className="mt-1 block text-sm text-ink">{selectedStatus?.trend_label || 'Sin tendencia'}</strong>
                </div>
                <div className="rounded-xl border border-line bg-white px-3 py-2">
                  <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-muted">Actualización</span>
                  <strong className="mt-1 block text-sm text-ink">{selectedKpis?.curricular_update_signal || 'Sin dato'}</strong>
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted">
                {selectedStatus?.curricular_status_detail || selectedInsights?.detected || 'Seleccione un programa con microcurrículo procesado para ver la evidencia.'}
              </p>
            </div>

            <DataTable
              title="Programas priorizados"
              subtitle="Resumen comparativo de programas con evidencia curricular real."
              columns={['Programa', 'Alignment', 'Coverage', 'Gap', 'Brechas', 'Fuente']}
              rows={visiblePrograms
                .slice()
                .sort((left, right) => Number(right.promedio_match_mercado || 0) - Number(left.promedio_match_mercado || 0))
                .slice(0, 10)
                .map((program) => [
                  program.nombre_especializacion,
                  formatPercent(Number(program.promedio_match_mercado || 0)),
                  formatPercent(Math.max(0, Number(program.promedio_match_mercado || 0))),
                  formatPercent(Math.max(0, 100 - Number(program.promedio_match_mercado || 0))),
                  Number(program.total_empleos_relacionados || 0),
                  program.microcurriculum_context ? 'microcurriculum_context' : 'programas',
                ])}
              empty={<EmptyDiagnostic title="No hay programas visibles." cause="El observatorio no devolvió programas en /api/programas." endpoint="/api/programas" action="Revise la respuesta del backend activo." />}
            />
          </div>
        </SectionCard>
      </section>

      <section id="recomendaciones" className="scroll-mt-24">
        <SectionCard title="Recomendaciones" subtitle="Empleos recomendados para el programa seleccionado usando el matching ya validado.">
          {selectedProgramState.isLoading ? (
            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-muted">
              Actualizando el detalle del programa seleccionado con datos reales.
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Programa" value={selectedProgramName} detail="Programa activo en el selector del dashboard." />
            <MetricCard label="Match promedio" value={formatPercent(selectedAlignmentScore)} detail="Score base utilizado por el ranking de recomendaciones." />
            <MetricCard label="Recomendaciones" value={selectedRecommendationRows.length} detail="Vacantes visibles en el set de recomendaciones actual." />
            <MetricCard label="Fuentes relacionadas" value={selectedProgramDashboard?.source ? 1 : 0} detail="Endpoint real consultado para este programa." />
          </div>

          <div className="mt-5">
            <DataTable
              title="Recomendaciones laborales"
              subtitle="Programa, empleo, empresa y score de match."
              columns={['Programa', 'Empleo', 'Empresa', 'Match score', 'Skills en común']}
              rows={selectedRecommendationRows}
              empty={<EmptyDiagnostic title="No hay recomendaciones laborales disponibles." cause="El programa activo aún no devuelve recomendaciones en el set seleccionado." endpoint={`/api/programas/${selectedProgramId || '{programId}'}/recommended-jobs`} action="Revise el programa seleccionado o la evidencia laboral asociada." />}
            />
          </div>
        </SectionCard>
      </section>

      <section id="brechas" className="scroll-mt-24">
        <SectionCard title="Brechas" subtitle="Skills faltantes consolidadas para el programa activo.">
          {selectedProgramState.isLoading ? (
            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-muted">
              Actualizando brechas del programa seleccionado.
            </div>
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
            <DataTable
              title="Brechas del programa seleccionado"
              subtitle="Salida directa del motor de pertinencia para el programa activo."
              columns={['Skill faltante', 'Frecuencia', 'Programa']}
              rows={selectedGapRows}
              empty={<EmptyDiagnostic title="No hay brechas seleccionadas para este programa." cause="El programa activo no reportó skills faltantes en el payload actual." endpoint={`/api/programas/${selectedProgramId || '{programId}'}/skill-gaps`} action="Seleccione otro programa con microcurrículo cargado." />}
            />

            <div className="rounded-2xl border border-line bg-slate-50 p-4">
              <h3 className="text-lg font-semibold text-ink">Información del programa</h3>
              <p className="mt-2 text-sm leading-6 text-muted">
                {selectedProgramDashboard?.insights?.detected || 'La vista usa endpoints reales del backend activo: programas, empleos, matches y market alignment.'}
              </p>
              {selectedProgramDashboard?.insights?.ai_recommends?.length ? (
                <ul className="mt-4 space-y-2 text-sm text-ink">
                  {selectedProgramDashboard.insights.ai_recommends.slice(0, 5).map((item) => (
                    <li key={item} className="rounded-xl border border-line bg-white px-3 py-2">
                      {item}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </div>
        </SectionCard>
      </section>

      <section id="mercado" className="scroll-mt-24">
        <SectionCard title="Mercado laboral" subtitle="Señales reales de skills, empresas y cargos observados en empleos y matches.">
          <div className="grid gap-5 xl:grid-cols-3">
            <MarketSeriesCard
              title="Top skills"
              subtitle="Skills con mayor presencia en vacantes reales."
              items={topSkillSignals}
              color="#005EB8"
              emptyTitle="No hay top skills visibles."
              emptyBody="Valide la carga de empleos y skills reales."
            />
            <MarketSeriesCard
              title="Top empresas"
              subtitle="Empresas detectadas en vacantes reales."
              items={topCompanySignals}
              color="#0f766e"
              emptyTitle="No hay empresas visibles."
              emptyBody="Valide la carga de empleos y el warehouse."
            />
            <MarketSeriesCard
              title="Top cargos"
              subtitle="Roles observados en vacantes y matches."
              items={topRoleSignals}
              color="#7c3aed"
              emptyTitle="No hay cargos visibles."
              emptyBody="Valide la carga laboral y el set de matches."
            />
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <DataTable
              title="Skills"
              subtitle="Señales reales de skills en vacantes."
              columns={['Skill', 'Presencia', 'Fuente']}
              rows={topSkillSignals.map((item) => [item.entity_name, item.horizon_months || 0, 'api/empleos'])}
              empty={<EmptyDiagnostic title="No hay skills de mercado visibles." cause="El observatorio no expuso top skills para esta sesión." endpoint="/api/empleos" action="Revise la carga de jobs." />}
            />
            <DataTable
              title="Empresas"
              subtitle="Señales reales de empresas en vacantes."
              columns={['Empresa', 'Presencia', 'Fuente']}
              rows={topCompanySignals.map((item) => [item.entity_name, item.horizon_months || 0, 'api/empleos'])}
              empty={<EmptyDiagnostic title="No hay empresas de mercado visibles." cause="El observatorio no expuso top companies para esta sesión." endpoint="/api/empleos" action="Revise la carga de jobs." />}
            />
            <DataTable
              title="Cargos"
              subtitle="Señales reales de cargos en vacantes y matches."
              columns={['Cargo', 'Presencia', 'Fuente']}
              rows={topRoleSignals.map((item) => [item.entity_name, item.horizon_months || 0, 'api/matches'])}
              empty={<EmptyDiagnostic title="No hay cargos de mercado visibles." cause="El observatorio no expuso top roles para esta sesión." endpoint="/api/matches" action="Revise la carga de jobs y matches." />}
            />
          </div>
        </SectionCard>
      </section>
    </div>
  );
}
