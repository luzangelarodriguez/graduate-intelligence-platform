import { useEffect, useMemo, useState } from 'react';

import { getDataQualitySnapshot, type DataQualityRow } from '../services/dataQualityService';
import { laborMarketService } from '../services/laborMarketService';
import { programService } from '../services/programService';
import { recommendationService } from '../services/recommendationService';
import { skillsService } from '../services/skillsService';
import type {
  CompanyIntelligenceItem,
  EmergingSkillSignal,
  ExecutiveObservatoryResponse,
  ForecastSummaryResponse,
  Job,
  MarketForecastItem,
  Match,
  Page,
  Program,
  ProgramIntelligenceItem,
  RecommendationV2,
} from '../types/api';

function itemsOf<T>(value: unknown): T[] {
  if (value && typeof value === 'object' && Array.isArray((value as Page<T>).items)) {
    return (value as Page<T>).items;
  }
  return [];
}

function asExecutive(value: unknown): ExecutiveObservatoryResponse | null {
  return value && typeof value === 'object' ? (value as ExecutiveObservatoryResponse) : null;
}

function asForecastSummary(value: unknown): ForecastSummaryResponse | null {
  return value && typeof value === 'object' ? (value as ForecastSummaryResponse) : null;
}

export interface InstitutionalSnapshot {
  programs: Program[];
  programIntelligence: ProgramIntelligenceItem[];
  jobs: Job[];
  matches: Match[];
  emergingSkills: EmergingSkillSignal[];
  companies: CompanyIntelligenceItem[];
  marketForecast: MarketForecastItem[];
  forecastSummary: ForecastSummaryResponse | null;
  recommendations: RecommendationV2[];
  executiveObservatory: ExecutiveObservatoryResponse | null;
  qualityRows: DataQualityRow[];
  baseUrl: string;
  generatedAt: string;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useInstitutionalSnapshot(): InstitutionalSnapshot {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<Omit<InstitutionalSnapshot, 'refresh'>>({
    programs: [],
    programIntelligence: [],
    jobs: [],
    matches: [],
    emergingSkills: [],
    companies: [],
    marketForecast: [],
    forecastSummary: null,
    recommendations: [],
    executiveObservatory: null,
    qualityRows: [],
    baseUrl: '',
    generatedAt: '',
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState((current) => ({ ...current, isLoading: true, error: null }));
      try {
        const [
          programs,
          programIntelligence,
          jobs,
          matches,
          emergingSkills,
          companies,
          marketForecast,
          forecastSummary,
          recommendations,
          executiveObservatory,
          quality,
        ] = await Promise.all([
          programService.listPrograms(),
          programService.listProgramIntelligence(),
          laborMarketService.listJobs(),
          laborMarketService.listMatches(),
          skillsService.listEmergingSkills(),
          laborMarketService.listCompanies(),
          laborMarketService.listMarketForecast(),
          laborMarketService.getForecastSummary(),
          recommendationService.listRecommendations(),
          programService.getExecutiveObservatory(),
          getDataQualitySnapshot(),
        ]);

        if (cancelled) return;
        setState({
          programs: itemsOf<Program>(programs.data),
          programIntelligence: itemsOf<ProgramIntelligenceItem>(programIntelligence.data),
          jobs: itemsOf<Job>(jobs.data),
          matches: itemsOf<Match>(matches.data),
          emergingSkills: itemsOf<EmergingSkillSignal>(emergingSkills.data),
          companies: itemsOf<CompanyIntelligenceItem>(companies.data),
          marketForecast: itemsOf<MarketForecastItem>(marketForecast.data),
          forecastSummary: asForecastSummary(forecastSummary.data),
          recommendations: itemsOf<RecommendationV2>(recommendations.data),
          executiveObservatory: asExecutive(executiveObservatory.data),
          qualityRows: quality.rows,
          baseUrl: quality.baseUrl,
          generatedAt: quality.generatedAt,
          isLoading: false,
          error: null,
        });
      } catch (cause) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            isLoading: false,
            error: cause instanceof Error ? cause.message : 'No fue posible cargar el snapshot institucional.',
          }));
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [version]);

  const refresh = useMemo(() => () => setVersion((current) => current + 1), []);

  return {
    ...state,
    refresh,
  };
}





