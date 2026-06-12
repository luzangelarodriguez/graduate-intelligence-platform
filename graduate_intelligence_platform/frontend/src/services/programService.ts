import {
  getCriticalPrograms,
  getExecutiveObservatory,
  getProgramAlignment,
  getProgramDashboard,
  getProgramIntelligence,
  getProgramIntelligenceDetail,
  getProgramas,
} from './api';
import { requestResource } from './serviceState';
import { hasProgramCurricularEvidence } from '../hooks/useProgramIntelligenceData';

export const programService = {
  listPrograms: () =>
    requestResource(
      '/api/programas',
      async () => {
        const [programsResult, intelligenceResult] = await Promise.allSettled([
          getProgramas(100),
          getProgramIntelligence(100),
        ]);
        const programs = programsResult.status === 'fulfilled' ? programsResult.value.items || [] : [];
        const eligiblePrograms = new Set(
          intelligenceResult.status === 'fulfilled'
            ? (intelligenceResult.value.items || [])
                .filter((item) => hasProgramCurricularEvidence(item))
                .map((item) => Number(item.program_id))
                .filter((programId) => Number.isFinite(programId) && programId > 0)
            : [],
        );
        const filteredPrograms = programs.filter((program) => eligiblePrograms.has(Number(program.especializacion_id)));
        return {
          items: filteredPrograms,
          count: filteredPrograms.length,
          total: filteredPrograms.length,
          limit: 100,
          offset: 0,
        };
      },
      'El endpoint respondió correctamente, pero no entregó programas académicos.',
      'Revise la carga de especializaciones y la vista de programas del backend.',
    ),
  listProgramIntelligence: () =>
    requestResource(
      '/program-intelligence',
      () => getProgramIntelligence(100),
      'No hay inteligencia curricular agregada para programas.',
      'Ejecute o revise el pipeline de inteligencia de programas.',
    ),
  getProgramIntelligence: (programId: number) =>
    requestResource(
      `/program-intelligence/${programId}`,
      () => getProgramIntelligenceDetail(programId),
      'No hay inteligencia específica para este programa.',
      'Procese el microcurrículo del programa y valide su relación con skills y brechas.',
    ),
  getProgramDashboard: (programId: number) =>
    requestResource(
      `/api/dashboard/programa/${programId}`,
      () => getProgramDashboard(programId),
      'No hay dashboard laboral específico para este programa.',
      'Revise matches, vacantes relacionadas y la vista de dashboard por programa.',
    ),
  getProgramAlignment: (programId: number) =>
    requestResource(
      `/programas/${programId}/alignment`,
      () => getProgramAlignment(programId),
      'No hay cálculo de alineación para este programa.',
      'Revise la cobertura curricular y las relaciones con skills de mercado.',
    ),
  getCriticalPrograms: () =>
    requestResource(
      '/critical-programs',
      () => getCriticalPrograms(20, 12),
      'No se encontraron programas críticos en el horizonte consultado.',
      'Valide si el pipeline de riesgo curricular está entregando resultados.',
    ),
  getExecutiveObservatory: () =>
    requestResource(
      '/executive-observatory',
      getExecutiveObservatory,
      'No hay métricas ejecutivas institucionales disponibles.',
      'Valide la tabla de métricas del observatorio ejecutivo.',
    ),
};




