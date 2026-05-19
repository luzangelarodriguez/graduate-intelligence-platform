import { useEffect, useMemo, useState } from 'react';

import { getProgramDashboard, getProgramas, getRelatedUniversityPrograms } from '../services/api';
import type { Match, Program, ProgramDashboardResponse, RecommendationProgram, RelatedUniversityProgram } from '../types/api';

interface DashboardState {
  programs: Program[];
  selectedProgram?: Program;
  programDashboard?: ProgramDashboardResponse;
  matches: Match[];
  recommendations: RecommendationProgram[];
  relatedUniversityPrograms: RelatedUniversityProgram[];
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
        const programsPage = await getProgramas(100);
        const preferred = programsPage.items.find((program) => program.total_empleos_relacionados > 0) ?? programsPage.items[0];
        if (cancelled) return;
        setSelectedProgramId(preferred?.especializacion_id ?? null);
        setState((current) => ({
          ...current,
          programs: programsPage.items,
        }));
        setError(null);
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
