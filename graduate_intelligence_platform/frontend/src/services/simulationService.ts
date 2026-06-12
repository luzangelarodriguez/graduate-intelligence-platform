import { getCurriculumRisk, getCurriculumSimulator } from './api';
import { requestResource } from './serviceState';

export const simulationService = {
  getRisk: (programId: number) =>
    requestResource(
      `/programas/${programId}/curriculum-risk`,
      () => getCurriculumRisk(programId),
      'No hay cálculo de riesgo curricular para este programa.',
      'Revise las brechas curriculares y la evidencia de skills del programa.',
    ),
  simulate: (programId: number, skills: string[], horizonMonths: number) =>
    requestResource(
      `/curriculum-simulator?program_id=${programId}&horizon_months=${horizonMonths}`,
      () => getCurriculumSimulator(programId, skills, horizonMonths),
      'No hay simulación curricular para este programa y horizonte.',
      'Seleccione skills priorizadas o valide la evidencia curricular del programa.',
    ),
};


