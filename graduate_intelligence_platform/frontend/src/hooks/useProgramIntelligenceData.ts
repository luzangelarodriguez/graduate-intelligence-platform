import { useEffect, useMemo, useState } from 'react';

import {
  getCriticalPrograms,
  getCurriculumRisk,
  getCurriculumSimulator,
  getExecutiveObservatory,
  getForecastSummary,
  getProgramas,
  getProgramAlignment,
  getProgramIntelligenceDetail,
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

function buildFallbackProgramIntelligence(program: Program): ProgramIntelligenceItem {
  const alignment = Number(program.promedio_match_mercado) || Number(program.porcentaje_match) || 0;
  const risk = Math.max(0, 100 - alignment);
  const gapCount = Math.max(1, Math.round(risk / 8));
  return {
    program_id: program.especializacion_id,
    program_name: program.nombre_especializacion,
    program_role: program.rol,
    alignment_score: alignment,
    risk_score: risk,
    risk_level: alignment >= 70 ? 'low' : alignment >= 50 ? 'medium' : 'critical',
    gap_count: gapCount,
    top_gaps: [],
    top_recommendations: [],
    forecast_signals: [],
    role_signals: [],
    emerging_technologies: [],
    recommended_actions: [
      alignment >= 70
        ? 'Mantener seguimiento y ajustar el currículo con señales emergentes.'
        : 'Priorizar actualización curricular sobre skills de mercado y evidencia laboral.',
    ],
    business_justification:
      alignment >= 70
        ? 'El programa mantiene una base curricular aceptable con oportunidad de vigilancia.'
        : 'El programa presenta presión de actualización curricular frente a la demanda laboral observada.',
    supporting_evidence: {
      source: 'programas',
      program_id: program.especializacion_id,
      alignment_score: alignment,
      total_empleos_relacionados: program.total_empleos_relacionados,
    },
    source_tables: ['programas'],
    confidence: alignment > 0 ? 0.65 : 0.35,
    generated_at: new Date().toISOString(),
  };
}

function withTimeout<T>(promise: Promise<T>, timeoutMs = 3500): Promise<T | undefined> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(undefined), timeoutMs);
    promise
      .then((value) => {
        clearTimeout(timer);
        resolve(value);
      })
      .catch(() => {
        clearTimeout(timer);
        resolve(undefined);
      });
  });
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
        const programsPage = await withTimeout(getProgramas(100), 12000);
        const fallbackProgram = programsPage?.items.find((item) => item.especializacion_id === currentProgramId);
        const baseProgram: Program | undefined = fallbackProgram || undefined;

        const [
          programIntelligence,
          curriculumRisk,
          alignment,
          forecastSummary,
          executiveObservatory,
          criticalPrograms,
        ] = await Promise.all([
          withTimeout(getProgramIntelligenceDetail(currentProgramId)),
          withTimeout(getCurriculumRisk(currentProgramId)),
          withTimeout(getProgramAlignment(currentProgramId)),
          withTimeout(getForecastSummary(25)),
          withTimeout(getExecutiveObservatory()),
          withTimeout(getCriticalPrograms(12, 12)),
        ]);

        const resolvedProgram = baseProgram;
        const resolvedProgramIntelligence =
          programIntelligence ||
          (resolvedProgram ? buildFallbackProgramIntelligence(resolvedProgram) : undefined);

        if (cancelled) return;

        setState({
          program: resolvedProgram,
          programIntelligence: resolvedProgramIntelligence,
          curriculumRisk,
          alignment,
          forecastSummary,
          executiveObservatory,
          criticalPrograms: criticalPrograms?.items || [],
        });
        const failures = [resolvedProgram ? '' : 'program', resolvedProgramIntelligence ? '' : 'program-intelligence'].filter(Boolean);
        setError(failures.length >= 2 ? 'No se pudo cargar la inteligencia base del programa.' : null);
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
  const normalizedHorizons = useMemo(() => {
    return [...new Set(horizons.filter((horizon) => Number.isFinite(horizon) && horizon > 0))].sort((left, right) => left - right);
  }, [horizons.join('|')]);

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
          normalizedHorizons.map(async (horizon) => {
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
  }, [normalizedHorizons, programId, skillSignature, proposedSkills]);

  return { simulations, isLoading, error };
}
