import { useCallback, useEffect, useState } from 'react';

import { getProgramas, getPrograma, getProgramDashboard } from '../services/api';
import type { Program, ProgramDashboardResponse } from '../types/api';

interface UseOfertaAcademicaResult {
  programs: Program[];
  selectedProgram: Program | null;
  programDashboard: ProgramDashboardResponse | null;
  selectedProgramId: number | null;
  setSelectedProgramId: (id: number | null) => void;
  isLoading: boolean;
  isProgramLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useOfertaAcademica(): UseOfertaAcademicaResult {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);
  const [programDashboard, setProgramDashboard] = useState<ProgramDashboardResponse | null>(null);
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProgramLoading, setIsProgramLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrograms = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getProgramas(100);
      setPrograms(response.items);
      
      // Auto-select first program if none selected
      if (response.items.length > 0 && !selectedProgramId) {
        setSelectedProgramId(response.items[0].especializacion_id);
      }
    } catch (err) {
      setError('No se pudieron cargar los programas academicos.');
      console.error('[v0] Oferta academica fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedProgramId]);

  const fetchProgramDetail = useCallback(async (programId: number) => {
    setIsProgramLoading(true);

    try {
      const [programRes, dashboardRes] = await Promise.allSettled([
        getPrograma(programId),
        getProgramDashboard(programId),
      ]);

      if (programRes.status === 'fulfilled') {
        setSelectedProgram(programRes.value);
      }
      if (dashboardRes.status === 'fulfilled') {
        setProgramDashboard(dashboardRes.value);
      }
    } catch (err) {
      console.error('[v0] Program detail fetch error:', err);
    } finally {
      setIsProgramLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrograms();
  }, [fetchPrograms]);

  useEffect(() => {
    if (selectedProgramId) {
      fetchProgramDetail(selectedProgramId);
    } else {
      setSelectedProgram(null);
      setProgramDashboard(null);
    }
  }, [selectedProgramId, fetchProgramDetail]);

  return {
    programs,
    selectedProgram,
    programDashboard,
    selectedProgramId,
    setSelectedProgramId,
    isLoading,
    isProgramLoading,
    error,
    refresh: fetchPrograms,
  };
}
