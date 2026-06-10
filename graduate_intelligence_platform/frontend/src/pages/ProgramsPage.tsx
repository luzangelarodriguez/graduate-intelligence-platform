import { useMemo, useState } from 'react';
import { GraduationCap, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { ExecutiveAiSection } from '../components/executive-ai/ExecutiveAiSection';
import { LoadingState } from '../components/LoadingState';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useDashboardData } from '../hooks/useDashboardData';
import type { Program } from '../types/api';

// Import new observatory components
import { ActiveProgramPanel } from '../components/programs-observatory/ActiveProgramPanel';
import { CurriculumVsMarketMatch } from '../components/programs-observatory/CurriculumVsMarketMatch';
import { UniversityBenchmarks } from '../components/programs-observatory/UniversityBenchmarks';
import { RelatedJobsPanel } from '../components/programs-observatory/RelatedJobsPanel';
import { MicrocurriculumModules } from '../components/programs-observatory/MicrocurriculumModules';
import { AIRecommendations } from '../components/programs-observatory/AIRecommendations';
import { SimulationDashboard } from '../components/programs-observatory/SimulationDashboard';
import { CriminologyValidation } from '../components/programs-observatory/CriminologyValidation';

// Import new observatory components
import { ActiveProgramPanel } from '../components/programs-observatory/ActiveProgramPanel';
import { CurriculumVsMarketMatch } from '../components/programs-observatory/CurriculumVsMarketMatch';
import { UniversityBenchmarks } from '../components/programs-observatory/UniversityBenchmarks';
import { RelatedJobsPanel } from '../components/programs-observatory/RelatedJobsPanel';
import { MicrocurriculumModules } from '../components/programs-observatory/MicrocurriculumModules';
import { AIRecommendations } from '../components/programs-observatory/AIRecommendations';
import { SimulationDashboard } from '../components/programs-observatory/SimulationDashboard';
import { CriminologyValidation } from '../components/programs-observatory/CriminologyValidation';

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

export function ProgramsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);

  const {
    programs,
    selectedProgram,
    programDashboard,
    matches,
    relatedUniversityPrograms,
    isLoading,
    error,
  } = useDashboardData();

  const {
    executiveNarrative,
    isLoading: executiveAiLoading,
  } = useExecutiveAi(selectedProgramId);

  const rankedPrograms = useMemo(() => buildRankedPrograms(programs), [programs]);

  // Calculate metrics
  const selectedProgramAlignment = Number(programDashboard?.kpis?.alignment_score ?? selectedProgram?.promedio_match_mercado ?? 0);
  const selectedProgramRisk = Math.max(0, 100 - selectedProgramAlignment);
  const selectedProgramEmployability = Math.max(0, 100 - selectedProgramRisk);

  // Check if selected program is Criminology (program_id=108)
  const isCriminologyProgram = selectedProgram?.especializacion_id === 108;

  if (isLoading) return <LoadingState label="Cargando inteligencia de programas..." />;
  if (!rankedPrograms.length) return <EmptyState title="Sin programas analizados" body={error || 'No se encontró información suficiente para construir el ranking ejecutivo.'} />;

  return (
    <section className="space-y-6 p-6">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <GraduationCap size={24} className="text-blue-600" />
          <h1 className="text-3xl font-bold text-slate-900">Programs Observatory</h1>
        </div>
        <p className="text-slate-600">
          Executive dashboard analyzing {rankedPrograms.length} academic programs with real labor market data and curriculum intelligence.
        </p>
      </div>

      {/* Program Selector */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block text-sm font-semibold text-slate-900 mb-3">Select a Program to Analyze</label>
        <select
          value={selectedProgramId ?? ''}
          onChange={(e) => setSelectedProgramId(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Choose a Program --</option>
          {programs.map((program) => (
            <option key={program.especializacion_id} value={program.especializacion_id}>
              {program.nombre_especializacion} ({program.rol})
            </option>
          ))}
        </select>
      </div>

      {selectedProgram && (
        <>
          {/* Section 1: Active Program Panel */}
          <ActiveProgramPanel
            program={selectedProgram}
            programId={selectedProgramId}
            onSelectProgram={() => setSelectedProgramId(null)}
          />

          {/* Section 2: Curriculum vs Market Match */}
          <CurriculumVsMarketMatch
            program={selectedProgram}
            programId={selectedProgramId}
          />

          {/* Section 3: University Benchmarks */}
          <UniversityBenchmarks programId={selectedProgramId} />

          {/* Section 4: Related Jobs Panel */}
          <RelatedJobsPanel programId={selectedProgramId} />

          {/* Section 5: Microcurriculum Modules */}
          <MicrocurriculumModules program={selectedProgram} />

          {/* Section 6: AI Recommendations */}
          <AIRecommendations programId={selectedProgramId} />

          {/* Section 7: Simulation Dashboard */}
          <SimulationDashboard programId={selectedProgramId} />

          {/* Section 8: Criminology Validation (if applicable) */}
          <CriminologyValidation program={selectedProgram} isCriminologyProgram={isCriminologyProgram} />

          {/* AI Analysis Section */}
          <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-6">
            <ExecutiveAiSection
              title="Program Analysis with AI"
              subtitle="The AI layer summarizes the selected program with curriculum evidence, labor signals, and executive insights."
              body={
                executiveNarrative?.narrative ||
                executiveNarrative?.why_at_risk ||
                'Executive analysis pending sufficient data. Select a program for contextual explanation.'
              }
              evidenceSources={executiveNarrative?.evidence_sources}
              confidence={executiveNarrative?.confidence}
              model={executiveNarrative?.model}
              loading={executiveAiLoading}
              emptyTitle="Unable to load executive analysis"
              emptyBody="The program explanation is not yet available, but the ranking remains operational."
              badgeLabel="Program AI"
            />
          </div>
        </>
      )}

      {/* Footer */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Sparkles size={18} className="text-blue-600" />
          <p className="text-sm font-semibold text-slate-900">8 Observable Sections</p>
        </div>
        <p className="text-xs text-slate-600">
          This observatory provides comprehensive program intelligence across active panel, curriculum analysis, competitive benchmarks, labor market alignment, microcurriculum coverage, AI recommendations, scenario simulation, and domain validation.
        </p>
      </div>
    </section>
  );
}
