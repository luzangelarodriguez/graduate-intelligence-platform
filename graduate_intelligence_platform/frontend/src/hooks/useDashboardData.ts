import { useEffect, useMemo, useState } from 'react';

import { getProgramDashboard, getProgramIntelligence, getProgramas, getRelatedUniversityPrograms } from '../services/api';
import type {
  Match,
  Program,
  ProgramDashboardResponse,
  ProgramIntelligenceItem,
  RecommendationProgram,
  RelatedUniversityProgram,
} from '../types/api';

interface DashboardState {
  programs: Program[];
  selectedProgram?: Program;
  programDashboard?: ProgramDashboardResponse;
  matches: Match[];
  recommendations: RecommendationProgram[];
  relatedUniversityPrograms: RelatedUniversityProgram[];
}

function mapProgramIntelligenceToProgram(item: ProgramIntelligenceItem): Program {
  const alignment = Number(item.alignment_score) || 0;
  const risk = Number(item.risk_score) || Math.max(0, 100 - alignment);
  const coveredSkills = Math.max(0, Math.round(alignment / 8));
  const totalSkills = Math.max(coveredSkills, item.gap_count + coveredSkills);

  return {
    especializacion_id: item.program_id,
    nombre_especializacion: item.program_name,
    rol: item.program_role,
    total_skills_programa: totalSkills,
    total_herramientas: Math.max(0, Math.min(coveredSkills, 6)),
    total_competencias: Math.max(0, item.gap_count + Math.ceil(coveredSkills / 2)),
    total_habilidades_blandas: Math.max(0, Math.min(4, Math.round(coveredSkills / 4))),
    promedio_match_mercado: alignment,
    porcentaje_match: alignment,
    max_match_mercado: Math.max(alignment, 100 - risk / 2),
    total_empleos_relacionados: item.forecast_signals.length,
    skills_cubiertas: coveredSkills,
    skills: [],
    microcurriculum_context: {
      source: 'program_intelligence',
      top_gaps: item.top_gaps,
      top_recommendations: item.top_recommendations,
      forecast_signals: item.forecast_signals,
      role_signals: item.role_signals,
      emerging_technologies: item.emerging_technologies,
    },
  };
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>({
    programs: [],
    matches: [],
    recommendations: [],
    relatedUniversityPrograms: [],
  });
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProgramLoading, setIsProgramLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      try {
        setIsLoading(true);
        const [programsResult, programIntelligenceResult] = await Promise.allSettled([
          getProgramas(100),
          getProgramIntelligence(100),
        ]);
        const programsPage = programsResult.status === 'fulfilled' ? programsResult.value : { items: [] as Program[] };
        const programIntelligenceItems = programIntelligenceResult.status === 'fulfilled' ? programIntelligenceResult.value.items : [];
        const fallbackPrograms =
          programsPage.items.length > 0
            ? programsPage.items
            : programIntelligenceItems.map(mapProgramIntelligenceToProgram);

        const preferred = fallbackPrograms.find((program) => program.total_empleos_relacionados > 0) ?? fallbackPrograms[0];
        if (cancelled) return;
        setSelectedProgramId(preferred?.especializacion_id ?? null);
        setState((current) => ({
          ...current,
          programs: fallbackPrograms,
        }));
        setError(programsPage.items.length || programIntelligenceItems.length ? null : 'No se pudo cargar inteligencia de programas.');
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'No fue posible cargar el observatorio.');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedProgramId) return;
    let cancelled = false;
    const programId = selectedProgramId;

    async function loadProgramContext() {
      try {
        setIsProgramLoading(true);
        setState((current) => ({
          ...current,
          selectedProgram: current.programs.find((program) => program.especializacion_id === programId),
          programDashboard: undefined,
          matches: [],
          recommendations: [],
          relatedUniversityPrograms: [],
        }));
        const [context, relatedPrograms] = await Promise.all([
          getProgramDashboard(programId),
          getRelatedUniversityPrograms(programId, 5),
        ]);
        if (cancelled) return;
        setState((current) => ({
          ...current,
          selectedProgram: context.program,
          programDashboard: context,
          matches: context.matches,
          recommendations: context.recommendations,
          relatedUniversityPrograms: relatedPrograms.items,
        }));
        setError(null);
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'No fue posible cargar el programa seleccionado.');
        }
      } finally {
        if (!cancelled) setIsProgramLoading(false);
      }
    }

    loadProgramContext();
    return () => {
      cancelled = true;
    };
  }, [selectedProgramId]);

  const topPrograms = useMemo(
    () =>
      [...state.programs]
        .sort((a, b) => b.promedio_match_mercado - a.promedio_match_mercado)
        .slice(0, 5),
    [state.programs],
  );

  return {
    ...state,
    topPrograms,
    selectedProgramId,
    setSelectedProgramId,
    isLoading,
    isProgramLoading,
    error,
  };
}
