import { useCallback, useEffect, useState } from 'react';

import { getObservatoryRecommendations } from '../services/api';
import type { ObservatoryRecommendation } from '../types/api';

interface UseRecomendacionesResult {
  recommendations: ObservatoryRecommendation[];
  selectedType: string | null;
  setSelectedType: (type: string | null) => void;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useRecomendaciones(): UseRecomendacionesResult {
  const [recommendations, setRecommendations] = useState<ObservatoryRecommendation[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getObservatoryRecommendations({
        limit: 100,
        recommendation_type: selectedType || undefined,
      });
      setRecommendations(response.items);
    } catch (err) {
      setError('No se pudieron cargar las recomendaciones.');
      console.error('[v0] Recomendaciones fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    recommendations,
    selectedType,
    setSelectedType,
    isLoading,
    error,
    refresh: fetchData,
  };
}
