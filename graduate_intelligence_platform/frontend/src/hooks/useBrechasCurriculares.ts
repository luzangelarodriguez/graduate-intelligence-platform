import { useCallback, useEffect, useState } from 'react';

import { getCurriculumGaps, getProgramas } from '../services/api';
import type { CurriculumGap, Program } from '../types/api';

interface UseBrechasCurricularesResult {
  gaps: CurriculumGap[];
  programs: Program[];
  selectedSpecialization: string | null;
  setSelectedSpecialization: (id: string | null) => void;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useBrechasCurriculares(): UseBrechasCurricularesResult {
  const [gaps, setGaps] = useState<CurriculumGap[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedSpecialization, setSelectedSpecialization] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [gapsRes, programsRes] = await Promise.allSettled([
        getCurriculumGaps({
          limit: 100,
          specialization: selectedSpecialization || undefined,
        }),
        getProgramas(100),
      ]);

      if (gapsRes.status === 'fulfilled') {
        setGaps(gapsRes.value.items);
      }
      if (programsRes.status === 'fulfilled') {
        setPrograms(programsRes.value.items);
      }

      if (gapsRes.status === 'rejected' && programsRes.status === 'rejected') {
        setError('No se pudieron cargar los datos de brechas curriculares.');
      }
    } catch (err) {
      setError('Error al cargar los datos de brechas curriculares.');
      console.error('[v0] Brechas curriculares fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedSpecialization]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    gaps,
    programs,
    selectedSpecialization,
    setSelectedSpecialization,
    isLoading,
    error,
    refresh: fetchData,
  };
}
