import { useEffect, useState } from 'react';
import { getProgramSummary } from '../services/api';
import type { ProgramSummaryResponse } from '../types/api';

interface ProgramIntelligenceData {
  summary: ProgramSummaryResponse | null;
  isLoading: boolean;
  error: Error | null;
}

export function useProgramIntelligence(programId: number | null) {
  const [data, setData] = useState<ProgramIntelligenceData>({
    summary: null,
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    if (!programId) {
      setData({ summary: null, isLoading: false, error: null });
      return;
    }

    const fetchData = async () => {
      setData({ summary: null, isLoading: true, error: null });
      try {
        const summary = await getProgramSummary(programId);
        setData({ summary, isLoading: false, error: null });
      } catch (error) {
        setData({
          summary: null,
          isLoading: false,
          error: error instanceof Error ? error : new Error('Unknown error'),
        });
      }
    };

    fetchData();
  }, [programId]);

  return data;
}
