import { getProgramIntelligenceDetail, getRecommendationsV2 } from './api';
import { requestResource } from './serviceState';

export const recommendationService = {
  listRecommendations: () =>
    requestResource(
      '/recommendations-v2',
      () => getRecommendationsV2(undefined, 50),
      'No hay recomendaciones institucionales activas.',
      'Revise recommendation_observatory y los criterios de priorización.',
    ),
  listProgramRecomendaciones: (programId: number) =>
    requestResource(
      `/recommendations-v2?program_id=${programId}`,
      () => getRecommendationsV2(programId, 50),
      'No hay recomendaciones específicas para este programa.',
      'Valide si el programa tiene brechas, evidencia laboral y reglas de recomendación suficientes.',
    ),
  listEmbeddedProgramRecomendaciones: (programId: number) =>
    requestResource(
      `/program-intelligence/${programId}`,
      () => getProgramIntelligenceDetail(programId),
      'No hay recomendaciones embebidas en la inteligencia del programa.',
      'Valide program_intelligence.top_recommendations.',
    ),
};




