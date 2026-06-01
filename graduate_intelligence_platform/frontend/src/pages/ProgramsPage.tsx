import { useMemo, useState } from 'react';
import { ArrowUpRight, BarChart3, BriefcaseBusiness, GraduationCap, Layers3, ShieldAlert, Sparkles, Target, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { ProgramSelectorStrip } from '../components/program-intelligence/ProgramIntelligenceBlocks';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';
import { LoadingState } from '../components/LoadingState';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useDashboardData } from '../hooks/useDashboardData';
import type { Program } from '../types/api';
import { ObservatoryHeader } from '../components/programs-observatory/ObservatoryHeader';
import { ProgramSelectorPanel } from '../components/programs-observatory/ProgramSelectorPanel';
import { ProgramDetailPanel } from '../components/programs-observatory/ProgramDetailPanel';
import { UniversityBenchmarkPanel } from '../components/programs-observatory/UniversityBenchmarkPanel';
import { MarketIntelligencePanel } from '../components/programs-observatory/MarketIntelligencePanel';

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
    const topGap = alignment >= 70 ? 'Brecha contenida con evidencia de monitoreo' : 'Cobertura curricular con presiÃ³n de actualizaciÃ³n';
    const topRecommendation = alignment >= 70 ? 'Mantener vigilancia y actualizar con seÃ±ales emergentes.' : 'Priorizar actualizaciÃ³n curricular y trazabilidad con mercado.';
    const forecastSignal = program.total_empleos_relacionados > 0 ? `${program.total_empleos_relacionados} seÃ±ales laborales relacionadas` : 'Sin seÃ±al laboral consolidada';

    return {
      id: program.especializacion_id,
      name: program.nombre_especializacion,
      area: program.rol || 'Ãrea acadÃ©mica no disponible en la fuente actual',
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
          <span className="block text-xs uppercase tracking-[0.12em] text-muted">AlineaciÃ³n</span>
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
          <strong className="font-semibold">AcciÃ³n prioritaria:</strong> {program.topRecommendation}
        </p>
        <p className="text-sm leading-6 text-muted">
          <strong className="font-semibold text-ink">SeÃ±al de forecast:</strong> {program.forecastSignal}
        </p>
      </div>
    </Link>
  );
}

export function ProgramsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  
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

  if (isLoading) return <LoadingState label="Cargando inteligencia de programas..." />;
  if (!rankedPrograms.length) return <EmptyState title="Sin programas analizados" body={error || 'No se encontró información suficiente para construir el ranking ejecutivo.'} />;

  // Get selected program's gap and recommendation
  const selectedProgramRanked = rankedPrograms.find(p => p.id === selectedProgramId);
  const topGap = selectedProgramRanked?.topGap || 'Análisis pendiente';
  const topRecommendation = selectedProgramRanked?.topRecommendation || 'Monitoreo continuo recomendado';

  if (isLoading) return <LoadingState label="Cargando inteligencia de programas..." />;
  if (!rankedPrograms.length) return <EmptyState title="Sin programas analizados" body={error || 'No se encontró información suficiente para construir el ranking ejecutivo.'} />;

  return (
    <section className="space-y-8 p-6">
      {/* Observatory Header */}
      <ObservatoryHeader
        totalPrograms={analyzedPrograms}
        averageAlignment={averageAlignment}
        criticalCount={criticalPrograms.length}
        opportunityCount={opportunityPrograms.length}
      />

      {/* Main Content Grid: Left (Selector + Detail) and Right (Benchmarks + Intelligence) */}
      <div className="grid grid-cols-4 gap-6">
        {/* Left Column */}
        <div className="col-span-2 space-y-6">
          {/* Program Selector */}
          <ProgramSelectorPanel
            programs={programs}
            selectedProgramId={selectedProgramId ?? null}
            onSelectProgram={setSelectedProgramId}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />

          {/* Program Detail Panel */}
          <ProgramDetailPanel
            program={selectedProgram ?? null}
            alignment={selectedProgramAlignment}
            risk={selectedProgramRisk}
            employability={selectedProgramEmployability}
            gapCount={selectedProgramRanked?.gapCount || 0}
            topGap={topGap}
            topRecommendation={topRecommendation}
            forecastSignal={selectedProgramRanked?.forecastSignal || 'Sin señal'}
          />
        </div>

        {/* Right Column */}
        <div className="col-span-2 space-y-6">
          {/* University Benchmarks */}
          <UniversityBenchmarkPanel
            selectedProgram={selectedProgram ?? null}
            relatedUniversityPrograms={relatedUniversityPrograms}
            alignment={selectedProgramAlignment}
          />

          {/* Market Intelligence */}
          <MarketIntelligencePanel
            selectedProgram={selectedProgram ?? null}
            topGap={topGap}
            topRecommendation={topRecommendation}
          />
        </div>
      </div>

      {/* Executive AI Section */}
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-6">
        <ExecutiveAiSection
          title="Program Analysis with AI"
          subtitle="The AI layer summarizes the selected program with curriculum evidence, labor signals, and executive insights."
          body={
            programExecutiveNarrative?.narrative ||
            programExecutiveNarrative?.why_at_risk ||
            'Executive analysis pending sufficient data. Select a program for contextual explanation.'
          }
          evidenceSources={programExecutiveNarrative?.evidence_sources}
          confidence={programExecutiveNarrative?.confidence}
          model={programExecutiveNarrative?.model}
          loading={executiveAiLoading}
          error={executiveAiError}
          emptyTitle="Unable to load executive analysis"
          emptyBody="The program explanation is not yet available, but the ranking remains operational."
          badgeLabel="Program AI"
        />
      </div>

      {/* Legacy Ranking Cards - Optional */}
      {opportunityPrograms.length > 0 && (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Opportunity Programs</h3>
            <p className="text-sm text-slate-600 mt-1">High-alignment programs ready for strategic positioning</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {opportunityPrograms.map((program) => (
              <RankingCard key={program.id} program={program} tone="opportunity" />
            ))}
          </div>
        </div>
      )}

      {criticalPrograms.length > 0 && (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Programs Requiring Attention</h3>
            <p className="text-sm text-slate-600 mt-1">Critical programs with high risk factors requiring immediate curriculum review</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {criticalPrograms.map((program) => (
              <RankingCard key={program.id} program={program} tone="critical" />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
