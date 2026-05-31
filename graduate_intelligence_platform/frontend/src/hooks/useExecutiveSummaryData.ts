import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getCompanyIntelligence,
  getEmergingSkills,
  getExecutiveObservatory,
  getMarketForecast,
  getProgramIntelligence,
  getProgramas,
  getRecommendationsV2,
} from '../services/api';
import type {
  CompanyIntelligenceItem,
  EmergingSkillSignal,
  ExecutiveObservatoryResponse,
  MarketForecastItem,
  Program,
  ProgramIntelligenceItem,
  RecommendationV2,
} from '../types/api';

export interface ExecutiveSummaryData {
  executiveObservatory: ExecutiveObservatoryResponse | null;
  programs: Program[];
  programIntelligence: ProgramIntelligenceItem[];
  recommendations: RecommendationV2[];
  emergingSkills: EmergingSkillSignal[];
  companies: CompanyIntelligenceItem[];
  forecasts: MarketForecastItem[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

interface ExecutiveSummaryState {
  executiveObservatory: ExecutiveObservatoryResponse | null;
  programs: Program[];
  programIntelligence: ProgramIntelligenceItem[];
  recommendations: RecommendationV2[];
  emergingSkills: EmergingSkillSignal[];
  companies: CompanyIntelligenceItem[];
  forecasts: MarketForecastItem[];
}

function stringifyError(message: string, failures: string[]) {
  if (!failures.length) return null;
  const suffix = failures.length === 1 ? `Fuente no disponible: ${failures[0]}.` : `Fuentes no disponibles: ${failures.join(', ')}.`;
  return message ? `${message} ${suffix}` : suffix;
}

export function useExecutiveSummaryData(): ExecutiveSummaryData {
  const [state, setState] = useState<ExecutiveSummaryState>({
    executiveObservatory: null,
    programs: [],
    programIntelligence: [],
    recommendations: [],
    emergingSkills: [],
    companies: [],
    forecasts: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    const results = await Promise.allSettled([
      getExecutiveObservatory(),
      getProgramIntelligence(100),
      getProgramas(100),
      getRecommendationsV2(undefined, 12),
      getEmergingSkills(12),
      getCompanyIntelligence(12),
      getMarketForecast(12),
    ]);

    const [
      executiveObservatoryResult,
      programIntelligenceResult,
      programsResult,
      recommendationsResult,
      emergingSkillsResult,
      companiesResult,
      forecastsResult,
    ] = results;

    const failures = [
      executiveObservatoryResult.status === 'rejected' ? 'executive-observatory' : '',
      programIntelligenceResult.status === 'rejected' ? 'program-intelligence' : '',
      programsResult.status === 'rejected' ? 'api/programas' : '',
      recommendationsResult.status === 'rejected' ? 'recommendations-v2' : '',
      emergingSkillsResult.status === 'rejected' ? 'emerging-skills' : '',
      companiesResult.status === 'rejected' ? 'company-intelligence' : '',
      forecastsResult.status === 'rejected' ? 'market-forecast' : '',
    ].filter(Boolean);

    setState({
      executiveObservatory: executiveObservatoryResult.status === 'fulfilled' ? executiveObservatoryResult.value : null,
      programIntelligence: programIntelligenceResult.status === 'fulfilled' ? programIntelligenceResult.value.items : [],
      programs: programsResult.status === 'fulfilled' ? programsResult.value.items : [],
      recommendations: recommendationsResult.status === 'fulfilled' ? recommendationsResult.value.items : [],
      emergingSkills: emergingSkillsResult.status === 'fulfilled' ? emergingSkillsResult.value.items : [],
      companies: companiesResult.status === 'fulfilled' ? companiesResult.value.items : [],
      forecasts: forecastsResult.status === 'fulfilled' ? forecastsResult.value.items : [],
    });

    const coreFailures = [
      executiveObservatoryResult.status === 'rejected' ? 'executive-observatory' : '',
      programIntelligenceResult.status === 'rejected' ? 'program-intelligence' : '',
      programsResult.status === 'rejected' ? 'api/programas' : '',
    ].filter(Boolean);
    setError(coreFailures.length >= 2 ? stringifyError('', failures) : null);

    setIsLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = useMemo(() => load, [load]);

  return {
    ...state,
    isLoading,
    error,
    refresh,
  };
}
