import { useEffect, useRef, useState } from 'react';

// ─── Config ────────────────────────────────────────────────────────────────────
const API = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

const C = {
  navy:      '#0D2158',
  red:       '#E63329',
  bg:        '#F4F6FA',
  navyBg:    '#EEF2FB',
  border:    '#D8DEF0',
  white:     '#FFFFFF',
  navyLight: '#1A3580',
  redLight:  '#FDECEA',
  gold:      '#B7791F',
  goldBg:    '#FEF3C7',
  mid:       '#7B93D4',
  light:     '#C7D3F5',
};

// ─── Types ─────────────────────────────────────────────────────────────────────
interface Programa {
  id: number;
  nombre: string;
  matches_total: number;
  score_promedio: number;
  score_maximo: number;
  labels: { high: number; medium: number; low: number };
}
interface TopMatch {
  programa: string;
  empleo: string;
  empresa: string;
  score: number;
  label: string;
  skills_en_comun: string[];
  skills_faltantes: string[];
}
interface Summary {
  run_id: number | null;
  fecha: string;
  programas: Programa[];
  top_matches: TopMatch[];
  totales: { matches: number; alta: number; media: number; baja: number };
}
interface SkillMercado  { skill: string; frecuencia: number }
interface SkillPrograma { skill: string; cobertura: number; asignaturas?: string[] }
interface Brecha        { skill: string; frecuencia_mercado: number }
interface Fortaleza     { skill: string; frecuencia_mercado: number; cobertura_programa: number }
interface Exclusiva     { skill: string; cobertura: number }
interface SkillsAnalysis {
  program_id: number;
  skills_mercado: SkillMercado[];
  skills_programa: SkillPrograma[];
  brechas: Brecha[];
  fortalezas: Fortaleza[];
  exclusivas_programa: Exclusiva[];
  cobertura_pct: number;
}
interface Competitor {
  nombre_ies: string;
  nombre_programa: string;
  ciudad: string;
  modalidad: string;
  nivel_academico: string;
  creditos: number | null;
  duracion: string;
  area_conocimiento: string;
  municipio: string;
  departamento: string;
  periodicidad_admision: string;
  matriculados: number;
  graduados: number;
  inscritos: number;
}
interface UniversityData {
  program_id: number;
  competitors: Competitor[];
  total: number;
}
interface RAPropuesto {
  codigo: string;
  texto: string;
  tipo: 'nuevo' | 'modificado';
  skills_incorporadas: string[];
}
interface RedisenioPropuesta {
  asignatura: string;
  relevancia_score: number;
  confianza: 'alta' | 'media' | 'baja';
  brechas_relevantes: string[];
  ras_actuales_texto: string;
  ras_propuestos: RAPropuesto[];
  skills_incorporadas: string[];
  justificacion?: string;
}
interface RediseniResult {
  program_id: number;
  asignaturas_analizadas: number;
  propuestas: RedisenioPropuesta[];
  advertencia?: string;
  debug?: Record<string, unknown>;
}
interface RediseniJob {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'error';
  current_step?: string | null;
  result?: RediseniResult;
  error?: string;
}

