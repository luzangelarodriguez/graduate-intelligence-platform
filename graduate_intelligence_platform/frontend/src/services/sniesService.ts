import { getProgramIntelligenceDetail, getRelatedUniversityPrograms } from './api';
import { requestResource } from './serviceState';

export const sniesService = {
  getRelatedUniversities: (programId: number) =>
    requestResource(
      `/api/programs/related-universities/${programId}`,
      () => getRelatedUniversityPrograms(programId, 20),
      'No hay universidades comparables disponibles para este programa.',
      'Verifique la carga SNIES, la homologación del programa, el dominio académico o el endpoint de benchmark.',
    ),
  getEmbeddedBenchmark: (programId: number) =>
    requestResource(
      `/program-intelligence/${programId}`,
      () => getProgramIntelligenceDetail(programId),
      'No hay benchmark SNIES embebido en la inteligencia del programa.',
      'Valide supporting_evidence.domain_benchmark.benchmark_institutions.',
    ),
};


