import { useCallback, useEffect, useState } from 'react';

import {
  getCompanyIntelligence,
  getCurriculumGaps,
  getObservatoryHealth,
  getObservatoryMetrics,
  getObservatoryRecommendations,
  getPrograms,
} from '../services/api';
import type {
  CompanyIntelligence,
  CurriculumGap,
  HealthResponse,
  ObservatoryMetric,
  ObservatoryRecommendation,
  Program,
} from '../types/api';

interface DashboardKpis {
  totalPrograms: number;
  totalCompanies: number;
  totalRecommendations: number;
  totalGaps: number;
  avgMatchMercado: number;
  avgAiAdoption: number;
  avgCloudMaturity: number;
  avgBiMaturity: number;
}

interface UseObservatoryDashboardResult {
  metrics: ObservatoryMetric[];
  programs: Program[];
  companies: CompanyIntelligence[];
  recommendations: ObservatoryRecommendation[];
  gaps: CurriculumGap[];
  health: HealthResponse | null;
  kpis: DashboardKpis;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useObservatoryDashboard(): UseObservatoryDashboardResult {
  const [metrics, setMetrics] = useState<ObservatoryMetric[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [companies, setCompanies] = useState<CompanyIntelligence[]>([]);
  const [recommendations, setRecommendations] = useState<ObservatoryRecommendation[]>([]);
  const [gaps, setGaps] = useState<CurriculumGap[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [metricsRes, programsRes, companiesRes, recsRes, gapsRes, healthRes] = await Promise.allSettled([
        getObservatoryMetrics({ limit: 50 }),
        getPrograms({ limit: 100 }),
        getCompanyIntelligence({ limit: 50 }),
        getObservatoryRecommendations({ limit: 50 }),
        getCurriculumGaps({ limit: 50 }),
        getObservatoryHealth(),
      ]);

      if (metricsRes.status === 'fulfilled') {
        setMetrics(metricsRes.value.items);
      }
      if (programsRes.status === 'fulfilled') {
        setPrograms(programsRes.value.items);
      }
      if (companiesRes.status === 'fulfilled') {
        setCompanies(companiesRes.value.items);
      }
      if (recsRes.status === 'fulfilled') {
        setRecommendations(recsRes.value.items);
      }
      if (gapsRes.status === 'fulfilled') {
        setGaps(gapsRes.value.items);
      }
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
      }

      const allFailed = [metricsRes, programsRes, companiesRes, recsRes, gapsRes, healthRes].every(
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

  // Calculate KPIs from real data
  const kpis: DashboardKpis = {
    totalPrograms: programs.length,
    totalCompanies: companies.length,
    totalRecommendations: recommendations.length,
    totalGaps: gaps.length,
    avgMatchMercado: programs.length > 0
      ? programs.reduce((sum, p) => sum + (p.promedio_match_mercado || 0), 0) / programs.length
      : 0,
    avgAiAdoption: companies.length > 0
      ? companies.reduce((sum, c) => sum + (parseFloat(c.ai_adoption_score) || 0), 0) / companies.length
      : 0,
    avgCloudMaturity: companies.length > 0
      ? companies.reduce((sum, c) => sum + (parseFloat(c.cloud_maturity_score) || 0), 0) / companies.length
      : 0,
    avgBiMaturity: companies.length > 0
      ? companies.reduce((sum, c) => sum + (parseFloat(c.bi_maturity_score) || 0), 0) / companies.length
      : 0,
  };

  return {
    metrics,
    programs,
    companies,
    recommendations,
    gaps,
    health,
    kpis,
    isLoading,
    error,
    refresh: fetchData,
  };
}
