import { useEffect, useState } from 'react';
import { getRecommendationsV2 } from '../services/api';
import type { Page, RecommendationV2 } from '../types/api';

interface ProgramRecommendationsData {
  recommendations: RecommendationV2[];
  isLoading: boolean;
  error: Error | null;
}

export function useProgramRecommendations(programId: number | null, limit = 12) {
  const [data, setData] = useState<ProgramRecommendationsData>({
    recommendations: [],
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    if (!programId) {
      setData({ recommendations: [], isLoading: false, error: null });
      return;
    }

    const fetchData = async () => {
      setData({ recommendations: [], isLoading: true, error: null });
      try {
        const result: Page<RecommendationV2> = await getRecommendationsV2(programId, limit);
        setData({
          recommendations: result.items || [],
          isLoading: false,
          error: null,
        });
      } catch (error) {
        setData({
          recommendations: [],
          isLoading: false,
          error: error instanceof Error ? error : new Error('Unknown error'),
        });
      }
    };

    fetchData();
  }, [programId, limit]);

  return data;
}
