import { useEffect, useState } from 'react';
import { getCurriculumSimulator } from '../services/api';
import type { CurriculumSimulationResponse } from '../types/api';

interface ProgramSimulationData {
  simulation: CurriculumSimulationResponse | null;
  isLoading: boolean;
  error: Error | null;
}

export function useProgramSimulation(programId: number | null, proposedSkills: string[] = [], horizonMonths = 12) {
  const [data, setData] = useState<ProgramSimulationData>({
    simulation: null,
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    if (!programId) {
      setData({ simulation: null, isLoading: false, error: null });
      return;
    }

    const fetchData = async () => {
      setData({ simulation: null, isLoading: true, error: null });
      try {
        const simulation = await getCurriculumSimulator(programId, proposedSkills, horizonMonths);
        setData({ simulation, isLoading: false, error: null });
      } catch (error) {
        setData({
          simulation: null,
          isLoading: false,
          error: error instanceof Error ? error : new Error('Unknown error'),
        });
      }
    };

    fetchData();
  }, [programId, proposedSkills, horizonMonths]);

  return data;
}
