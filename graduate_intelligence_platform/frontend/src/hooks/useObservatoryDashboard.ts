import { useCallback, useEffect, useState } from 'react';

import {
  getCompanyIntelligence,
  getEmergingSkills,
  getObservatoryHealth,
  getObservatoryMetrics,
} from '../services/api';
import type {
  CompanyIntelligence,
  EmergingSkill,
  HealthResponse,
  ObservatoryMetric,
} from '../types/api';

interface UseObservatoryDashboardResult {
  metrics: ObservatoryMetric[];
  emergingSkills: EmergingSkill[];
  companies: CompanyIntelligence[];
  health: HealthResponse | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useObservatoryDashboard(): UseObservatoryDashboardResult {
  const [metrics, setMetrics] = useState<ObservatoryMetric[]>([]);
  const [emergingSkills, setEmergingSkills] = useState<EmergingSkill[]>([]);
  const [companies, setCompanies] = useState<CompanyIntelligence[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [metricsRes, skillsRes, companiesRes, healthRes] = await Promise.allSettled([
        getObservatoryMetrics({ limit: 50 }),
        getEmergingSkills({ limit: 20 }),
        getCompanyIntelligence({ limit: 15 }),
        getObservatoryHealth(),
      ]);

      if (metricsRes.status === 'fulfilled') {
        setMetrics(metricsRes.value.items);
      }
      if (skillsRes.status === 'fulfilled') {
        setEmergingSkills(skillsRes.value.items);
      }
      if (companiesRes.status === 'fulfilled') {
        setCompanies(companiesRes.value.items);
      }
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
      }

      // Check if all requests failed
      const allFailed = [metricsRes, skillsRes, companiesRes, healthRes].every(
        (r) => r.status === 'rejected'
      );
      if (allFailed) {
        setError('No se pudo conectar con el observatorio. Verifique la configuracion de la API.');
      }
    } catch (err) {
      setError('Error al cargar los datos del observatorio.');
      console.error('[v0] Observatory dashboard fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    metrics,
    emergingSkills,
    companies,
    health,
    isLoading,
    error,
    refresh: fetchData,
  };
}
