import { getEmergingSkills, getProgramIntelligence, getProgramIntelligenceDetail } from './api';
import { requestResource } from './serviceState';

export const skillsService = {
  listEmergingSkills: () =>
    requestResource(
      '/emerging-skills',
      () => getEmergingSkills(50),
      'No hay skills emergentes disponibles.',
      'Valide el observatorio de skills emergentes y las fuentes laborales recientes.',
    ),
  listProgramSkillEvidence: () =>
    requestResource(
      '/program-intelligence',
      () => getProgramIntelligence(100),
      'No hay evidencia de skills por programa.',
      'Procese microcurrículos y brechas curriculares para poblar program-intelligence.',
    ),
  getProgramSkills: (programId: number) =>
    requestResource(
      `/program-intelligence/${programId}`,
      () => getProgramIntelligenceDetail(programId),
      'No hay skills específicas para este programa.',
      'Verifique microcurrículo, normalización de skills y brechas del programa.',
    ),
};


