export type Tone = 'blue' | 'green' | 'amber' | 'red' | 'slate';

export type Progress = {
  label: string;
  value: string;
  level: 'level-38' | 'level-48' | 'level-55' | 'level-62' | 'level-68' | 'level-72' | 'level-76' | 'level-82' | 'level-86' | 'level-91' | 'level-94';
  tone?: Tone;
};

export const navItems = [
  'Home ejecutivo',
  'Especializacion',
  'Benchmarking SNIES',
  'Empleabilidad',
  'Reescritura IA',
  'Comite academico',
  'Detalle microcurricular',
  'Dashboard institucional',
] as const;

export const executiveMetrics = [
  { label: 'Indice institucional de pertinencia', value: '82.4', detail: 'Portafolio competitivo con presion selectiva de actualizacion.', tone: 'green' as Tone },
  { label: 'Programas criticos', value: '9', detail: 'Tres requieren decision del comite en este ciclo.', tone: 'amber' as Tone },
  { label: 'Universidades comparables', value: '24', detail: 'Referentes SNIES usados para lectura competitiva.', tone: 'blue' as Tone },
  { label: 'Riesgo curricular alto', value: '4', detail: 'Asociado a vigencia tecnologica y baja evidencia laboral.', tone: 'red' as Tone },
];

export const internalRanking: Progress[] = [
  { label: 'Visual Analytics y Big Data', value: '88', level: 'level-86', tone: 'green' },
  { label: 'Ciberseguridad', value: '81', level: 'level-82', tone: 'blue' },
  { label: 'Gerencia de Proyectos', value: '74', level: 'level-76', tone: 'blue' },
  { label: 'Marketing Digital', value: '69', level: 'level-68', tone: 'amber' },
];

export const riskSignals: Progress[] = [
  { label: 'Obsolescencia tecnologica', value: 'Alta', level: 'level-76', tone: 'red' },
  { label: 'Evidencia laboral insuficiente', value: 'Media alta', level: 'level-68', tone: 'amber' },
  { label: 'Solapamiento curricular', value: 'Medio', level: 'level-55', tone: 'amber' },
  { label: 'Resultados poco medibles', value: 'Controlado', level: 'level-48', tone: 'blue' },
];

export const employabilityMap: Progress[] = [
  { label: 'Bogota', value: '82%', level: 'level-82', tone: 'green' },
  { label: 'Medellin', value: '68%', level: 'level-68', tone: 'blue' },
  { label: 'Cali', value: '48%', level: 'level-48', tone: 'amber' },
  { label: 'Remoto LATAM', value: '76%', level: 'level-76', tone: 'green' },
];

export const programSignals = [
  { label: 'Estado curricular', value: 'Actualizacion prioritaria controlada', detail: 'El nucleo disciplinar es solido; la mejora esta en tecnologia aplicada y evidencia de evaluacion.' },
  { label: 'Indice de alineacion', value: '84/100', detail: 'Alineacion alta frente a demanda de roles analiticos ejecutivos.' },
  { label: 'Score institucional', value: 'A-', detail: 'Competitivo para portafolio de posgrado virtual.' },
];

export const technologyCoverage: Progress[] = [
  { label: 'BI ejecutivo', value: '90%', level: 'level-91', tone: 'green' },
  { label: 'Gobierno de datos', value: '66%', level: 'level-68', tone: 'amber' },
  { label: 'Analitica cloud', value: '72%', level: 'level-72', tone: 'blue' },
  { label: 'Automatizacion con IA', value: '48%', level: 'level-48', tone: 'red' },
];

export const laborRoles = [
  ['Analytics Lead', '1.248', '+18%'],
  ['BI Architect', '904', '+12%'],
  ['Data Product Manager', '612', '+21%'],
  ['Governance Analyst', '488', '+9%'],
];

export const skillsHeatmap = [
  { label: 'Power BI', level: 5 },
  { label: 'SQL avanzado', level: 5 },
  { label: 'Python analitico', level: 4 },
  { label: 'Gobierno de datos', level: 3 },
  { label: 'Analitica cloud', level: 3 },
  { label: 'Storytelling ejecutivo', level: 4 },
];

export const sniesPrograms = [
  ['U. Andes', '91', 'Muy alta', '+9'],
  ['UNIR', '82', 'Alta', '0'],
  ['U. Rosario', '80', 'Alta', '-2'],
  ['U. EAFIT', '78', 'Media alta', '-4'],
  ['U. Sabana', '73', 'Media', '-9'],
  ['U. Javeriana', '72', 'Media', '-10'],
];

export const marketTrend: Progress[] = [
  { label: 'Analytics Lead', value: '94%', level: 'level-94', tone: 'green' },
  { label: 'BI Architect', value: '82%', level: 'level-82', tone: 'green' },
  { label: 'Data Product Manager', value: '78%', level: 'level-76', tone: 'blue' },
  { label: 'Decision Scientist', value: '62%', level: 'level-62', tone: 'blue' },
  { label: 'Data Governance', value: '55%', level: 'level-55', tone: 'amber' },
];

export const vacancyEvidence = [
  ['Analista BI Senior', 'Power BI, SQL, storytelling', 'Alta', 'Actualizar modulo de visualizacion'],
  ['Lider de gobierno de datos', 'Calidad, gobierno, etica', 'Media alta', 'Refuerzo transversal'],
  ['Arquitecto analytics cloud', 'Cloud, seguridad, integracion', 'Media', 'Nuevo caso aplicado'],
  ['Product manager data', 'Metricas, experimentacion', 'Alta', 'Proyecto integrador'],
];

export const committeeRows = [
  ['Visualizacion avanzada', 'Aprobar', 'Alto', 'Bajo'],
  ['Gobierno de datos', 'Actualizar', 'Alto', 'Medio'],
  ['Mineria descriptiva', 'Revisar', 'Medio', 'Alto'],
  ['Herramientas legacy', 'Retirar', 'Bajo', 'Alto'],
];

export const institutionalRows = [
  ['Ingenieria', '86', '2', 'Alta'],
  ['Empresa', '81', '3', 'Media'],
  ['Educacion', '78', '1', 'Media'],
  ['Salud', '74', '3', 'Alta'],
  ['Derecho', '83', '0', 'Baja'],
];
