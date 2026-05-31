import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  askObservatory,
  getExecutiveNarrative,
  getProgramSummary,
  getRecommendationExplanation,
} from '../services/api';
import type {
  AskObservatoryResponse,
  ExecutiveNarrativeResponse,
  ProgramSummaryResponse,
  RecommendationExplanationResponse,
} from '../types/api';

interface ExecutiveAiState {
  programSummary?: ProgramSummaryResponse;
  executiveNarrative?: ExecutiveNarrativeResponse;
  recommendationExplanation?: RecommendationExplanationResponse;
  observatoryAnswer?: AskObservatoryResponse;
  isLoading: boolean;
  error?: string;
}

export function useExecutiveAi(programId: number | null, recommendationId: number | null = null) {
  const [state, setState] = useState<ExecutiveAiState>({ isLoading: false });

  useEffect(() => {
    let cancelled = false;

    setState((current) => ({ ...current, isLoading: true, error: undefined }));

    Promise.all([
      programId ? getProgramSummary(programId) : Promise.resolve(undefined),
      getExecutiveNarrative(programId ?? undefined),
      recommendationId ? getRecommendationExplanation(recommendationId) : Promise.resolve(null),
    ])
      .then(([programSummary, executiveNarrative, recommendationExplanation]) => {
        if (cancelled) {
          return;
        }
        setState({
          programSummary: programSummary || undefined,
          executiveNarrative,
          recommendationExplanation: recommendationExplanation || undefined,
          isLoading: false,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setState({
          isLoading: false,
          error: error instanceof Error ? error.message : 'No se pudo generar la explicación ejecutiva.',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [programId, recommendationId]);

  const runQuery = useCallback(
    async (question: string, context?: Record<string, unknown>) => {
      setState((current) => ({ ...current, isLoading: true, error: undefined }));
      try {
        const observatoryAnswer = await askObservatory({
          question,
          program_id: programId ?? undefined,
          recommendation_id: recommendationId ?? undefined,
          context: context ?? {},
        });
        setState((current) => ({ ...current, observatoryAnswer, isLoading: false }));
        return observatoryAnswer;
      } catch (error) {
        setState((current) => ({
          ...current,
          isLoading: false,
          error: error instanceof Error ? error.message : 'No se pudo consultar el observatorio.',
        }));
        return null;
      }
    },
    [programId, recommendationId],
  );

  return useMemo(
    () => ({
      ...state,
      runQuery,
    }),
    [runQuery, state],
  );
}
