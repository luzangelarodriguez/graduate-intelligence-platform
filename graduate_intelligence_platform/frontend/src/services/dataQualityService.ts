import { getApiBaseUrlLabel } from '../config/api';
import { laborMarketService } from './laborMarketService';
import { programService } from './programService';
import { recommendationService } from './recommendationService';
import { skillsService } from './skillsService';
import type { ResourceResult } from './serviceState';

export interface DataQualityRow {
  entity: string;
  endpoint: string;
  status: ResourceResult<unknown>['status'];
  records: number;
  impact: string;
  action: string;
  error?: string;
}

export async function getDataQualitySnapshot() {
  const checks = await Promise.all([
    programService.listPrograms().then((result) => ({ entity: 'Programas', result })),
    programService.listProgramIntelligence().then((result) => ({ entity: 'Inteligencia curricular', result })),
    laborMarketService.listJobs().then((result) => ({ entity: 'Empleos', result })),
    laborMarketService.listMatches().then((result) => ({ entity: 'Matches programa-vacante', result })),
    skillsService.listEmergingSkills().then((result) => ({ entity: 'Skills emergentes', result })),
    laborMarketService.listMarketForecast().then((result) => ({ entity: 'Proyección laboral', result })),
    recommendationService.listRecommendations().then((result) => ({ entity: 'Recomendaciones', result })),
  ]);

  const rows: DataQualityRow[] = checks.map(({ entity, result }) => ({
    entity,
    endpoint: result.endpoint,
    status: result.status,
    records: result.count,
    impact:
      result.status === 'success'
        ? 'La sección puede mostrar evidencia real.'
        : result.status === 'empty'
          ? 'La sección mostrará un estado vacío institucional.'
          : 'La sección requiere revisión técnica antes de confiar en la lectura.',
    action: result.action,
    error: result.error,
  }));

  return {
    baseUrl: getApiBaseUrlLabel(),
    generatedAt: new Date().toISOString(),
    rows,
    successful: rows.filter((row) => row.status === 'success').length,
    empty: rows.filter((row) => row.status === 'empty').length,
    errors: rows.filter((row) => row.status === 'error').length,
  };
}