// ─── Static program metadata ──────────────────────────────────────────────────
const PROGRAMS = [
  { id: 94,  label: 'Visual Analytics & Big Data',    nombre: 'Especialización en Visual Analytics y Big Data', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 92,  label: 'Inteligencia Artificial',        nombre: 'Especialización en Inteligencia Artificial',     creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 108, label: 'Especialización en Criminología', nombre: 'Especialización en Criminología',               creditos: 24, duracion: '2', periodicidad: 'Semestral' },
  { id: 20,  label: 'Neuropsicología y Educación',    nombre: 'Especialización en Neuropsicología y Educación', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
];

const NAV_SECTIONS = [
  { id: 's1',  n: '01',  label: 'Estado de Pertinencia',    sub: 'Score general de alineación con el mercado' },
  { id: 's2',  n: '02',  label: 'Qué Demanda el Mercado',   sub: 'Skills y roles más solicitados en vacantes' },
  { id: 's3',  n: '03',  label: 'Qué Enseña el Programa',   sub: 'Competencias actuales del microcurrículo' },
  { id: 's4',  n: '04',  label: 'Cobertura Curricular',     sub: '% del mercado que el programa cubre' },
  { id: 's4b', n: '04b', label: 'Benchmarking SNIES',       sub: 'Comparativa con universidades similares' },
  { id: 's5',  n: '05',  label: 'Brechas Curriculares',     sub: 'Skills demandadas que el programa no enseña' },
  { id: 's6',  n: '06',  label: 'Empleos Compatibles',      sub: 'Vacantes reales alineadas con el programa' },
  { id: 's7',  n: '07',  label: 'Simulación Curricular',    sub: 'Impacto de incorporar nuevas competencias' },
  { id: 's8',  n: '08',  label: 'Recomendaciones',          sub: 'Acciones sugeridas para el comité curricular' },
  { id: 's9',  n: '09',  label: 'Rediseño Curricular',      sub: 'Propuestas de mejora asistidas por IA' },
];

// ─── Fallback data ─────────────────────────────────────────────────────────────
const FALLBACK: Summary = {
  run_id: 6, fecha: '2026-06-01',
  programas: [
    { id: 92,  nombre: 'Inteligencia Artificial',       matches_total: 38, score_promedio: 71.2, score_maximo: 88.4, labels: { high: 18, medium: 14, low: 6 } },
    { id: 94,  nombre: 'Visual Analytics and Big Data', matches_total: 31, score_promedio: 68.5, score_maximo: 85.1, labels: { high: 14, medium: 12, low: 5 } },
    { id: 108, nombre: 'Especialización en Criminología', matches_total: 22, score_promedio: 52.3, score_maximo: 67.8, labels: { high: 4, medium: 10, low: 8 } },
    { id: 20,  nombre: 'Neuropsicología y Educación',    matches_total: 0,  score_promedio: 0,    score_maximo: 0,    labels: { high: 0, medium: 0,  low: 0  } },
  ],
  top_matches: [
    { programa: 'Visual Analytics', empleo: 'Data Scientist Senior', empresa: 'Bancolombia', score: 88.4, label: 'high', skills_en_comun: ['Python', 'Machine Learning', 'SQL'], skills_faltantes: ['Spark', 'Kafka'] },
    { programa: 'Visual Analytics', empleo: 'Analista BI', empresa: 'Rappi', score: 85.1, label: 'high', skills_en_comun: ['Power BI', 'SQL'], skills_faltantes: ['dbt', 'Airflow'] },
    { programa: 'Visual Analytics', empleo: 'ML Engineer', empresa: 'Mercado Libre', score: 83.7, label: 'high', skills_en_comun: ['TensorFlow', 'Python'], skills_faltantes: ['Kubernetes'] },
  ],
  totales: { matches: 91, alta: 36, media: 36, baja: 19 },
};

const FALLBACK_SKILLS: Record<number, SkillsAnalysis> = {
  94: {
    program_id: 94, cobertura_pct: 54,
    skills_mercado:  [
      { skill: 'Python', frecuencia: 28 }, { skill: 'Power BI', frecuencia: 24 },
      { skill: 'SQL', frecuencia: 22 },    { skill: 'Tableau', frecuencia: 18 },
      { skill: 'Spark', frecuencia: 16 },  { skill: 'AWS', frecuencia: 14 },
      { skill: 'Airflow', frecuencia: 12 },{ skill: 'dbt', frecuencia: 10 },
      { skill: 'Kafka', frecuencia: 9 },   { skill: 'Databricks', frecuencia: 8 },
    ],
    skills_programa:  [
      { skill: 'Python', cobertura: 5 }, { skill: 'Power BI', cobertura: 4 },
      { skill: 'SQL', cobertura: 4 },    { skill: 'Tableau', cobertura: 3 },
      { skill: 'R', cobertura: 3 },      { skill: 'Estadística', cobertura: 3 },
      { skill: 'Excel', cobertura: 2 },  { skill: 'Matplotlib', cobertura: 2 },
    ],
    fortalezas: [
      { skill: 'Python', frecuencia_mercado: 28, cobertura_programa: 5 },
      { skill: 'Power BI', frecuencia_mercado: 24, cobertura_programa: 4 },
      { skill: 'SQL', frecuencia_mercado: 22, cobertura_programa: 4 },
      { skill: 'Tableau', frecuencia_mercado: 18, cobertura_programa: 3 },
    ],
    brechas: [
      { skill: 'Spark', frecuencia_mercado: 16 },  { skill: 'AWS', frecuencia_mercado: 14 },
      { skill: 'Airflow', frecuencia_mercado: 12 }, { skill: 'dbt', frecuencia_mercado: 10 },
      { skill: 'Kafka', frecuencia_mercado: 9 },    { skill: 'Databricks', frecuencia_mercado: 8 },
    ],
    exclusivas_programa: [
      { skill: 'R', cobertura: 3 }, { skill: 'Estadística', cobertura: 3 },
      { skill: 'Excel', cobertura: 2 }, { skill: 'Matplotlib', cobertura: 2 },
    ],
  },
  92: {
    program_id: 92, cobertura_pct: 61,
    skills_mercado:  [
      { skill: 'Python', frecuencia: 31 },         { skill: 'TensorFlow', frecuencia: 22 },
      { skill: 'Machine Learning', frecuencia: 20 },{ skill: 'PyTorch', frecuencia: 18 },
      { skill: 'SQL', frecuencia: 17 },             { skill: 'AWS', frecuencia: 15 },
      { skill: 'Docker', frecuencia: 13 },           { skill: 'Kubernetes', frecuencia: 11 },
      { skill: 'Spark', frecuencia: 10 },            { skill: 'MLflow', frecuencia: 9 },
    ],
    skills_programa:  [
      { skill: 'Python', cobertura: 6 },          { skill: 'TensorFlow', cobertura: 5 },
      { skill: 'Machine Learning', cobertura: 5 },{ skill: 'PyTorch', cobertura: 4 },
      { skill: 'Estadística', cobertura: 4 },     { skill: 'Álgebra Lineal', cobertura: 3 },
      { skill: 'Scikit-learn', cobertura: 3 },    { skill: 'NLP', cobertura: 2 },
    ],
    fortalezas: [
      { skill: 'Python', frecuencia_mercado: 31, cobertura_programa: 6 },
      { skill: 'TensorFlow', frecuencia_mercado: 22, cobertura_programa: 5 },
      { skill: 'Machine Learning', frecuencia_mercado: 20, cobertura_programa: 5 },
      { skill: 'PyTorch', frecuencia_mercado: 18, cobertura_programa: 4 },
    ],
    brechas: [
      { skill: 'AWS', frecuencia_mercado: 15 },       { skill: 'Docker', frecuencia_mercado: 13 },
      { skill: 'Kubernetes', frecuencia_mercado: 11 }, { skill: 'Spark', frecuencia_mercado: 10 },
      { skill: 'MLflow', frecuencia_mercado: 9 },
    ],
    exclusivas_programa: [
      { skill: 'Estadística', cobertura: 4 }, { skill: 'Álgebra Lineal', cobertura: 3 },
      { skill: 'Scikit-learn', cobertura: 3 }, { skill: 'NLP', cobertura: 2 },
    ],
  },
  108: {
    program_id: 108, cobertura_pct: 38,
    skills_mercado:  [
      { skill: 'Investigación', frecuencia: 18 },  { skill: 'Excel', frecuencia: 15 },
      { skill: 'Análisis datos', frecuencia: 14 }, { skill: 'Derecho Penal', frecuencia: 13 },
      { skill: 'SPSS', frecuencia: 11 },           { skill: 'Redacción', frecuencia: 10 },
      { skill: 'Python', frecuencia: 8 },          { skill: 'Power BI', frecuencia: 7 },
      { skill: 'GIS', frecuencia: 6 },             { skill: 'R', frecuencia: 5 },
    ],
    skills_programa:  [
      { skill: 'Investigación', cobertura: 5 }, { skill: 'Derecho Penal', cobertura: 4 },
      { skill: 'Criminología', cobertura: 4 },  { skill: 'Excel', cobertura: 2 },
      { skill: 'Estadística', cobertura: 3 },   { skill: 'Victimología', cobertura: 3 },
    ],
    fortalezas: [
      { skill: 'Investigación', frecuencia_mercado: 18, cobertura_programa: 5 },
      { skill: 'Excel', frecuencia_mercado: 15, cobertura_programa: 2 },
      { skill: 'Derecho Penal', frecuencia_mercado: 13, cobertura_programa: 4 },
    ],
    brechas: [
      { skill: 'Análisis datos', frecuencia_mercado: 14 }, { skill: 'SPSS', frecuencia_mercado: 11 },
      { skill: 'Redacción', frecuencia_mercado: 10 },      { skill: 'Python', frecuencia_mercado: 8 },
      { skill: 'Power BI', frecuencia_mercado: 7 },        { skill: 'GIS', frecuencia_mercado: 6 },
      { skill: 'R', frecuencia_mercado: 5 },
    ],
    exclusivas_programa: [
      { skill: 'Criminología', cobertura: 4 }, { skill: 'Victimología', cobertura: 3 },
      { skill: 'Estadística', cobertura: 3 },
    ],
  },
  20: {
    program_id: 20,
    skills_mercado:   [],
    skills_programa:  [],
    brechas:          [],
    fortalezas:       [],
    exclusivas_programa: [],
    cobertura_pct:    0,
  },
};

// ─── Pertinencia scale ─────────────────────────────────────────────────────────
function pertinenciaLevel(score: number): { label: string; color: string; bg: string; desc: string } {
  if (score >= 75) return { label: 'Excelente', color: '#059669', bg: '#d1fae5', desc: 'El currículo está muy bien alineado con las demandas actuales del mercado laboral.' };
  if (score >= 60) return { label: 'Buena',     color: '#2563eb', bg: '#dbeafe', desc: 'Buena alineación general; existen oportunidades de fortalecimiento en áreas específicas.' };
  if (score >= 40) return { label: 'Moderada',  color: C.gold,   bg: C.goldBg,  desc: 'Alineación parcial. Se recomienda actualización curricular prioritaria.' };
  return              { label: 'Crítica',   color: '#dc2626', bg: '#fee2e2', desc: 'Brecha significativa entre el currículo y las competencias demandadas por el mercado.' };
}

// ─── Skill normalization ──────────────────────────────────────────────────────
const SKILL_ALIASES: Record<string, string> = {
  'powerbi':    'power bi',
  'power-bi':   'power bi',
  'rstudio':    'r',
  'r studio':   'r',
};
function normalizeSkill(s: string): string {
  const lower = s.toLowerCase().replace(/\s+/g, ' ').trim();
  return SKILL_ALIASES[lower] ?? lower;
}

// ─── Skill classification ─────────────────────────────────────────────────────
const SKILL_CATS = {
  herramienta: new Set([
    'python','sql','power bi','tableau','excel','aws','azure','gcp','docker',
    'spark','databricks','tensorflow','r','hadoop','kafka','looker','salesforce',
    'pytorch','kubernetes','git','postgresql','mysql','mongodb','redis',
    'numpy','pandas','sklearn','scikit-learn','jupyter','colab','sap','crm',
    'spss','wais','wisc','rorschach','bender','rstudio','powerbi',
  ]),
  competencia: new Set([
    'machine learning','deep learning','nlp','data visualization','big data','etl',
    'business intelligence','analisis de datos','data engineering','mlops',
    'estadistica','data warehouse','data lake','cloud computing','feature engineering',
    'computer vision','forecasting','data governance','data mining','series de tiempo',
    'neuropsicolog','neuropsicologia','cognitiv','funciones ejecutivas','funciones superiores',
    'evaluacion','intervencion','psicodiagnostico','psicometria',
    'aprendizaje','memoria','atencion','percepcion','lenguaje',
    'trastorno','discapacidad','neuroling','rehabilitacion',
    'psicologia','diagnostico','evaluacion neuropsicologica',
    'visualizacion de datos','pmbok','lean','scrum','agile','six sigma',
    'metodologia','analisis de datos',
  ]),
  habilidad: new Set([
    'gestion','liderazgo','comunicacion','trabajo en equipo','pensamiento critico',
    'innovacion','negociacion','planeacion','kanban',
    'gestion de proyectos','orientacion a resultados','toma de decisiones',
    'educacion','orientacion','diversidad','inclusion','desarrollo','inteligencia',
    'pedagogia','docencia','didactica','ensenanza','formacion',
    'resolucion de problemas',
  ]),
};
type SkillCat = 'herramienta' | 'competencia' | 'habilidad' | 'otro';
function classifySkill(s: string): SkillCat {
  const key = normalizeSkill(s);
  if (SKILL_CATS.herramienta.has(key)) return 'herramienta';
  if (SKILL_CATS.competencia.has(key)) return 'competencia';
  if (SKILL_CATS.habilidad.has(key))   return 'habilidad';
  for (const cat of ['herramienta', 'competencia', 'habilidad'] as ('herramienta' | 'competencia' | 'habilidad')[]) {
    for (const term of SKILL_CATS[cat]) {
      if (term.length >= 6 && (key.startsWith(term) || term.startsWith(key))) return cat;
    }
  }
  return 'otro';
}
const CAT_STYLE: Record<SkillCat, { bg: string; color: string; icon: string; label: string }> = {
  herramienta: { bg: 'rgba(147,197,253,0.2)', color: '#3b82f6', icon: '⚙', label: 'Herramienta' },
  competencia:  { bg: 'rgba(134,239,172,0.2)', color: '#16a34a', icon: '◈', label: 'Competencia'  },
  habilidad:    { bg: 'rgba(251,191,36,0.2)',  color: '#d97706', icon: '◇', label: 'Habilidad'    },
  otro:         { bg: 'rgba(148,163,184,0.15)',color: '#64748b', icon: '·', label: 'Otro'         },
};

// ─── Insight block ─────────────────────────────────────────────────────────────
function Insight({ text, dark = false }: { text: string; dark?: boolean }) {
  return (
    <div className="rounded-r-xl px-5 py-4 my-5"
      style={{ background: dark ? 'rgba(183,121,31,0.15)' : C.navyBg, borderLeft: `4px solid ${dark ? C.gold : C.navy}` }}>
      <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: dark ? C.gold : C.navy }}>✦ Lectura Clave</p>
      <p className="text-sm leading-relaxed" style={{ color: dark ? '#e2e8f0' : '#1e293b' }}>{text}</p>
    </div>
  );
}

