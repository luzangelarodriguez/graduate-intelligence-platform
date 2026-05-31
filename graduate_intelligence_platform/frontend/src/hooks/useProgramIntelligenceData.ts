import { useEffect, useMemo, useState } from 'react';

import {
  getCriticalPrograms,
  getCurriculumRisk,
  getCurriculumSimulator,
  getExecutiveObservatory,
  getForecastSummary,
  getProgramAlignment,
  getProgramIntelligenceDetail,
  getPrograma,
} from '../services/api';
import type {
  CriticalProgramItem,
  CurriculumRiskResponse,
  CurriculumSimulationResponse,
  ExecutiveObservatoryResponse,
  ForecastSummaryResponse,
  Program,
  ProgramIntelligenceItem,
  UniversityMarketAlignmentResponse,
} from '../types/api';

interface ProgramIntelligenceDataState {
  program?: Program;
  programIntelligence?: ProgramIntelligenceItem;
  curriculumRisk?: CurriculumRiskResponse;
  alignment?: UniversityMarketAlignmentResponse;
  forecastSummary?: ForecastSummaryResponse;
  executiveObservatory?: ExecutiveObservatoryResponse;
  criticalPrograms: CriticalProgramItem[];
}

interface UseProgramIntelligenceDataResult extends ProgramIntelligenceDataState {
  isLoading: boolean;
  error: string | null;
  suggestedSkills: string[];
}

interface UseProgramSimulationsResult {
  simulations: Record<number, CurriculumSimulationResponse>;
  isLoading: boolean;
  error: string | null;
}

function normalizeText(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function uniqueStrings(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    const key = normalizeText(trimmed);
    if (seen.has(key)) return;
    seen.add(key);
    result.push(trimmed);
  });
  return result;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function extractString(value: unknown): string[] {
  if (value == null) return [];
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed ? [trimmed] : [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => extractString(item));
  }
  const record = asRecord(value);
  if (!record) return [];
  const candidates: unknown[] = [
    record.skill,
    record.skills,
    record.missing_skill,
    record.canonical_skill,
    record.canonical_skill_name,
    record.nombre,
    record.name,
    record.title,
    record.target_entity,
    record.recommended_skill,
  ];
  if (Array.isArray(record.recommended_skills)) candidates.push(record.recommended_skills);
  if (Array.isArray(record.top_skills)) candidates.push(record.top_skills);
  if (Array.isArray(record.missing_skills)) candidates.push(record.missing_skills);
  return candidates.flatMap((candidate) => extractString(candidate));
}

function extractRecommendationSkills(item: unknown): string[] {
  const record = asRecord(item);
  if (!record) return [];
  const candidates: string[] = [];
  if (Array.isArray(record.recommended_skills)) {
    candidates.push(...record.recommended_skills.flatMap((value) => extractString(value)));
  }
  candidates.push(...extractString(record.skill));
  candidates.push(...extractString(record.missing_skill));
  candidates.push(...extractString(record.canonical_skill));
  candidates.push(...extractString(record.canonical_skill_name));
  candidates.push(...extractString(record.name));
  candidates.push(...extractString(record.title));
  return candidates;
}

export function useProgramIntelligenceData(programId: number | null) {
  const [state, setState] = useState<ProgramIntelligenceDataState>({
    criticalPrograms: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!programId) {
      setState({ criticalPrograms: [] });
      setError('No se encontró el programa solicitado.');
      setIsLoading(false);
      return;
    }

    const currentProgramId = programId;
    let cancelled = false;

    async function load() {
      try {
        setIsLoading(true);
        const [program, programIntelligence, curriculumRisk, alignment, forecastSummary, executiveObservatory, criticalPrograms] =
          await Promise.all([
            getPrograma(currentProgramId),
            getProgramIntelligenceDetail(currentProgramId),
            getCurriculumRisk(currentProgramId),
            getProgramAlignment(currentProgramId),
            getForecastSummary(25),
            getExecutiveObservatory(),
            getCriticalPrograms(12, 12),
          ]);

        if (cancelled) return;

        setState({
          program,
          programIntelligence,
          curriculumRisk,
          alignment,
          forecastSummary,
          executiveObservatory,
          criticalPrograms: criticalPrograms.items,
        });
        setError(null);
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'No fue posible cargar la inteligencia del programa.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [programId]);

  const suggestedSkills = useMemo(() => {
    const fromProgram = state.program?.skills?.map((skill) => skill.nombre) ?? [];
    const fromGaps = state.programIntelligence?.top_gaps.flatMap((item) => extractString(item)) ?? [];
    const fromRecommendations = state.programIntelligence?.top_recommendations.flatMap((item) => extractRecommendationSkills(item)) ?? [];
    const fromAlignment = state.alignment?.missing_skills ?? [];
    const fromRisk = state.curriculumRisk?.risk_drivers.flatMap((driver) => extractString(driver.evidence)) ?? [];
    return uniqueStrings([...fromProgram, ...fromGaps, ...fromRecommendations, ...fromAlignment, ...fromRisk]).slice(0, 10);
  }, [state.alignment?.missing_skills, state.curriculumRisk?.risk_drivers, state.program?.skills, state.programIntelligence?.top_gaps, state.programIntelligence?.top_recommendations]);

  const result: UseProgramIntelligenceDataResult = {
    ...state,
    isLoading,
    error,
    suggestedSkills,
  };

  return result;
}

export function useProgramSimulations(
  programId: number | null,
  proposedSkills: string[],
  horizons: number[] = [6, 12, 24],
): UseProgramSimulationsResult {
  const [simulations, setSimulations] = useState<Record<number, CurriculumSimulationResponse>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const skillSignature = useMemo(() => uniqueStrings(proposedSkills).map((skill) => normalizeText(skill)).join('|'), [proposedSkills]);

  useEffect(() => {
    if (!programId || !skillSignature) {
      setSimulations({});
      setIsLoading(false);
      return;
    }

    const currentProgramId = programId;
    let cancelled = false;

    async function load() {
      try {
        setIsLoading(true);
        const uniqueSkills = uniqueStrings(proposedSkills);
        const results = await Promise.all(
          horizons.map(async (horizon) => {
            const data = await getCurriculumSimulator(currentProgramId, uniqueSkills, horizon);
            return [horizon, data] as const;
          }),
        );
        if (cancelled) return;
        setSimulations(Object.fromEntries(results));
        setError(null);
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'No fue posible ejecutar la simulación curricular.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [horizons, programId, skillSignature, proposedSkills]);

  return { simulations, isLoading, error };
}
