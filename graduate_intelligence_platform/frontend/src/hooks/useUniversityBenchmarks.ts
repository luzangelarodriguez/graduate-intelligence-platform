import { useEffect, useState } from 'react';
import { getRelatedUniversityPrograms } from '../services/api';
import type { Page, RelatedUniversityProgram } from '../types/api';

interface UniversityBenchmarksData {
  programs: RelatedUniversityProgram[];
  isLoading: boolean;
  error: Error | null;
}

export function useUniversityBenchmarks(programId: number | null, limit = 10) {
  const [data, setData] = useState<UniversityBenchmarksData>({
    programs: [],
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    if (!programId) {
      setData({ programs: [], isLoading: false, error: null });
      return;
    }

    const fetchData = async () => {
      setData({ programs: [], isLoading: true, error: null });
      try {
        const result: Page<RelatedUniversityProgram> = await getRelatedUniversityPrograms(programId, limit);
        setData({
          programs: result.items || [],
          isLoading: false,
          error: null,
        });
      } catch (error) {
        setData({
          programs: [],
          isLoading: false,
          error: error instanceof Error ? error : new Error('Unknown error'),
        });
      }
    };

    fetchData();
  }, [programId, limit]);

  return data;
}