// ─── Semicircular SVG gauge ────────────────────────────────────────────────────
function SemiGauge({ pct, color, size = 200 }: { pct: number; color: string; size?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => { const id = setTimeout(() => setV(pct), 80); return () => clearTimeout(id); }, [pct]);
  const r = 80, stroke = 14, cx = 100, cy = 100;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const arcX = (deg: number) => cx + r * Math.cos(toRad(deg));
  const arcY = (deg: number) => cy + r * Math.sin(toRad(deg));
  const filled = (v / 100) * 180;
  function describeArc(start: number, end: number) {
    const s = { x: arcX(start), y: arcY(start) };
    const e = { x: arcX(end),   y: arcY(end) };
    const large = Math.abs(end - start) > 180 ? 1 : 0;
    const sweep = end > start ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} ${sweep} ${e.x} ${e.y}`;
  }
  return (
    <svg width={size} height={size * 0.6} viewBox="0 60 200 120" style={{ overflow: 'visible' }}>
      <path d={describeArc(180, 0)} fill="none" stroke="#e5e7eb" strokeWidth={stroke} strokeLinecap="round" />
      {v > 0 && (
        <path d={describeArc(180, 180 - filled)} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          style={{ transition: 'all 1.4s cubic-bezier(.4,0,.2,1)' }} />
      )}
      <text x="100" y="115" textAnchor="middle" fontSize="28" fontWeight="800" fill={color}>{Math.round(v)}%</text>
    </svg>
  );
}

// ─── Skill tag ─────────────────────────────────────────────────────────────────
function SkillTag({ skill, variant = 'default' }: { skill: string; variant?: 'default' | 'gap' | 'match' }) {
  if (variant === 'gap')
    return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626', border: '1px solid rgba(220,38,38,0.25)' }}>− {skill}</span>;
  if (variant === 'match')
    return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: 'rgba(5,150,105,0.1)', color: '#059669', border: '1px solid rgba(5,150,105,0.25)' }}>✓ {skill}</span>;
  const cat = classifySkill(skill);
  const st  = CAT_STYLE[cat];
  return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: st.bg, color: st.color, border: `1px solid ${st.color}33` }} title={st.label}>{st.icon} {skill}</span>;
}

// ─── Horizontal bar ────────────────────────────────────────────────────────────
function HBar({ label, val, max, color }: { label: string; val: number; max: number; color: string }) {
  const pct = max > 0 ? (val / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-600 w-32 flex-shrink-0 truncate">{label}</span>
      <div className="flex-1 h-3 rounded-full" style={{ background: '#e5e7eb' }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold w-6 text-right" style={{ color }}>{val}</span>
    </div>
  );
}

// ─── Explorando msg ────────────────────────────────────────────────────────────
function ExplorandoMsg() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px', background: '#F8F9FC', borderRadius: 8, border: '1px dashed #D8DEF0' }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: '#334670', marginBottom: 8 }}>Mercado laboral en exploración</div>
      <div style={{ fontSize: 13, color: '#6B7A9E', maxWidth: 400, margin: '0 auto', lineHeight: 1.6 }}>
        La oferta digital para este perfil en Colombia es limitada.
        Estamos ampliando la cobertura de vacantes con términos especializados.
        Los datos estarán disponibles en la próxima adquisición.
      </div>
    </div>
  );
}

// ─── Spinner ──────────────────────────────────────────────────────────────────
function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-10 h-10 rounded-full border-4 border-blue-200 border-t-blue-800 animate-spin" />
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
// ─── ProposalCard ─────────────────────────────────────────────────────────────
function ProposalCard({ prop }: { prop: RedisenioPropuesta }) {
  const [expanded, setExpanded] = useState(false);

  const confianzaStyle: Record<string, { bg: string; color: string; label: string }> = {
    alta:  { bg: '#D1FAE5', color: '#065F46', label: 'Confianza alta' },
    media: { bg: '#FEF3C7', color: '#92400E', label: 'Confianza media' },
    baja:  { bg: '#F3F4F6', color: '#374151', label: 'Confianza baja' },
  };
  const conf = confianzaStyle[prop.confianza] ?? confianzaStyle.baja;

  const TRUNCATE = 300;
  const truncated = prop.ras_actuales_texto.length > TRUNCATE && !expanded;
  const displayText = truncated ? prop.ras_actuales_texto.slice(0, TRUNCATE) + '…' : prop.ras_actuales_texto;

  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 12, overflow: 'hidden', marginBottom: 20, background: C.white }}>
      {/* Card header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${C.border}`, background: C.navyBg }}>
        <p style={{ fontSize: 14, fontWeight: 700, color: C.navy, margin: 0 }}>{prop.asignatura}</p>
        <span style={{ fontSize: 11, fontWeight: 700, background: conf.bg, color: conf.color, borderRadius: 20, padding: '3px 10px' }}>
          {conf.label}
        </span>
      </div>

      {/* 2-column body */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 160 }}>
        {/* Left — RAs actuales */}
        <div style={{ padding: '16px 20px', borderRight: `1px solid ${C.border}`, background: '#F9FAFB' }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#6B7280', marginBottom: 10 }}>
            RAs Actuales
          </p>
          <p style={{ fontSize: 12, color: '#374151', lineHeight: 1.7, margin: 0, whiteSpace: 'pre-wrap' }}>{displayText}</p>
          {prop.ras_actuales_texto.length > TRUNCATE && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{ marginTop: 8, fontSize: 11, color: C.navy, fontWeight: 700, background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}>
              {expanded ? 'Ver menos ▲' : 'Ver más ▼'}
            </button>
          )}
        </div>

        {/* Right — RAs propuestos */}
        <div style={{ padding: '16px 20px', background: '#F0FDF4' }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#065F46', marginBottom: 10 }}>
            RAs Propuestos
          </p>
          {prop.ras_propuestos.length === 0 ? (
            <p style={{ fontSize: 12, color: '#6B7280', fontStyle: 'italic', margin: 0 }}>
              Ninguna brecha disponible es coherente con esta asignatura.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {prop.ras_propuestos.map((ra, i) => (
                <div key={i} style={{ paddingBottom: 14, borderBottom: i < prop.ras_propuestos.length - 1 ? `1px solid #BBF7D0` : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontWeight: 800, color: '#065F46' }}>{ra.codigo}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 700,
                      background: ra.tipo === 'nuevo' ? '#DCFCE7' : '#E0F2FE',
                      color: ra.tipo === 'nuevo' ? '#166534' : '#075985',
                      borderRadius: 20, padding: '1px 8px',
                    }}>
                      {ra.tipo === 'nuevo' ? 'nuevo' : 'modificado'}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: '#166534', lineHeight: 1.6, margin: '0 0 8px' }}>{ra.texto}</p>
                  {ra.skills_incorporadas.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {ra.skills_incorporadas.map((s, si) => (
                        <span key={si} style={{ fontSize: 10, background: '#D1FAE5', color: '#065F46', borderRadius: 20, padding: '1px 8px', fontWeight: 600 }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Card footer */}
      <div style={{ padding: '12px 20px', borderTop: `1px solid ${C.border}`, background: C.white }}>
        {prop.justificacion && (
          <p style={{ fontSize: 11, color: '#6B7280', fontStyle: 'italic', margin: '0 0 8px' }}>
            {prop.justificacion}
          </p>
        )}
        {prop.brechas_relevantes.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#6B7280', alignSelf: 'center', marginRight: 4 }}>Brechas:</span>
            {prop.brechas_relevantes.slice(0, 6).map((b, bi) => (
              <span key={bi} style={{ fontSize: 10, background: C.navyBg, color: C.navy, borderRadius: 20, padding: '1px 8px', fontWeight: 600 }}>
                {b}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionBlock({ id, n, title, dark = false, children }: {
  id: string; n: string; title: string; dark?: boolean; children: React.ReactNode;
}) {
  return (
    <section id={id} style={{
      borderBottom: `1px solid ${dark ? 'rgba(255,255,255,0.08)' : C.border}`,
      background: dark ? C.navy : 'transparent',
      margin: dark ? '0 -48px' : '0',
      padding: dark ? '48px 48px' : '48px 0',
    } as React.CSSProperties}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: dark ? C.light : C.red, marginBottom: 4 }}>
        Sección {n}
      </p>
      <h2 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.02em', color: dark ? C.white : C.navy, marginBottom: 24, marginTop: 0 }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ObservatorioStorytelling() {
  const [summary, setSummary]         = useState<Summary | null>(null);
  const [skills, setSkills]           = useState<SkillsAnalysis | null>(null);
  const [univ, setUniv]               = useState<UniversityData | null>(null);
  const [loading, setLoading]         = useState(true);
  const [isFallback, setIsFallback]   = useState(false);
  const [programaId, setProgramaId]   = useState(94);
  const [activeSection, setActiveSection] = useState('s1');
  const [pipelineLogOpen, setPipelineLogOpen] = useState(false);
  const [pipelineJobId, setPipelineJobId]     = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus]   = useState<string>('idle');
  const [pipelineStep, setPipelineStep]       = useState<string | null>(null);
  const [pipelineLog, setPipelineLog]         = useState<string[]>([]);
  const [redesignJob, setRedesignJob]         = useState<RediseniJob | null>(null);
  const [redesignDlError, setRedesignDlError] = useState(false);
  const mainRef         = useRef<HTMLDivElement>(null);
  const tabsRef         = useRef<HTMLDivElement>(null);
  const pollRef         = useRef<ReturnType<typeof setInterval> | null>(null);
  const redesignPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // fetch summary
  useEffect(() => {
    setLoading(true);
    setIsFallback(false);
    fetch(`${API}/api/dashboard/summary?program_id=${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: Summary) => { setSummary(d); setLoading(false); })
      .catch(() => {
        const fb = { ...FALLBACK, programas: FALLBACK.programas.filter(p => p.id === programaId) };
        const prog = fb.programas[0];
        if (prog) fb.totales = { matches: prog.matches_total, alta: prog.labels.high, media: prog.labels.medium, baja: prog.labels.low };
        setSummary(fb);
        setIsFallback(true);
        setLoading(false);
      });
  }, [programaId]);

  // fetch skills analysis
  useEffect(() => {
    setSkills(null);
    fetch(`${API}/api/dashboard/skills-analysis/${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: SkillsAnalysis) => setSkills(d))
      .catch(() => setSkills(FALLBACK_SKILLS[programaId] ?? null));
  }, [programaId]);

  // fetch universities
  useEffect(() => {
    setUniv(null);
    fetch(`${API}/api/programs/related-universities/${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: UniversityData) => setUniv(d))
      .catch(() => setUniv(null));
  }, [programaId]);

  // Reset redesign when program changes
  useEffect(() => {
    setRedesignJob(null);
    setRedesignDlError(false);
    if (redesignPollRef.current) {
      clearInterval(redesignPollRef.current);
      redesignPollRef.current = null;
    }
  }, [programaId]);

  // Cleanup redesign poll on unmount
  useEffect(() => () => { if (redesignPollRef.current) clearInterval(redesignPollRef.current); }, []);

  function startRedesign() {
    setRedesignDlError(false);
    setRedesignJob({ job_id: '', status: 'queued', current_step: 'Iniciando análisis…' });
    fetch(`${API}/api/curriculum/redesign/${programaId}`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: { job_id: string }) => {
        const initial: RediseniJob = { job_id: d.job_id, status: 'queued', current_step: 'En cola…' };
        setRedesignJob(initial);
        redesignPollRef.current = setInterval(() => pollRedesign(d.job_id), 3000);
      })
      .catch(() => setRedesignJob({ job_id: '', status: 'error', error: 'No se pudo iniciar el análisis. Verifica que el servidor esté activo.' }));
  }

  function pollRedesign(jobId: string) {
    fetch(`${API}/api/curriculum/redesign/status/${jobId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: RediseniJob) => {
        setRedesignJob(d);
        if (d.status === 'done' || d.status === 'error') {
          if (redesignPollRef.current) { clearInterval(redesignPollRef.current); redesignPollRef.current = null; }
        }
      })
      .catch(() => {});
  }

  async function downloadRedesign() {
    setRedesignDlError(false);
    try {
      const res = await fetch(`${API}/api/curriculum/redesign/${programaId}/download`);
      if (res.status === 404) { setRedesignDlError(true); return; }
      if (!res.ok) { setRedesignDlError(true); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rediseno_curricular_${programaId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setRedesignDlError(true);
    }
  }

  // pipeline
  function startPipeline() {
    setPipelineStatus('launching');
    setPipelineLog([]);
    setPipelineStep(null);
    fetch(`${API}/api/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ program_id: programaId, steps: ['microcurriculos', 'matching'] }),
    })
      .then(r => r.json())
      .then((d: { job_id: string }) => {
        setPipelineJobId(d.job_id);
        setPipelineStatus('queued');
        pollRef.current = setInterval(() => pollJob(d.job_id), 3000);
      })
      .catch(() => setPipelineStatus('error'));
  }

  function pollJob(jobId: string) {
    fetch(`${API}/api/pipeline/status/${jobId}`)
      .then(r => r.json())
      .then((d: { status: string; current_step: string | null; log: string[] }) => {
        setPipelineStatus(d.status);
        setPipelineStep(d.current_step);
        setPipelineLog(d.log);
        if (d.status === 'done' || d.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (d.status === 'done') setTimeout(() => window.location.reload(), 1500);
        }
      })
      .catch(() => {});
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  // Scroll-spy via IntersectionObserver (root = main scroll container)
  useEffect(() => {
    const container = mainRef.current;
    if (!container) return;
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        });
      },
      { root: container, rootMargin: '-20% 0px -70% 0px', threshold: 0 }
    );
    NAV_SECTIONS.forEach(({ id }) => {
      const el = container.querySelector(`#${id}`);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [loading]);

  // Auto-scroll active tab into view in the horizontal subnav
  useEffect(() => {
    const nav = tabsRef.current;
    if (!nav) return;
    const activeTab = nav.querySelector<HTMLButtonElement>(`[data-section="${activeSection}"]`);
    if (activeTab) activeTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }, [activeSection]);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg }}>
      <div style={{ textAlign: 'center' }}>
        <div className="mx-auto w-14 h-14 rounded-full border-4 border-blue-200 border-t-blue-900 animate-spin" style={{ marginBottom: 16 }} />
        <p style={{ fontSize: 13, fontWeight: 500, color: C.navy }}>Cargando observatorio…</p>
      </div>
    </div>
  );

  const d = summary!;
  const { totales, programas, top_matches } = d;
  const prog  = programas.find(p => p.id === programaId) ?? programas[0];
  const meta  = PROGRAMS.find(p => p.id === programaId) ?? PROGRAMS[0];
  const score = prog?.score_promedio ?? 0;
  const nivel = pertinenciaLevel(score);
  const coberturaPct   = skills?.cobertura_pct ?? 0;
  const brechaPct      = skills ? 100 - coberturaPct : 0;
  const empCompatibles = top_matches.filter(m => m.skills_en_comun.length > 0).length;
  const maxCobertura   = skills ? Math.max(...skills.skills_programa.map(s => s.cobertura), 1) : 1;
  const qualityMatches = top_matches.filter(m => (m.skills_en_comun?.length ?? 0) > 0).length;
  const dataPobre      = totales.matches < 10 || qualityMatches < 3;
  const brechasAlta    = skills?.brechas.filter(b => b.frecuencia_mercado >= 10) ?? [];
  const empleosCompatibles = top_matches.filter(m => m.skills_en_comun.length > 0 && m.score >= 45).slice(0, 8);

  const skillsByCategory: Record<string, SkillPrograma[]> = {};
  if (skills) {
    // Deduplicate by normalized skill name, summing cobertura across variants
    const seen = new Map<string, SkillPrograma>();
    for (const s of skills.skills_programa) {
      const norm = normalizeSkill(s.skill);
      if (seen.has(norm)) {
        seen.get(norm)!.cobertura += s.cobertura;
      } else {
        seen.set(norm, { ...s, skill: norm });
      }
    }
    for (const s of seen.values()) {
      const cat = CAT_STYLE[classifySkill(s.skill)].label;
      if (!skillsByCategory[cat]) skillsByCategory[cat] = [];
      skillsByCategory[cat].push(s);
    }
  }

  // Same dedup for skills_mercado used in S2
  const skillsMercadoDeduped: SkillMercado[] = (() => {
    if (!skills) return [];
    const seen = new Map<string, SkillMercado>();
    for (const s of skills.skills_mercado) {
      const norm = normalizeSkill(s.skill);
      if (seen.has(norm)) {
        seen.get(norm)!.frecuencia += s.frecuencia;
      } else {
        seen.set(norm, { ...s, skill: norm });
      }
    }
    return Array.from(seen.values()).sort((a, b) => b.frecuencia - a.frecuencia);
  })();
  const maxFrecuencia = skillsMercadoDeduped.length ? Math.max(...skillsMercadoDeduped.map(s => s.frecuencia), 1) : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'system-ui, -apple-system, sans-serif', background: '#F7F8FC' }}>

      {/* ── HEADER PRINCIPAL ── */}
      <header style={{
        background: 'linear-gradient(90deg, #0a3d8f 0%, #1265b8 55%, #1f7bc4 100%)',
        padding: '0 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 68,
        flexShrink: 0,
        boxShadow: '0 2px 12px rgba(10,61,143,0.30)',
        position: 'relative',
        zIndex: 20,
      }}>
        {/* Logo izquierda */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div>
            {/* Logo "uniR" serif con punto celeste sobre la i */}
            <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1 }}>
              <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 30, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>un</span>
              <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 30, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em', position: 'relative', display: 'inline-block' }}>
                i
                <span style={{ position: 'absolute', top: -5, left: '50%', transform: 'translateX(-50%)', width: 5, height: 5, background: '#5BC4F5', borderRadius: '50%', display: 'block' }} />
              </span>
              <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 32, fontWeight: 900, color: '#fff', letterSpacing: '-0.02em' }}>R</span>
            </div>
            <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.65)', marginTop: 3 }}>
              La Universidad en Internet
            </div>
          </div>

          <div style={{ width: 1, height: 30, background: 'rgba(255,255,255,0.22)', margin: '0 4px' }} />

          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', letterSpacing: '0.01em' }}>Observatorio de Pertinencia</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.60)', letterSpacing: '0.04em', marginTop: 2 }}>Colombia · Inteligencia Curricular</div>
          </div>
        </div>

        {/* Derecha: badge + selector + KPIs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* KPIs pequeños */}
          {[
            { v: `${score.toFixed(0)}/100`, l: 'Pertinencia', c: nivel.color },
            { v: `${coberturaPct}%`,         l: 'Cobertura',  c: '#38BDF8' },
            { v: String(empCompatibles),      l: 'Empleos',   c: '#34D399' },
          ].map(({ v, l, c }) => (
            <div key={l} style={{ textAlign: 'center', padding: '5px 12px', background: 'rgba(255,255,255,0.10)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.18)' }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: c, lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.55)', marginTop: 2, letterSpacing: '0.05em' }}>{l}</div>
            </div>
          ))}

          <div style={{ width: 1, height: 30, background: 'rgba(255,255,255,0.18)' }} />

          {/* Beta badge */}
          <span style={{ border: '1.5px solid rgba(255,255,255,0.55)', color: 'rgba(255,255,255,0.85)', fontSize: 9, fontWeight: 800, letterSpacing: '0.14em', textTransform: 'uppercase', borderRadius: 20, padding: '4px 10px' }}>
            Beta
          </span>

          {/* Selector de programa */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, padding: '7px 12px' }}>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.55)', whiteSpace: 'nowrap' }}>Programa</span>
            <select
              value={programaId}
              onChange={e => setProgramaId(Number(e.target.value))}
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer', outline: 'none', maxWidth: 190 }}>
              {PROGRAMS.map(p => (
                <option key={p.id} value={p.id} style={{ color: '#111', background: '#fff' }}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Run info + pipeline button */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setPipelineLogOpen(o => !o)}
              title={`Run #${d.run_id} · ${d.fecha}`}
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 8, color: 'rgba(255,255,255,0.70)', fontSize: 11, fontWeight: 600, cursor: 'pointer', padding: '7px 10px', lineHeight: 1 }}>
              ↻
            </button>
            {pipelineLogOpen && (
              <div style={{ position: 'absolute', right: 0, top: 40, width: 280, background: '#0a3d8f', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, padding: '14px 16px', boxShadow: '0 8px 24px rgba(0,0,0,0.35)', zIndex: 50 }}>
                <p style={{ fontSize: 11, color: '#86efac', marginBottom: 6, fontWeight: 700 }}>Último análisis: {d.fecha ?? '—'}</p>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5, margin: 0 }}>
                  Adquisición y matching corren cada noche vía GitHub Actions.
                </p>
                {isFallback && <p style={{ fontSize: 10, color: C.gold, marginTop: 8, fontWeight: 600 }}>⚠ Datos de referencia (API no disponible)</p>}
                {pipelineStatus !== 'idle' && (
                  <div style={{ marginTop: 10, padding: '6px 10px', background: 'rgba(255,255,255,0.08)', borderRadius: 6, fontSize: 10 }}>
                    <span style={{ color: '#fff' }}>
                      {pipelineStatus === 'queued'  && '⏳ Iniciando…'}
                      {pipelineStatus === 'running' && `⚙ ${pipelineStep ?? '…'}`}
                      {pipelineStatus === 'done'    && '✓ Listo'}
                      {pipelineStatus === 'error'   && '⚠ Error'}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── SUBNAV HORIZONTAL (tabs) ── */}
      <div
        ref={tabsRef}
        style={{
          background: '#fff',
          borderBottom: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          overflowX: 'auto',
          scrollbarWidth: 'none',
          flexShrink: 0,
          paddingLeft: 24,
        }}>
        <style>{`
          .subnav-tabs::-webkit-scrollbar { display: none; }
          .skill-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px 20px;
          }
          @media (max-width: 640px) {
            .skill-grid { grid-template-columns: 1fr; }
          }
          .chip-sub { display: none; font-size: 9px; color: #9CA3AF; margin-left: 4px; }
          @media (max-width: 640px) { .chip-sub { display: inline; } }
        `}</style>
        {NAV_SECTIONS.map(({ id, n, label, sub }) => {
          const isActive = activeSection === id;
          return (
            <button
              key={id}
              data-section={id}
              onClick={() => {
                const el = mainRef.current?.querySelector(`#${id}`);
                el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center',
                padding: '0 16px',
                height: 52,
                background: 'transparent',
                border: 'none',
                borderBottom: `2px solid ${isActive ? '#0a3d8f' : 'transparent'}`,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'color 0.15s, border-color 0.15s',
                flexShrink: 0,
              }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: '0.05em', color: isActive ? '#1265b8' : '#D1D5DB' }}>{n}</span>
                <span style={{ fontSize: 12, fontWeight: isActive ? 700 : 500, color: isActive ? '#0a3d8f' : '#374151' }}>{label}</span>
              </div>
              <span style={{ fontSize: 10, color: isActive ? '#1265b8' : '#9CA3AF', marginTop: 2, fontWeight: 400 }}>{sub}</span>
            </button>
          );
        })}
      </div>

      {/* ── MAIN CONTENT ── */}
      <main ref={mainRef} style={{ flex: 1, overflowY: 'auto', background: '#F7F8FC' }}>

        {/* Sections */}
        <div style={{ padding: '0 48px', maxWidth: 960, margin: '0 auto' }}>

          {/* S1 */}
          <SectionBlock id="s1" n="01" title="Estado de Pertinencia">
            <div className="flex flex-col sm:flex-row gap-8 items-center">
              <div className="flex flex-col items-center gap-3 flex-shrink-0">
                <SemiGauge pct={score} color={nivel.color} size={240} />
                <span className="rounded-full px-5 py-1.5 text-sm font-extrabold" style={{ background: nivel.bg, color: nivel.color }}>{nivel.label}</span>
              </div>
              <div className="flex-1 space-y-4">
                <p className="text-sm leading-relaxed text-gray-700">{nivel.desc}</p>
                <div className="space-y-2">
                  {[
                    { range: '75 – 100', label: 'Excelente', color: '#059669', bg: '#d1fae5' },
                    { range: '60 – 74',  label: 'Buena',     color: '#2563eb', bg: '#dbeafe' },
                    { range: '40 – 59',  label: 'Moderada',  color: C.gold,   bg: C.goldBg  },
                    { range: '0 – 39',   label: 'Crítica',   color: '#dc2626', bg: '#fee2e2' },
                  ].map(({ range, label, color, bg }) => (
                    <div key={label} className="flex items-center gap-3">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                      <span className="text-xs font-semibold w-14" style={{ color }}>{label}</span>
                      <span className="text-xs text-gray-500">{range} / 100</span>
                      {Math.round(score) >= parseInt(range) && Math.round(score) <= parseInt(range.split('–')[1] ?? '100') && (
                        <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: bg, color }}>← aquí</span>
                      )}
                    </div>
                  ))}
                </div>
                <Insight text={`Con un score promedio de ${score.toFixed(0)}/100, el programa se ubica en nivel ${nivel.label.toLowerCase()}. ${nivel.desc}`} />
              </div>
            </div>
          </SectionBlock>

          {/* S2 */}
          <SectionBlock id="s2" n="02" title="Qué Demanda el Mercado" dark>
            {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (() => {
              // Group deduplicated skills by category, sorted by frecuencia DESC
              const bycat: Record<'herramienta'|'competencia'|'habilidad', SkillMercado[]> = { herramienta: [], competencia: [], habilidad: [] };
              for (const s of skillsMercadoDeduped) {
                const cat = classifySkill(s.skill);
                if (cat !== 'otro') bycat[cat].push(s);
              }
              const cols: { cat: 'herramienta'|'competencia'|'habilidad'; items: SkillMercado[] }[] = [
                { cat: 'herramienta', items: bycat.herramienta.slice(0, 8) },
                { cat: 'competencia', items: bycat.competencia.slice(0, 8) },
                { cat: 'habilidad',   items: bycat.habilidad.slice(0, 8) },
              ];
              return (
                <>
                  <p className="text-sm text-blue-200 mb-6">Skills clasificadas por tipo en las {totales.matches} vacantes analizadas.</p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
                    {cols.map(({ cat, items }) => {
                      const st = CAT_STYLE[cat];
                      const maxFreq = items.length ? Math.max(...items.map(s => s.frecuencia), 1) : 1;
                      return (
                        <div key={cat} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: 12, padding: '16px 18px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                            <span style={{ fontSize: 16 }}>{st.icon}</span>
                            <div>
                              <p style={{ fontSize: 11, fontWeight: 800, color: st.color, textTransform: 'uppercase', letterSpacing: '0.07em', margin: 0 }}>{st.label}s</p>
                              <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{bycat[cat].length} identificadas</p>
                            </div>
                          </div>
                          {items.length === 0 ? (
                            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontStyle: 'italic' }}>Sin datos suficientes</p>
                          ) : (
                            <div className="skill-grid">
                              {items.map(s => (
                                <div key={s.skill} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.75)', width: 72, flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.skill}</span>
                                  <div style={{ flex: 1, height: 5, borderRadius: 4, background: 'rgba(255,255,255,0.10)', minWidth: 20 }}>
                                    <div style={{ height: '100%', borderRadius: 4, background: st.color, width: `${(s.frecuencia / maxFreq) * 100}%`, transition: 'width 0.6s ease' }} />
                                  </div>
                                  <span style={{ fontSize: 9, fontWeight: 700, color: st.color, width: 16, textAlign: 'right', flexShrink: 0 }}>{s.frecuencia}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <Insight dark text={`El mercado demanda ${skillsMercadoDeduped.length} skills distintas. Las 3 más frecuentes son: ${skillsMercadoDeduped.slice(0,3).map(s=>s.skill).join(', ')}.`} />
                </>
              );
            })()}
          </SectionBlock>

          {/* S3 */}
          <SectionBlock id="s3" n="03" title="Qué Enseña el Programa">
            {!skills ? <Spinner /> : (() => {
              const fortalezasSet = new Set(skills.fortalezas.map(f => normalizeSkill(f.skill)));
              return (
                <>
                  {/* Leyenda */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 14, marginBottom: 20, padding: '8px 14px', background: '#F8FAFC', border: `1px solid ${C.border}`, borderRadius: 8 }}>
                    {(['herramienta','competencia','habilidad','otro'] as SkillCat[]).map(k => (
                      <span key={k} style={{ fontSize: 11, color: CAT_STYLE[k].color, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ fontSize: 8 }}>●</span> {CAT_STYLE[k].label}
                      </span>
                    ))}
                    <span style={{ color: C.border }}>·</span>
                    <span style={{ fontSize: 11, color: '#374151' }}><strong>Negrita</strong> = también demandado por el mercado</span>
                    <span style={{ color: C.border }}>·</span>
                    <span style={{ fontSize: 11, color: '#6B7280', fontStyle: 'italic' }}>Hover → asignatura que lo enseña</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
                    {Object.entries(skillsByCategory).map(([cat, skList]) => {
                      const catKey = (Object.entries(CAT_STYLE).find(([, v]) => v.label === cat)?.[0] ?? 'otro') as SkillCat;
                      const st = CAT_STYLE[catKey];
                      const maxCob = Math.max(...skList.map(s => s.cobertura), 1);
                      return (
                        <div key={cat}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                            <span style={{ fontSize: 13 }}>{st.icon}</span>
                            <span style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: st.color }}>{cat}s</span>
                            <span style={{ fontSize: 10, fontWeight: 700, background: st.bg, color: st.color, borderRadius: 20, padding: '1px 8px' }}>{skList.length}</span>
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-start', alignItems: 'baseline', gap: '8px 14px' }}>
                            {skList.map(s => {
                              const esFortale = fortalezasSet.has(normalizeSkill(s.skill));
                              const fs = Math.round(13 + Math.min(20, (s.cobertura / maxCob) * 20));
                              const tooltipText = s.asignaturas && s.asignaturas.length > 0
                                ? `Enseñado en: ${s.asignaturas.join(', ')}`
                                : undefined;
                              return (
                                <span
                                  key={s.skill}
                                  title={tooltipText}
                                  style={{
                                    fontSize: fs,
                                    fontWeight: esFortale ? 800 : 500,
                                    color: st.color,
                                    opacity: esFortale ? 1 : 0.65,
                                    cursor: tooltipText ? 'help' : 'default',
                                    lineHeight: 1.3,
                                    transition: 'opacity 0.15s',
                                  }}>
                                  {s.skill}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                    {skills.skills_programa.length === 0 && (
                      <p className="text-sm text-gray-400 py-6 text-center">Cargando competencias del programa… (ejecuta el pipeline para poblar los datos)</p>
                    )}
                  </div>
                  {skills.skills_programa.length > 0 && (
                    <Insight text={`El programa cubre ${skills.skills_programa.length} skills. Sus fortalezas son: ${skills.fortalezas.slice(0,3).map(f=>f.skill).join(', ') || 'por determinar'}.`} />
                  )}
                </>
              );
            })()}
          </SectionBlock>

          {/* S4 */}
          <SectionBlock id="s4" n="04" title="Cobertura Curricular" dark>
            {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (
              <>
                <p className="text-sm text-blue-200 mb-6">Porcentaje de las skills demandadas por el mercado que ya están cubiertas en el plan de estudios.</p>
                <div className="flex flex-col sm:flex-row gap-8 items-center">
                  <div className="flex flex-col items-center gap-2 flex-shrink-0">
                    <SemiGauge pct={coberturaPct} color="#86efac" size={220} />
                    <p className="text-sm font-semibold" style={{ color: '#86efac' }}>Cobertura Curricular</p>
                  </div>
                  <div className="flex-1 space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { k: 'Skills cubiertas', v: skills.fortalezas.length, c: '#86efac' },
                        { k: 'Brechas',          v: skills.brechas.length,    c: '#fca5a5' },
                        { k: 'Exclusivas prog.', v: skills.exclusivas_programa.length, c: C.mid },
                      ].map(({ k, v, c }) => (
                        <div key={k} className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                          <p className="text-2xl font-extrabold" style={{ color: c }}>{v}</p>
                          <p className="text-xs text-blue-300 mt-0.5">{k}</p>
                        </div>
                      ))}
                    </div>
                    {skills.fortalezas.length > 0 && (
                      <div>
                        <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: '#86efac' }}>✓ Fortalezas (presentes en ambos)</p>
                        <div className="flex flex-wrap gap-1.5">
                          {skills.fortalezas.slice(0, 8).map(f => <SkillTag key={f.skill} skill={f.skill} variant="match" />)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <Insight dark text={`El programa cubre el ${coberturaPct}% de las skills que el mercado laboral demanda. ${coberturaPct >= 60 ? 'Cobertura sólida con oportunidades de mejora.' : 'Existe una brecha significativa que requiere actualización curricular.'}`} />
              </>
            )}
          </SectionBlock>

          {/* S4b: SNIES Benchmarking */}
          <SectionBlock id="s4b" n="04b" title="Benchmarking SNIES">
            {!univ ? <Spinner /> : univ.competitors.length === 0 ? (
              <p style={{ fontSize: 13, color: C.mid }}>Sin programas similares registrados para este perfil en SNIES.</p>
            ) : (
              <>
                <p style={{ fontSize: 13, color: '#4b5563', marginBottom: 20, lineHeight: 1.5 }}>
                  <strong style={{ color: C.navy }}>{univ.total}</strong> programas similares activos en Colombia
                  en modalidad virtual · datos SNIES 2024.
                </p>
                <div style={{ border: `1px solid ${C.border}`, borderRadius: 10, overflow: 'hidden' }}>
                  {/* table header */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px 80px', padding: '8px 16px', background: C.navyBg, borderBottom: `1px solid ${C.border}` }}>
                    <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: C.mid }}>Universidad / Programa</span>
                    <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: C.mid, textAlign: 'right' as const }}>Matriculados</span>
                    <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: C.mid, textAlign: 'right' as const }}>Graduados</span>
                  </div>
                  {/* rows */}
                  {univ.competitors.slice(0, 8).map((comp, i) => (
                    <div key={i} style={{
                      display: 'grid', gridTemplateColumns: '1fr 90px 80px',
                      padding: '12px 16px',
                      borderBottom: i < Math.min(univ.competitors.length, 8) - 1 ? `1px solid ${C.border}` : 'none',
                      background: i % 2 === 0 ? C.white : '#fafbfd',
                      alignItems: 'center',
                    }}>
                      <div style={{ minWidth: 0, paddingRight: 12 }}>
                        <p style={{ fontSize: 12, fontWeight: 600, color: C.navy, margin: 0, lineHeight: 1.3, whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>{comp.nombre_ies}</p>
                        <p style={{ fontSize: 10, color: C.mid, margin: 0, marginTop: 2, whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>{comp.nombre_programa}</p>
                      </div>
                      <p style={{ fontSize: 16, fontWeight: 800, color: C.red, margin: 0, textAlign: 'right' as const }}>{(comp.matriculados ?? 0).toLocaleString('es-CO')}</p>
                      <p style={{ fontSize: 13, fontWeight: 600, color: C.navy, margin: 0, textAlign: 'right' as const }}>{(comp.graduados ?? 0).toLocaleString('es-CO')}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </SectionBlock>

          {/* S5 */}
          <SectionBlock id="s5" n="05" title="Brechas Curriculares">
            {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (
              <>
                <p className="text-sm text-gray-600 mb-6">Skills con alta demanda en el mercado que el programa aún no cubre, agrupadas por tipo.</p>
                {skills.brechas.length === 0 ? (
                  <div className="rounded-xl px-5 py-8 text-center" style={{ background: '#d1fae5', border: '1px solid #6ee7b7' }}>
                    <p className="text-sm font-semibold text-green-800">✓ Sin brechas críticas identificadas</p>
                    <p className="text-xs text-green-600 mt-1">El programa cubre las principales skills del mercado.</p>
                  </div>
                ) : (
                  <>
                    {(['herramienta', 'competencia', 'habilidad', 'otro'] as SkillCat[]).map(cat => {
                      const st      = CAT_STYLE[cat];
                      const catList = skills.brechas.filter(b => classifySkill(b.skill) === cat);
                      if (catList.length === 0) return null;
                      const maxFreqCat = Math.max(...catList.map(b => b.frecuencia_mercado ?? 1), 1);
                      return (
                        <div key={cat} style={{ marginBottom: 24 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                            <span>{st.icon}</span>
                            <span style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#DC2626' }}>{st.label}s faltantes</span>
                            <span style={{ fontSize: 10, fontWeight: 700, background: '#FEE2E2', color: '#DC2626', borderRadius: 20, padding: '1px 8px' }}>{catList.length}</span>
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-start', alignItems: 'baseline', gap: '8px 14px' }}>
                            {catList.map(b => {
                              const esRuido = cat === 'otro' && (b.frecuencia_mercado ?? 0) < 3;
                              const freq = b.frecuencia_mercado ?? 1;
                              const fs = Math.round(13 + Math.min(20, (freq / maxFreqCat) * 20));
                              return (
                                <span
                                  key={b.skill}
                                  title={esRuido ? 'Skill genérica — verificar si aplica al programa' : `${freq} vacante${freq !== 1 ? 's' : ''} en el mercado`}
                                  style={{
                                    fontSize: fs,
                                    fontWeight: 600,
                                    color: esRuido ? '#B45309' : '#DC2626',
                                    opacity: esRuido ? 0.6 : 1,
                                    cursor: 'help',
                                    lineHeight: 1.3,
                                  }}>
                                  {b.skill}{esRuido ? ' ⚠' : ''}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                    {skills.exclusivas_programa.length > 0 && (
                      <div className="rounded-xl p-4 mb-4" style={{ background: C.navyBg, border: `1px solid ${C.border}` }}>
                        <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: C.navy }}>Skills Exclusivas del Programa (no demandadas aún)</p>
                        <div className="flex flex-wrap gap-2">
                          {skills.exclusivas_programa.map(e => (
                            <span key={e.skill} className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: '#EEF2FB', color: C.navy, border: `1px solid ${C.border}` }}>{e.skill}</span>
                          ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-2">Estas skills pueden ser relevantes en un futuro cercano o nicho específico.</p>
                      </div>
                    )}
                  </>
                )}
                <Insight text={`Se detectaron ${skills.brechas.length} brechas, de las cuales ${brechasAlta.length} son de prioridad alta por su alta frecuencia en el mercado. ${brechasAlta.length > 0 ? `Cubrir "${brechasAlta[0]?.skill}" y "${brechasAlta[1]?.skill ?? brechasAlta[0]?.skill}" tendría el mayor impacto.` : ''}`} />
              </>
            )}
          </SectionBlock>

          {/* S6 */}
          <SectionBlock id="s6" n="06" title="Empleos Compatibles" dark>
            {empleosCompatibles.length === 0 ? (
              <div className="rounded-xl px-5 py-8 text-center" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <p className="text-sm text-blue-300 leading-relaxed">Aún no hay empleos con solapamiento de skills para este programa.<br />Se requiere re-ejecutar el pipeline de matching en Railway.</p>
              </div>
            ) : (
              <>
                <p className="text-sm text-blue-200 mb-5">Vacantes con mayor compatibilidad de skills con el programa seleccionado.</p>
                <div className="space-y-3">
                  {empleosCompatibles.map((m, i) => {
                    const total    = m.skills_en_comun.length + m.skills_faltantes.length;
                    const coverPct = total ? Math.round((m.skills_en_comun.length / total) * 100) : 0;
                    return (
                      <div key={i} className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                        <div className="flex items-start gap-3 mb-3">
                          <span className="text-xl font-black w-7 text-center flex-shrink-0" style={{ color: 'rgba(255,255,255,0.2)' }}>{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-white truncate">{m.empleo}</p>
                            <p className="text-xs text-blue-300">{m.empresa} · Score {m.score.toFixed(0)}/100</p>
                          </div>
                          <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                            style={{ background: coverPct >= 60 ? 'rgba(134,239,172,0.2)' : 'rgba(252,165,165,0.2)', color: coverPct >= 60 ? '#86efac' : '#fca5a5' }}>
                            {coverPct}% cubierto
                          </span>
                        </div>
                        <div className="ml-10 mb-2">
                          <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${coverPct}%`, background: '#86efac' }} />
                          </div>
                        </div>
                        <div className="ml-10 flex flex-wrap gap-1">
                          {m.skills_en_comun.slice(0, 4).map(s => <SkillTag key={s} skill={s} variant="match" />)}
                          {m.skills_faltantes.slice(0, 3).map(s => <SkillTag key={s} skill={s} variant="gap" />)}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <Insight dark text={`${empCompatibles} empleos tienen solapamiento directo de skills con el programa. El empleo con mayor cobertura es "${empleosCompatibles[0]?.empleo}" en ${empleosCompatibles[0]?.empresa}.`} />
              </>
            )}
          </SectionBlock>

          {/* S7 */}
          <SectionBlock id="s7" n="07" title="Simulación Curricular">
            {dataPobre ? <ExplorandoMsg /> : (
              <>
                <p className="text-sm text-gray-600 mb-6">Impacto estimado de incorporar las principales brechas al plan de estudios.</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                  {[
                    { title: 'Escenario A — Mínimo',   sub: `Incorporar top ${Math.min(brechasAlta.length, 2)} brechas críticas`,            pertinencia: `+${Math.round(brechaPct * 0.25)}%`, cobertura: `${Math.min(coberturaPct + 15, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.2)}`, color: C.gold },
                    { title: 'Escenario B — Moderado', sub: `Incorporar todas las brechas de prioridad alta (${brechasAlta.length})`,          pertinencia: `+${Math.round(brechaPct * 0.45)}%`, cobertura: `${Math.min(coberturaPct + 25, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.4)}`, color: '#2563eb' },
                    { title: 'Escenario C — Completo', sub: `Incorporar todas las brechas identificadas (${skills?.brechas.length ?? '—'})`,   pertinencia: `+${Math.round(brechaPct * 0.70)}%`, cobertura: `${Math.min(coberturaPct + 40, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.65)}`, color: '#059669' },
                  ].map(sc => (
                    <div key={sc.title} className="rounded-2xl border p-5 space-y-3" style={{ borderColor: sc.color, background: C.navyBg }}>
                      <p className="text-sm font-bold" style={{ color: sc.color }}>{sc.title}</p>
                      <p className="text-xs text-gray-500">{sc.sub}</p>
                      <div className="space-y-2">
                        {[{ k: 'Pertinencia', v: sc.pertinencia }, { k: 'Cobertura', v: sc.cobertura }, { k: 'Empleos comp.', v: sc.empleos }].map(({ k, v }) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-gray-600">{k}</span>
                            <span className="font-bold" style={{ color: sc.color }}>{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <Insight text={`Incorporar las ${brechasAlta.length} brechas de alta prioridad podría elevar la cobertura curricular a ~${Math.min(coberturaPct + 25, 99)}% y aumentar los empleos compatibles en ~${Math.round(empCompatibles * 0.4)} adicionales. Estos valores son estimaciones con base en el análisis de frecuencia del mercado.`} />
              </>
            )}
          </SectionBlock>

          {/* S8 */}
          <SectionBlock id="s8" n="08" title="Recomendaciones" dark>
            {dataPobre ? <ExplorandoMsg /> : (
              <>
                <p className="text-sm text-blue-200 mb-6">Acciones prioritarias para mejorar la pertinencia curricular del programa.</p>
                <div className="rounded-xl px-5 py-4 mb-6 flex gap-3" style={{ background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.35)' }}>
                  <span className="text-lg flex-shrink-0 mt-0.5">📋</span>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#fbbf24' }}>Nota metodológica</p>
                    <p className="text-sm leading-relaxed" style={{ color: '#fde68a' }}>
                      Las skills identificadas como "faltantes" provienen de vacantes del mercado laboral activo.
                      Algunas pueden representar ruido contextual (ej: <em>"financiero"</em> en clínicas IPS,{' '}
                      <em>"sas"</em> como herramienta estadística alternativa) y no necesariamente requieren actualización curricular.
                      El comité debe evaluar la pertinencia académica de cada brecha.
                      Las skills marcadas con <span className="font-bold">⚠ Verificar relevancia</span> son las de mayor riesgo de ser ruido (clasificación genérica + menos de 3 vacantes).
                    </p>
                  </div>
                </div>

                {programaId === 20 && skills !== null && (
                  // eslint-disable-next-line no-console
                  (() => { console.log('[S8 debug] skills for program 20:', JSON.stringify(skills, null, 2)); return null; })()
                )}

                {(!skills || (skills.brechas.length === 0 && skills.fortalezas.length === 0)) ? (
                  <div className="rounded-xl px-5 py-6 flex gap-3" style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)' }}>
                    <span className="text-2xl flex-shrink-0">⏳</span>
                    <div>
                      <p className="text-sm font-semibold text-white mb-1">Análisis en proceso</p>
                      <p className="text-sm text-blue-300 leading-relaxed">
                        Los datos de brechas se actualizarán cuando corra el próximo matching nocturno (todos los días a las 03:00 a.m. hora Colombia vía GitHub Actions).
                        Mientras tanto, puedes explorar las secciones de perfiles y empleos compatibles.
                      </p>
                    </div>
                  </div>
                ) : (() => {
                  const topBrechas   = [...(skills?.brechas ?? [])].sort((a, b) => (b.frecuencia_mercado ?? 0) - (a.frecuencia_mercado ?? 0)).slice(0, 3);
                  const topFortalezas = [...(skills?.fortalezas ?? [])].sort((a, b) => (b.cobertura_programa ?? 0) - (a.cobertura_programa ?? 0)).slice(0, 3);
                  const ruido = (skills?.brechas ?? []).filter(b => classifySkill(b.skill) === 'otro' && (b.frecuencia_mercado ?? 0) < 3);
                  type Rec = { action: string; detail: string; urgency: string; color: string; urgBg: string };
                  const recs: Rec[] = [];
                  topBrechas.forEach(b => recs.push({
                    action: `Incorporar "${b.skill}" como contenido del programa.`,
                    detail: `${b.frecuencia_mercado ?? 0} vacante${(b.frecuencia_mercado ?? 0) !== 1 ? 's' : ''} en el mercado lo demandan actualmente y no está cubierto en el currículo.`,
                    urgency: (b.frecuencia_mercado ?? 0) >= 8 ? 'Urgente' : 'Alta',
                    color: (b.frecuencia_mercado ?? 0) >= 8 ? '#dc2626' : '#d97706',
                    urgBg: (b.frecuencia_mercado ?? 0) >= 8 ? '#fee2e2' : '#fef3c7',
                  }));
                  topFortalezas.forEach(f => recs.push({
                    action: `Profundizar "${f.skill}" — ya está en el currículo y el mercado lo valora.`,
                    detail: `Presente en ${f.cobertura_programa} materia${f.cobertura_programa !== 1 ? 's' : ''} del programa y demandado en ${f.frecuencia_mercado} vacante${f.frecuencia_mercado !== 1 ? 's' : ''}. Potencial de diferenciación.`,
                    urgency: 'Media', color: '#2563eb', urgBg: '#dbeafe',
                  }));
                  if (ruido.length > 0) recs.push({
                    action: `Revisar pertinencia de: ${ruido.map(b => `"${b.skill}"`).join(', ')} antes de incorporar.`,
                    detail: 'Estas skills aparecen en pocas vacantes y no tienen categoría clara — pueden ser ruido de mercado contextual.',
                    urgency: 'Verificar', color: '#92400e', urgBg: '#fef9c3',
                  });
                  recs.push({
                    action: 'Actualizar microcurrículo con evidencia de este análisis en la próxima revisión curricular.',
                    detail: 'Documentar decisiones tomadas y skills incorporadas para trazabilidad del proceso de renovación curricular.',
                    urgency: 'Planear', color: '#6b7280', urgBg: 'rgba(255,255,255,0.1)',
                  });
                  return (
                    <div className="space-y-4">
                      {recs.map((rec, i) => (
                        <div key={i} className="rounded-xl p-4 flex gap-4" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                          <span className="text-2xl font-black flex-shrink-0 mt-0.5" style={{ color: 'rgba(255,255,255,0.2)' }}>{i + 1}</span>
                          <div className="flex-1">
                            <div className="flex items-start justify-between gap-3 mb-1">
                              <p className="text-sm font-semibold text-white leading-snug">{rec.action}</p>
                              <span className="rounded-full px-2 py-0.5 text-xs font-bold flex-shrink-0" style={{ background: rec.urgBg, color: rec.color }}>{rec.urgency}</span>
                            </div>
                            <p className="text-xs text-blue-300">{rec.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </>
            )}
          </SectionBlock>

          {/* ── S9: Rediseño Curricular Asistido ── */}
          <SectionBlock id="s9" n="09" title="Rediseño Curricular Asistido">
            {(() => {
              // ── Estado inicial ──────────────────────────────────────────────
              if (!redesignJob || redesignJob.job_id === '') {
                const isLaunching = redesignJob?.status === 'queued' && redesignJob.job_id === '';
                return (
                  <div style={{ maxWidth: 640 }}>
                    <p style={{ fontSize: 14, color: '#4B5563', lineHeight: 1.7, marginBottom: 24 }}>
                      El motor de IA analiza los microcurrículos del programa contra las brechas detectadas en el mercado
                      y genera propuestas concretas de nuevos o modificados Resultados de Aprendizaje (RAs) por asignatura.
                    </p>
                    <div style={{ background: C.navyBg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '20px 24px', marginBottom: 24 }}>
                      <p style={{ fontSize: 12, color: C.navy, fontWeight: 600, marginBottom: 6 }}>¿Qué incluye el análisis?</p>
                      <ul style={{ fontSize: 12, color: '#374151', lineHeight: 1.8, paddingLeft: 18, margin: 0 }}>
                        <li>Identificación de brechas más relevantes por asignatura (TF-IDF)</li>
                        <li>Propuestas de RAs generadas con GPT-4o-mini</li>
                        <li>Filtrado de ruido genérico (Excel, liderazgo, etc.)</li>
                        <li>Descarga en formato .docx con comparación antes/después</li>
                      </ul>
                    </div>
                    <button
                      onClick={startRedesign}
                      disabled={isLaunching}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: isLaunching ? '#9CA3AF' : C.navy,
                        color: C.white,
                        border: 'none', borderRadius: 8,
                        padding: '12px 24px',
                        fontSize: 14, fontWeight: 700,
                        cursor: isLaunching ? 'not-allowed' : 'pointer',
                        transition: 'background 0.15s',
                      }}>
                      {isLaunching ? '⏳ Iniciando…' : '🔬 Analizar y proponer mejoras curriculares'}
                    </button>
                  </div>
                );
              }

              // ── Running / queued ────────────────────────────────────────────
              if (redesignJob.status === 'queued' || redesignJob.status === 'running') {
                return (
                  <div style={{ maxWidth: 520 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
                      <div style={{
                        width: 40, height: 40, borderRadius: '50%',
                        border: `3px solid ${C.border}`,
                        borderTopColor: C.navy,
                        animation: 'spin 0.8s linear infinite',
                        flexShrink: 0,
                      }} />
                      <div>
                        <p style={{ fontSize: 14, fontWeight: 700, color: C.navy, margin: 0 }}>
                          {redesignJob.status === 'queued' ? 'En cola…' : 'Analizando con IA…'}
                        </p>
                        {redesignJob.current_step && (
                          <p style={{ fontSize: 12, color: '#6B7280', margin: '4px 0 0', fontStyle: 'italic' }}>
                            {redesignJob.current_step}
                          </p>
                        )}
                      </div>
                    </div>
                    {/* Animated progress bar */}
                    <div style={{ height: 4, background: C.border, borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: '40%',
                        background: `linear-gradient(90deg, ${C.navy}, ${C.mid})`,
                        borderRadius: 4,
                        animation: 'progressSlide 1.8s ease-in-out infinite',
                      }} />
                    </div>
                    <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 10 }}>
                      Esto puede tomar 1–2 minutos. No cierres esta pestaña.
                    </p>
                    <style>{`
                      @keyframes spin { to { transform: rotate(360deg); } }
                      @keyframes progressSlide {
                        0%   { transform: translateX(-100%); }
                        50%  { transform: translateX(150%); }
                        100% { transform: translateX(150%); }
                      }
                    `}</style>
                  </div>
                );
              }

              // ── Error ───────────────────────────────────────────────────────
              if (redesignJob.status === 'error') {
                return (
                  <div style={{ maxWidth: 520 }}>
                    <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 10, padding: '20px 24px', marginBottom: 20 }}>
                      <p style={{ fontSize: 14, fontWeight: 700, color: '#B91C1C', marginBottom: 6 }}>Error en el análisis</p>
                      <p style={{ fontSize: 13, color: '#7F1D1D', margin: 0 }}>
                        {redesignJob.error ?? 'Ocurrió un error inesperado. Intenta de nuevo.'}
                      </p>
                    </div>
                    <button
                      onClick={() => { setRedesignJob(null); setRedesignDlError(false); }}
                      style={{ background: C.navy, color: C.white, border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                      Reintentar
                    </button>
                  </div>
                );
              }

              // ── Done ────────────────────────────────────────────────────────
              const result = redesignJob.result;
              if (!result) return null;
              const propuestas = result.propuestas ?? [];

              return (
                <div>
                  {/* Header resumen */}
                  <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
                    <p style={{ fontSize: 15, fontWeight: 700, color: C.navy, margin: 0 }}>
                      {result.asignaturas_analizadas} asignaturas analizadas · {propuestas.length} con propuestas de mejora
                    </p>
                    {result.advertencia && (
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: 20, padding: '3px 10px' }}>
                        ⚠ {result.advertencia}
                      </span>
                    )}
                  </div>

                  {/* Vacío */}
                  {propuestas.length === 0 && (
                    <div style={{ background: C.navyBg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '32px 24px', textAlign: 'center', marginBottom: 24 }}>
                      <p style={{ fontSize: 14, color: '#6B7280', margin: 0 }}>
                        No se identificaron asignaturas con potencial de mejora clara para este programa.
                      </p>
                    </div>
                  )}

                  {/* Cards por propuesta */}
                  {propuestas.map((prop, idx) => (
                    <ProposalCard key={idx} prop={prop} />
                  ))}

                  {/* Botón descarga */}
                  <div style={{ marginTop: 32, paddingTop: 24, borderTop: `1px solid ${C.border}` }}>
                    <button
                      onClick={downloadRedesign}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 8,
                        background: C.navy, color: C.white,
                        border: 'none', borderRadius: 8,
                        padding: '12px 24px', fontSize: 14, fontWeight: 700,
                        cursor: 'pointer',
                      }}>
                      📥 Descargar propuesta completa (.docx)
                    </button>
                    {redesignDlError && (
                      <p style={{ fontSize: 12, color: '#B91C1C', marginTop: 10, fontStyle: 'italic' }}>
                        El archivo ya no está disponible en el servidor. Vuelve a analizar para descargar.
                      </p>
                    )}
                    <button
                      onClick={() => { setRedesignJob(null); setRedesignDlError(false); }}
                      style={{
                        marginLeft: 12,
                        background: 'transparent', color: C.navy,
                        border: `1px solid ${C.border}`, borderRadius: 8,
                        padding: '12px 20px', fontSize: 13, fontWeight: 600,
                        cursor: 'pointer',
                      }}>
                      ↺ Nuevo análisis
                    </button>
                  </div>
                </div>
              );
            })()}
          </SectionBlock>

          {/* Footer */}
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: C.navy, marginBottom: 6 }}>Evidencia para la Decisión Curricular</p>
            <p style={{ fontSize: 11, color: C.mid, lineHeight: 1.6, maxWidth: 480, margin: '0 auto 12px' }}>
              Con {totales.matches.toLocaleString('es-CO')} pares analizados, este observatorio provee inteligencia curricular accionable para UNIR Colombia.
            </p>
            <p style={{ fontSize: 9, color: C.border, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Run #{d.run_id} · {d.fecha} · Motor de Pertinencia Académica v2
            </p>
          </div>

        </div>
      </main>
    </div>
  );
}
