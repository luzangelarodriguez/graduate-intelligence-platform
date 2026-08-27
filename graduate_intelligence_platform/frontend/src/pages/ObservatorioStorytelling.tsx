import { useEffect, useRef, useState } from 'react';
import { blueGradient } from '../utils/chartColors';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  ArcElement, Tooltip, Legend,
  ScatterController, PointElement,
} from 'chart.js';
import { Bar, Doughnut, Scatter } from 'react-chartjs-2';
import {
  IconGauge, IconChartBar, IconSchool, IconTarget,
  IconAlertTriangle, IconBriefcase, IconListCheck,
  IconWorld, IconChartDonut, IconClipboardList, IconCircleCheck,
  IconTool, IconBrain, IconBolt,
  type IconProps,
} from '@tabler/icons-react';
import type { ForwardRefExoticComponent, RefAttributes } from 'react';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend, ScatterController, PointElement);

// ─── Config ────────────────────────────────────────────────────────────────────
const API = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

const C = {
  navy:      '#0D2158',
  red:       '#E63329',
  bg:        '#F7F8FC',
  border:    '#E5E7EB',
  white:     '#FFFFFF',
  gold:      '#B7791F',
  goldBg:    '#FEF3C7',
  mid:       '#7B93D4',
};

// ─── Types ─────────────────────────────────────────────────────────────────────
interface Programa {
  id: number; nombre: string; matches_total: number;
  score_promedio: number; score_maximo: number;
  labels: { high: number; medium: number; low: number };
}
interface TopMatch {
  programa: string; empleo: string; empresa: string; score: number; label: string;
  skills_en_comun: string[]; skills_faltantes: string[];
}
interface Summary {
  run_id: number | null; fecha: string;
  programas: Programa[]; top_matches: TopMatch[]; skill_matches: TopMatch[];
  totales: { matches: number; alta: number; media: number; baja: number; empleos_compatibles: number };
}
interface SkillMercado  { skill: string; frecuencia: number }
interface SkillPrograma { skill: string; cobertura: number; asignaturas?: string[] }
interface Brecha        { skill: string; frecuencia_mercado: number }
interface Fortaleza     { skill: string; frecuencia_mercado: number; cobertura_programa: number }
interface Exclusiva     { skill: string; cobertura: number }
interface MatrizSkill   { skill: string; demanda_mercado: number; oferta_programa: number }
interface SkillsAnalysis {
  program_id: number;
  skills_mercado: SkillMercado[]; skills_programa: SkillPrograma[];
  brechas: Brecha[]; fortalezas: Fortaleza[]; exclusivas_programa: Exclusiva[];
  cobertura_pct: number;
  matriz_completa?: MatrizSkill[];
}
interface Competitor {
  nombre_ies: string; nombre_programa: string; ciudad: string; modalidad: string;
  nivel_academico: string; creditos: number | null; duracion: string;
  area_conocimiento: string; municipio: string; departamento: string;
  periodicidad_admision: string; matriculados: number; graduados: number; inscritos: number;
}
interface UniversityData { program_id: number; competitors: Competitor[]; total: number }
interface RAPropuesto {
  codigo: string; texto: string; tipo: 'nuevo' | 'modificado'; skills_incorporadas: string[];
}
interface RedisenioPropuesta {
  asignatura: string; relevancia_score: number; confianza: 'alta' | 'media' | 'baja';
  brechas_relevantes: string[]; ras_actuales_texto: string;
  ras_propuestos: RAPropuesto[]; skills_incorporadas: string[]; justificacion?: string;
}
interface RediseniResult {
  program_id: number; asignaturas_analizadas: number;
  propuestas: RedisenioPropuesta[]; advertencia?: string; debug?: Record<string, unknown>;
}
interface RediseniJob {
  job_id: string; status: 'queued' | 'running' | 'done' | 'error';
  current_step?: string | null; result?: RediseniResult; error?: string;
}

// ─── Static program metadata ──────────────────────────────────────────────────
const PROGRAMS = [
  { id: 94,  label: 'Visual Analytics & Big Data',    nombre: 'Especialización en Visual Analytics y Big Data', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 92,  label: 'Inteligencia Artificial',        nombre: 'Especialización en Inteligencia Artificial',     creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 108, label: 'Especialización en Criminología', nombre: 'Especialización en Criminología',               creditos: 24, duracion: '2', periodicidad: 'Semestral' },
  { id: 20,  label: 'Neuropsicología y Educación',    nombre: 'Especialización en Neuropsicología y Educación', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 9,   label: 'Dirección y Gestión de Proyectos', nombre: 'Especialización en Dirección y Gestión de Proyectos', creditos: 24, duracion: '2', periodicidad: 'Semestral' },
];

// ─── Nav items ────────────────────────────────────────────────────────────────
type ViewId = 'resumen' | 'mercado' | 'programa' | 'cobertura' | 'brechas' | 'empleos' | 'recomendaciones' | 'contexto';

const NAV_ITEMS: { id: ViewId; label: string; Icon: ForwardRefExoticComponent<IconProps & RefAttributes<SVGSVGElement>> }[] = [
  { id: 'resumen',         label: 'Resumen',         Icon: IconGauge         },
  { id: 'mercado',         label: 'Mercado',          Icon: IconChartBar      },
  { id: 'programa',        label: 'Programa',         Icon: IconSchool        },
  { id: 'cobertura',       label: 'Cobertura',        Icon: IconTarget        },
  { id: 'brechas',         label: 'Brechas',          Icon: IconAlertTriangle },
  { id: 'empleos',         label: 'Empleos',          Icon: IconBriefcase     },
  { id: 'recomendaciones', label: 'Recomendaciones',  Icon: IconListCheck     },
  { id: 'contexto',        label: 'Contexto',         Icon: IconWorld         },
];

// ─── Fallback data ─────────────────────────────────────────────────────────────
const FALLBACK: Summary = {
  run_id: 6, fecha: '2026-06-01',
  programas: [
    { id: 92,  nombre: 'Inteligencia Artificial',         matches_total: 38, score_promedio: 71.2, score_maximo: 88.4, labels: { high: 18, medium: 14, low: 6 } },
    { id: 94,  nombre: 'Visual Analytics and Big Data',   matches_total: 31, score_promedio: 68.5, score_maximo: 85.1, labels: { high: 14, medium: 12, low: 5 } },
    { id: 108, nombre: 'Especialización en Criminología', matches_total: 22, score_promedio: 52.3, score_maximo: 67.8, labels: { high: 4,  medium: 10, low: 8 } },
    { id: 20,  nombre: 'Neuropsicología y Educación',     matches_total: 0,  score_promedio: 0,    score_maximo: 0,    labels: { high: 0,  medium: 0,  low: 0 } },
    { id: 9,   nombre: 'Dirección y Gestión de Proyectos', matches_total: 0, score_promedio: 0,    score_maximo: 0,    labels: { high: 0,  medium: 0,  low: 0 } },
  ],
  top_matches: [
    { programa: 'Visual Analytics', empleo: 'Data Scientist Senior', empresa: 'Bancolombia', score: 88.4, label: 'high', skills_en_comun: ['Python', 'Machine Learning', 'SQL'], skills_faltantes: ['Spark', 'Kafka'] },
    { programa: 'Visual Analytics', empleo: 'Analista BI',           empresa: 'Rappi',       score: 85.1, label: 'high', skills_en_comun: ['Power BI', 'SQL'],                  skills_faltantes: ['dbt', 'Airflow'] },
    { programa: 'Visual Analytics', empleo: 'ML Engineer',           empresa: 'Mercado Libre', score: 83.7, label: 'high', skills_en_comun: ['TensorFlow', 'Python'],           skills_faltantes: ['Kubernetes'] },
  ],
  totales: { matches: 91, alta: 36, media: 36, baja: 19, empleos_compatibles: 3 },
  skill_matches: [],
};

const FALLBACK_SKILLS: Record<number, SkillsAnalysis> = {
  94: {
    program_id: 94, cobertura_pct: 54,
    skills_mercado:  [
      { skill: 'Python', frecuencia: 28 }, { skill: 'Power BI', frecuencia: 24 },
      { skill: 'SQL', frecuencia: 22 },    { skill: 'Tableau', frecuencia: 18 },
      { skill: 'Spark', frecuencia: 16 },  { skill: 'AWS', frecuencia: 14 },
      { skill: 'Airflow', frecuencia: 12 },{ skill: 'dbt', frecuencia: 10 },
    ],
    skills_programa: [
      { skill: 'Python', cobertura: 5 }, { skill: 'Power BI', cobertura: 4 },
      { skill: 'SQL', cobertura: 4 },    { skill: 'Tableau', cobertura: 3 },
      { skill: 'R', cobertura: 3 },      { skill: 'Estadística', cobertura: 3 },
    ],
    fortalezas:  [
      { skill: 'Python', frecuencia_mercado: 28, cobertura_programa: 5 },
      { skill: 'Power BI', frecuencia_mercado: 24, cobertura_programa: 4 },
      { skill: 'SQL', frecuencia_mercado: 22, cobertura_programa: 4 },
    ],
    brechas: [
      { skill: 'Spark', frecuencia_mercado: 16 }, { skill: 'AWS', frecuencia_mercado: 14 },
      { skill: 'Airflow', frecuencia_mercado: 12 }, { skill: 'dbt', frecuencia_mercado: 10 },
    ],
    exclusivas_programa: [{ skill: 'R', cobertura: 3 }, { skill: 'Estadística', cobertura: 3 }],
  },
  92: {
    program_id: 92, cobertura_pct: 61,
    skills_mercado:  [
      { skill: 'Python', frecuencia: 31 }, { skill: 'TensorFlow', frecuencia: 22 },
      { skill: 'Machine Learning', frecuencia: 20 }, { skill: 'PyTorch', frecuencia: 18 },
      { skill: 'SQL', frecuencia: 17 }, { skill: 'AWS', frecuencia: 15 },
    ],
    skills_programa: [
      { skill: 'Python', cobertura: 6 }, { skill: 'TensorFlow', cobertura: 5 },
      { skill: 'Machine Learning', cobertura: 5 }, { skill: 'PyTorch', cobertura: 4 },
    ],
    fortalezas: [
      { skill: 'Python', frecuencia_mercado: 31, cobertura_programa: 6 },
      { skill: 'TensorFlow', frecuencia_mercado: 22, cobertura_programa: 5 },
    ],
    brechas: [
      { skill: 'AWS', frecuencia_mercado: 15 }, { skill: 'Docker', frecuencia_mercado: 13 },
      { skill: 'Kubernetes', frecuencia_mercado: 11 },
    ],
    exclusivas_programa: [{ skill: 'Estadística', cobertura: 4 }, { skill: 'Álgebra Lineal', cobertura: 3 }],
  },
  108: {
    program_id: 108, cobertura_pct: 38,
    skills_mercado:  [
      { skill: 'Investigación', frecuencia: 18 }, { skill: 'Excel', frecuencia: 15 },
      { skill: 'Análisis datos', frecuencia: 14 }, { skill: 'Derecho Penal', frecuencia: 13 },
    ],
    skills_programa: [
      { skill: 'Investigación', cobertura: 5 }, { skill: 'Derecho Penal', cobertura: 4 },
    ],
    fortalezas: [{ skill: 'Investigación', frecuencia_mercado: 18, cobertura_programa: 5 }],
    brechas: [
      { skill: 'Análisis datos', frecuencia_mercado: 14 }, { skill: 'SPSS', frecuencia_mercado: 11 },
    ],
    exclusivas_programa: [{ skill: 'Criminología', cobertura: 4 }],
  },
  20: { program_id: 20, skills_mercado: [], skills_programa: [], brechas: [], fortalezas: [], exclusivas_programa: [], cobertura_pct: 0 },
  9:  { program_id: 9, cobertura_pct: 0, skills_mercado: [], skills_programa: [], brechas: [], fortalezas: [], exclusivas_programa: [] },
};

// ─── Pertinencia scale ─────────────────────────────────────────────────────────
function pertinenciaLevel(score: number): { label: string; color: string; bg: string; desc: string } {
  if (score >= 75) return { label: 'Excelente', color: '#059669', bg: '#d1fae5', desc: 'El currículo está muy bien alineado con las demandas actuales del mercado laboral.' };
  if (score >= 60) return { label: 'Buena',     color: '#2563eb', bg: '#dbeafe', desc: 'Buena alineación general; existen oportunidades de fortalecimiento en áreas específicas.' };
  if (score >= 40) return { label: 'Moderada',  color: C.gold,   bg: C.goldBg,  desc: 'Alineación parcial. Se recomienda actualización curricular prioritaria.' };
  return              { label: 'Crítica',   color: '#dc2626', bg: '#fee2e2', desc: 'Brecha significativa entre el currículo y las competencias demandadas por el mercado.' };
}

// ─── Skill normalization + classification ─────────────────────────────────────
const SKILL_ALIASES: Record<string, string> = { 'powerbi': 'power bi', 'power-bi': 'power bi', 'rstudio': 'r', 'r studio': 'r' };
function normalizeSkill(s: string): string {
  const lower = s.toLowerCase().replace(/\s+/g, ' ').trim();
  return SKILL_ALIASES[lower] ?? lower;
}

const SKILL_CATS = {
  herramienta: new Set([
    // Languages & runtimes
    'python','sql','r','java','javascript','typescript','scala','c++','c#','go','kotlin','matlab','node','nodejs','node.js','php','ruby','swift',
    // BI & viz tools
    'power bi','tableau','looker','qlik','metabase','grafana','excel','powerpoint','word','google sheets',
    // Cloud & infra
    'aws','azure','gcp','google cloud','docker','kubernetes','terraform','ansible','linux','unix','bash','shell',
    // Data & ML frameworks
    'spark','hadoop','databricks','tensorflow','pytorch','sklearn','scikit-learn','keras','xgboost','lightgbm','hugging face','langchain','openai',
    // Databases
    'postgresql','mysql','mongodb','redis','elasticsearch','oracle','snowflake','bigquery','dbt','cassandra','dynamodb','hive',
    // Data tools
    'kafka','airflow','luigi','prefect','numpy','pandas','scipy','statsmodels','jupyter','colab','streamlit','fastapi','django','flask','react','angular','vue',
    // Dev tools
    'git','github','jenkins','gitlab','jira','confluence','sharepoint','figma',
    // ERP / vertical tools
    'sap','salesforce','crm','erp','power automate','zapier',
    // Psych assessment tools
    'spss','wais','wisc','rorschach','bender','rstudio','powerbi','sas',
    // Security tools
    'nmap','wireshark','metasploit','burp suite','splunk','siem',
  ]),
  competencia: new Set([
    // Data science
    'machine learning','deep learning','nlp','procesamiento lenguaje natural','data visualization','visualizacion de datos','big data','etl','business intelligence','analisis de datos','data engineering','mlops','estadistica','data warehouse','data lake','cloud computing','feature engineering','computer vision','forecasting','data governance','data mining','series de tiempo','inteligencia artificial','ciencia de datos','analítica avanzada','analitica de datos',
    // Cybersecurity
    'seguridad informatica','ciberseguridad','security','seguridad','hacking etico','pentesting','riesgos informaticos','criptografia','redes','networking',
    // DevOps / Arch
    'devops','mlops','arquitectura de software','microservicios','api rest','api','microservices','sistemas distribuidos','data architecture',
    // Methodology
    'pmbok','lean','scrum','agile','six sigma','metodologia','kanban','design thinking','gestion de proyectos',
    // Psychology competences
    'neuropsicolog','neuropsicologia','cognitiv','funciones ejecutivas','evaluacion','intervencion','psicodiagnostico','psicometria','aprendizaje','memoria','atencion','percepcion','lenguaje','trastorno','discapacidad','rehabilitacion','psicologia','diagnostico','neuropsi',
    // Legal/criminology
    'derecho penal','investigacion criminal','criminologia','criminalistica','peritaje','victimologia',
    // General
    'analisis','investigacion','redaccion','escritura','excel avanzado','elaboracion de informes',
  ]),
  habilidad: new Set([
    'gestion','liderazgo','comunicacion','trabajo en equipo','pensamiento critico','innovacion','negociacion','planeacion','orientacion a resultados','toma de decisiones','resolucion de problemas','adaptabilidad','creatividad','empatia','servicio al cliente','orientacion','diversidad','inclusion','desarrollo','inteligencia emocional','pedagogia','docencia','didactica','ensenanza','formacion','facilitacion','presentaciones','relaciones interpersonales','trabajo bajo presion','autonomia','proactividad',
    // Education-specific
    'educacion','orientacion vocacional','coaching','mentoría',
  ]),
};
type SkillCat = 'herramienta' | 'competencia' | 'habilidad' | 'otro';
function classifySkill(s: string): SkillCat {
  const key = normalizeSkill(s);
  if (SKILL_CATS.herramienta.has(key)) return 'herramienta';
  if (SKILL_CATS.competencia.has(key))  return 'competencia';
  if (SKILL_CATS.habilidad.has(key))    return 'habilidad';
  for (const cat of ['herramienta', 'competencia', 'habilidad'] as ('herramienta' | 'competencia' | 'habilidad')[]) {
    for (const term of SKILL_CATS[cat]) {
      if (term.length >= 6 && (key.startsWith(term) || term.startsWith(key))) return cat;
    }
  }
  return 'otro';
}
const CAT_META: Record<SkillCat, { label: string; color: string; bar: string }> = {
  herramienta: { label: 'Herramientas', color: '#2563EB', bar: '#3B82F6' },
  competencia:  { label: 'Competencias', color: '#059669', bar: '#10B981' },
  habilidad:    { label: 'Habilidades',  color: '#D97706', bar: '#F59E0B' },
  otro:         { label: 'Otros',        color: '#64748B', bar: '#94A3B8' },
};

// ─── Shared UI components ─────────────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="w-8 h-8 rounded-full border-4 border-blue-200 border-t-blue-800 animate-spin" />
    </div>
  );
}

function ExplorandoMsg() {
  return (
    <div style={{ textAlign: 'center', padding: '32px 16px', background: '#F8F9FC', borderRadius: 8, border: '1px dashed #D8DEF0' }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>🔍</div>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#334670', marginBottom: 6 }}>Mercado laboral en exploración</div>
      <div style={{ fontSize: 12, color: '#6B7A9E', maxWidth: 360, margin: '0 auto', lineHeight: 1.6 }}>
        La oferta digital para este perfil en Colombia es limitada. Los datos estarán disponibles en la próxima adquisición.
      </div>
    </div>
  );
}

function SkillTag({ skill, variant = 'default' }: { skill: string; variant?: 'default' | 'gap' | 'match' }) {
  if (variant === 'gap')
    return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626', border: '1px solid rgba(220,38,38,0.25)' }}>− {skill}</span>;
  if (variant === 'match')
    return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: 'rgba(5,150,105,0.1)', color: '#059669', border: '1px solid rgba(5,150,105,0.25)' }}>✓ {skill}</span>;
  const m = CAT_META[classifySkill(skill)];
  return <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: `${m.bar}22`, color: m.color, border: `1px solid ${m.bar}44` }}>{skill}</span>;
}

function ProposalCard({ prop }: { prop: RedisenioPropuesta }) {
  const [expanded, setExpanded] = useState(false);
  const confStyle: Record<string, { bg: string; color: string; label: string }> = {
    alta:  { bg: '#D1FAE5', color: '#065F46', label: 'Confianza alta'  },
    media: { bg: '#FEF3C7', color: '#92400E', label: 'Confianza media' },
    baja:  { bg: '#F3F4F6', color: '#374151', label: 'Confianza baja'  },
  };
  const conf = confStyle[prop.confianza] ?? confStyle.baja;
  const TRUNCATE = 300;
  const truncated = prop.ras_actuales_texto.length > TRUNCATE && !expanded;
  const displayText = truncated ? prop.ras_actuales_texto.slice(0, TRUNCATE) + '…' : prop.ras_actuales_texto;
  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 12, overflow: 'hidden', marginBottom: 16, background: C.white }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: `1px solid ${C.border}`, background: '#F9FAFB' }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: C.navy, margin: 0 }}>{prop.asignatura}</p>
        <span style={{ fontSize: 10, fontWeight: 700, background: conf.bg, color: conf.color, borderRadius: 20, padding: '2px 8px' }}>{conf.label}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
        <div style={{ padding: '14px 16px', borderRight: `1px solid ${C.border}`, background: '#F9FAFB' }}>
          <p style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: '#6B7280', marginBottom: 8 }}>RAs Actuales</p>
          <p style={{ fontSize: 11, color: '#374151', lineHeight: 1.7, margin: 0, whiteSpace: 'pre-wrap' as const }}>{displayText}</p>
          {prop.ras_actuales_texto.length > TRUNCATE && (
            <button onClick={() => setExpanded(e => !e)} style={{ marginTop: 6, fontSize: 10, color: C.navy, fontWeight: 700, background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}>
              {expanded ? 'Ver menos ▲' : 'Ver más ▼'}
            </button>
          )}
        </div>
        <div style={{ padding: '14px 16px', background: '#F0FDF4' }}>
          <p style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: '#065F46', marginBottom: 8 }}>RAs Propuestos</p>
          {prop.ras_propuestos.length === 0 ? (
            <p style={{ fontSize: 11, color: '#6B7280', fontStyle: 'italic', margin: 0 }}>Ninguna brecha coherente con esta asignatura.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {prop.ras_propuestos.map((ra, i) => (
                <div key={i} style={{ paddingBottom: 12, borderBottom: i < prop.ras_propuestos.length - 1 ? '1px solid #BBF7D0' : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span style={{ fontSize: 10, fontWeight: 800, color: '#065F46' }}>{ra.codigo}</span>
                    <span style={{ fontSize: 9, fontWeight: 700, background: ra.tipo === 'nuevo' ? '#DCFCE7' : '#E0F2FE', color: ra.tipo === 'nuevo' ? '#166534' : '#075985', borderRadius: 20, padding: '1px 7px' }}>{ra.tipo}</span>
                  </div>
                  <p style={{ fontSize: 11, color: '#166534', lineHeight: 1.6, margin: '0 0 6px' }}>{ra.texto}</p>
                  {ra.skills_incorporadas.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {ra.skills_incorporadas.map((s, si) => (
                        <span key={si} style={{ fontSize: 9, background: '#D1FAE5', color: '#065F46', borderRadius: 20, padding: '1px 7px', fontWeight: 600 }}>{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {(prop.justificacion || prop.brechas_relevantes.length > 0) && (
        <div style={{ padding: '10px 16px', borderTop: `1px solid ${C.border}`, background: C.white }}>
          {prop.justificacion && <p style={{ fontSize: 10, color: '#6B7280', fontStyle: 'italic', margin: '0 0 6px' }}>{prop.justificacion}</p>}
          {prop.brechas_relevantes.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: '#6B7280', alignSelf: 'center', marginRight: 4 }}>Brechas:</span>
              {prop.brechas_relevantes.slice(0, 5).map((b, bi) => (
                <span key={bi} style={{ fontSize: 9, background: '#EEF2FB', color: C.navy, borderRadius: 20, padding: '1px 7px', fontWeight: 600 }}>{b}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Chart.js wrappers ─────────────────────────────────────────────────────────

function HorizBarChart({ labels, values, color, valueLabel = 'vacantes' }: {
  labels: string[]; values: number[]; color?: string | string[]; valueLabel?: string;
}) {
  const bg = color ?? blueGradient(values.length);
  const data = {
    labels,
    datasets: [{ data: values, backgroundColor: bg, borderRadius: 4, barThickness: 14 }],
  };
  const options = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (c: { raw: unknown }) => ` ${c.raw} ${valueLabel}` } },
    },
    scales: {
      x: { grid: { color: '#F3F4F6' }, ticks: { font: { size: 10 }, color: '#9CA3AF' } },
      y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#374151' } },
    },
  };
  return <Bar data={data} options={options} />;
}

function DonutChart({ labels, values, colors }: { labels: string[]; values: number[]; colors: string[] }) {
  const data = {
    labels,
    datasets: [{ data: values, backgroundColor: colors, borderWidth: 0, hoverOffset: 4 }],
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' as const, labels: { font: { size: 10 }, padding: 10, boxWidth: 10 } },
      tooltip: { callbacks: { label: (c: { label: string; raw: unknown }) => ` ${c.label}: ${c.raw}` } },
    },
    cutout: '62%',
  };
  return <Doughnut data={data} options={options} />;
}

function SkillScatter({ matriz }: { matriz: MatrizSkill[] }) {
  if (matriz.length === 0) return <p style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center', paddingTop: 20 }}>Sin datos de matriz</p>;

  const medX = [...matriz].sort((a, b) => a.demanda_mercado - b.demanda_mercado)[Math.floor(matriz.length / 2)]?.demanda_mercado ?? 0;
  const medY = [...matriz].sort((a, b) => a.oferta_programa - b.oferta_programa)[Math.floor(matriz.length / 2)]?.oferta_programa ?? 0;

  const quadrant = (d: number, o: number) => {
    if (d >= medX && o >= medY) return { color: '#059669', q: 'Bien cubiertas' };
    if (d >= medX && o < medY)  return { color: '#EF4444', q: 'Brecha crítica' };
    if (d < medX  && o >= medY) return { color: '#2563EB', q: 'Exclusiva prog.' };
    return { color: '#9CA3AF', q: 'Sin relevancia' };
  };

  // Group by quadrant color for datasets (Chart.js scatter needs datasets per color)
  const groups: Record<string, { label: string; color: string; points: { x: number; y: number; skill: string }[] }> = {
    green: { label: 'Bien cubiertas',  color: '#059669', points: [] },
    red:   { label: 'Brechas críticas', color: '#EF4444', points: [] },
    blue:  { label: 'Exclusivas prog.', color: '#2563EB', points: [] },
    gray:  { label: 'Sin relevancia',  color: '#9CA3AF', points: [] },
  };
  for (const m of matriz) {
    const { q } = quadrant(m.demanda_mercado, m.oferta_programa);
    const key = q === 'Bien cubiertas' ? 'green' : q === 'Brecha crítica' ? 'red' : q === 'Exclusiva prog.' ? 'blue' : 'gray';
    groups[key].points.push({ x: m.demanda_mercado, y: m.oferta_programa, skill: m.skill });
  }

  const datasets = Object.values(groups).map(g => ({
    label: g.label,
    data: g.points,
    backgroundColor: g.color + 'CC',
    borderColor: g.color,
    borderWidth: 1,
    pointRadius: 5,
    pointHoverRadius: 7,
  }));

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' as const, labels: { font: { size: 10 }, boxWidth: 10, padding: 10 } },
      tooltip: {
        callbacks: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          label: (ctx: any) =>
            `${(ctx.raw as { skill?: string }).skill ?? ''} — Demanda: ${ctx.raw.x} vac / Oferta: ${ctx.raw.y} mat`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Demanda del mercado (vacantes)', font: { size: 10 }, color: '#9CA3AF' },
        grid: { color: '#F3F4F6' },
        ticks: { font: { size: 10 }, color: '#9CA3AF' },
      },
      y: {
        title: { display: true, text: 'Oferta del programa (materias)', font: { size: 10 }, color: '#9CA3AF' },
        grid: { color: '#F3F4F6' },
        ticks: { font: { size: 10 }, color: '#9CA3AF' },
      },
    },
  };

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      {/* Quadrant labels */}
      <div style={{ position: 'absolute', top: 6, right: 10, fontSize: 9, fontWeight: 700, color: '#059669', opacity: 0.7, pointerEvents: 'none' }}>Bien cubiertas ↑</div>
      <div style={{ position: 'absolute', bottom: 28, right: 10, fontSize: 9, fontWeight: 700, color: '#EF4444', opacity: 0.7, pointerEvents: 'none' }}>Brechas críticas ↘</div>
      <div style={{ position: 'absolute', top: 6, left: 52, fontSize: 9, fontWeight: 700, color: '#2563EB', opacity: 0.7, pointerEvents: 'none' }}>Exclusivas ↑</div>
      <div style={{ position: 'absolute', bottom: 28, left: 52, fontSize: 9, fontWeight: 700, color: '#9CA3AF', opacity: 0.7, pointerEvents: 'none' }}>Sin relevancia</div>
      <Scatter data={{ datasets }} options={options} />
    </div>
  );
}

// ─── Dashboard primitives ─────────────────────────────────────────────────────

function isNoiseSkill(skill: string): boolean {
  return skill.length > 40 || skill.toLowerCase().includes('confianza extraccion');
}

function SkillBarList({ items, color, valueLabel = 'vacantes' }: {
  items: { label: string; value: number }[];
  color: string;
  valueLabel?: string;
}) {
  const max = Math.max(...items.map(i => i.value), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
      {items.map(({ label, value }) => (
        <div key={label} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', alignItems: 'center', gap: 8 }}>
          <span title={label} style={{ fontSize: 11, color: '#4B5563', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
          <div style={{ height: 7, borderRadius: 6, background: '#E5E7EB', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(value / max) * 100}%`, borderRadius: 6, background: color }} />
          </div>
          <span title={`${value} ${valueLabel}`} style={{ fontSize: 10, color: '#9CA3AF', minWidth: 22, textAlign: 'right' }}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function DashPanel({ title, children, style, className, badge }: {
  title: string; children: React.ReactNode; style?: React.CSSProperties; className?: string; badge?: string | number;
}) {
  return (
    <div className={className} style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: '1.1rem 1.25rem', display: 'flex', flexDirection: 'column', ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#9CA3AF', margin: 0 }}>{title}</p>
        {badge !== undefined && (
          <span style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', background: '#F3F4F6', borderRadius: 20, padding: '2px 7px', whiteSpace: 'nowrap' }}>{badge}</span>
        )}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
}

function MetricCard({ label, value, badge, color = C.navy, sub }: {
  label: string; value: string | number; badge?: string; color?: string; sub?: string;
}) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: '14px 16px' }}>
      <p style={{ fontSize: 10, fontWeight: 600, color: '#9CA3AF', margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</p>
      <p style={{ fontSize: 28, fontWeight: 800, color, margin: 0, lineHeight: 1 }}>{value}</p>
      {badge && <span style={{ display: 'inline-block', marginTop: 6, fontSize: 11, fontWeight: 700, background: `${color}22`, color, borderRadius: 20, padding: '2px 10px' }}>{badge}</span>}
      {sub && <p style={{ fontSize: 11, color: '#6B7280', margin: '4px 0 0' }}>{sub}</p>}
    </div>
  );
}

// ─── Views ────────────────────────────────────────────────────────────────────

interface ViewProps {
  summary: Summary;
  prog: Programa;
  meta: typeof PROGRAMS[0];
  score: number;
  nivel: ReturnType<typeof pertinenciaLevel>;
  coberturaPct: number;
  brechaPct: number;
  empCompatibles: number;
  skills: SkillsAnalysis | null;
  skillsMercadoDeduped: SkillMercado[];
  univ: UniversityData | null;
  totales: Summary['totales'];
  top_matches: TopMatch[];
  skill_matches: TopMatch[];
  dataPobre: boolean;
  programaId: number;
  redesignJob: RediseniJob | null;
  redesignDlError: boolean;
  onStartRedesign: () => void;
  onDownloadRedesign: () => void;
  onClearRedesign: () => void;
}

function ViewResumen({ summary, prog, meta, score, nivel, coberturaPct, empCompatibles, skills, skillsMercadoDeduped, univ, totales, dataPobre }: ViewProps) {
  const topMarket  = skillsMercadoDeduped.slice(0, 8);
  const topBrechas = [...(skills?.brechas ?? [])].sort((a, b) => (b.frecuencia_mercado ?? 0) - (a.frecuencia_mercado ?? 0)).slice(0, 6);

  // Curriculum composition counts
  const compCount: Record<string, number> = { Herramientas: 0, Competencias: 0, Habilidades: 0, Otros: 0 };
  if (skills) {
    for (const s of skills.skills_programa) {
      const cat = CAT_META[classifySkill(s.skill)].label;
      compCount[cat] = (compCount[cat] ?? 0) + 1;
    }
  }

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 flex-shrink-0">
        <div>
          <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: 0, lineHeight: 1.2 }}>{meta.nombre}</h1>
          <p style={{ fontSize: 11, color: '#9CA3AF', margin: '3px 0 0' }}>
            {totales.matches} vacantes analizadas · Run #{summary.run_id} · {summary.fecha}
          </p>
        </div>
        <span style={{ fontSize: 9, fontWeight: 800, border: '1px solid #D1D5DB', color: '#9CA3AF', borderRadius: 20, padding: '3px 10px', letterSpacing: '0.1em', textTransform: 'uppercase', flexShrink: 0 }}>
          {prog?.labels?.high ?? 0}↑ · {prog?.labels?.medium ?? 0}→ · {prog?.labels?.low ?? 0}↓
        </span>
      </div>

      {/* 4 KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 flex-shrink-0">
        <MetricCard label="Pertinencia" value={`${score.toFixed(0)}/100`} badge={nivel.label} color={nivel.color} />
        <MetricCard label="Cobertura curricular" value={`${coberturaPct}%`} color="#2563EB" />
        <MetricCard label="Empleos compatibles" value={empCompatibles} color="#059669" />
        <MetricCard label="Brechas detectadas" value={skills?.brechas.length ?? '—'} color="#DC2626" />
      </div>

      {dataPobre ? (
        <ExplorandoMsg />
      ) : (
        <>
          {/* Row 2: market skills + curriculum donut */}
          <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-2.5 flex-shrink-0">
            <DashPanel title="Top Skills del Mercado">
              <div style={{ height: 190 }}>
                {topMarket.length > 0
                  ? <HorizBarChart labels={topMarket.map(s => s.skill)} values={topMarket.map(s => s.frecuencia)} />
                  : <Spinner />}
              </div>
            </DashPanel>
            <DashPanel title="Composición Curricular">
              <div style={{ height: 190 }}>
                {skills
                  ? <DonutChart
                      labels={['Herramientas', 'Competencias', 'Habilidades', 'Otros']}
                      values={[compCount.Herramientas, compCount.Competencias, compCount.Habilidades, compCount.Otros]}
                      colors={blueGradient(4)}
                    />
                  : <Spinner />}
              </div>
            </DashPanel>
          </div>

          {/* Row 3: priority gaps + SNIES */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5 flex-shrink-0">
            <DashPanel title="Brechas Prioritarias">
              <div style={{ height: 160 }}>
                {topBrechas.length > 0
                  ? <HorizBarChart labels={topBrechas.map(b => b.skill)} values={topBrechas.map(b => b.frecuencia_mercado ?? 0)} color="#EF4444" />
                  : <p style={{ fontSize: 12, color: '#6B7280', textAlign: 'center', paddingTop: 20 }}>Sin brechas críticas identificadas ✓</p>}
              </div>
            </DashPanel>
            <DashPanel title="Benchmark SNIES">
              {!univ || univ.competitors.length === 0 ? (
                <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>Sin programas similares en SNIES.</p>
              ) : (
                <div style={{ overflowY: 'auto', overflowX: 'auto', maxHeight: 160 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, minWidth: 280 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '3px 6px', color: '#9CA3AF', fontWeight: 600, fontSize: 9, textTransform: 'uppercase' }}>Universidad</th>
                        <th style={{ textAlign: 'right', padding: '3px 6px', color: '#9CA3AF', fontWeight: 600, fontSize: 9 }}>Matr.</th>
                        <th style={{ textAlign: 'right', padding: '3px 6px', color: '#9CA3AF', fontWeight: 600, fontSize: 9 }}>Grad.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {univ.competitors.slice(0, 6).map((c, i) => (
                        <tr key={i} style={{ borderTop: '1px solid #F3F4F6' }}>
                          <td style={{ padding: '5px 6px', color: '#374151', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.nombre_ies}</td>
                          <td style={{ padding: '5px 6px', textAlign: 'right', fontWeight: 700, color: C.navy }}>{(c.matriculados ?? 0).toLocaleString('es-CO')}</td>
                          <td style={{ padding: '5px 6px', textAlign: 'right', color: '#6B7280' }}>{(c.graduados ?? 0).toLocaleString('es-CO')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </DashPanel>
          </div>
        </>
      )}
    </div>
  );
}

function ViewMercado({ skills, skillsMercadoDeduped, totales, dataPobre }: ViewProps) {
  if (dataPobre) return <div style={{ padding: 24 }}><ExplorandoMsg /></div>;
  if (!skills)   return <div style={{ padding: 24 }}><Spinner /></div>;

  const bycat: Record<SkillCat, SkillMercado[]> = { herramienta: [], competencia: [], habilidad: [], otro: [] };
  for (const s of skillsMercadoDeduped) bycat[classifySkill(s.skill)].push(s);

  const ALL_CATS: SkillCat[] = ['herramienta', 'competencia', 'habilidad', 'otro'];
  const cols: { cat: SkillCat; items: SkillMercado[] }[] = ALL_CATS
    .map(cat => ({ cat, items: bycat[cat].slice(0, 10) }))
    .filter(({ cat, items }) => items.length > 0 || cat !== 'otro');

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Qué Demanda el Mercado</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
          {skillsMercadoDeduped.length} skills en vacantes compatibles con el programa
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" style={{ minHeight: 0 }}>
        {cols.map(({ cat, items }) => {
          const m = CAT_META[cat];
          const isEmpty = items.length === 0;
          return (
            <DashPanel
              key={cat}
              title={m.label}
              badge={`${bycat[cat].length} identificadas`}
              className={isEmpty ? 'min-h-[90px] lg:min-h-[320px]' : undefined}
              style={isEmpty ? undefined : { minHeight: 320 }}
            >
              {isEmpty ? (
                <div className="flex items-center justify-center flex-1">
                  <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin datos suficientes</p>
                </div>
              ) : (
                <SkillBarList
                  items={items.map(s => ({ label: s.skill, value: s.frecuencia }))}
                  color={m.bar}
                />
              )}
            </DashPanel>
          );
        })}
      </div>
    </div>
  );
}

function ViewPrograma({ skills, dataPobre }: ViewProps) {
  if (!skills) return <div style={{ padding: 24 }}><Spinner /></div>;

  const bycat: Record<SkillCat, SkillPrograma[]> = { herramienta: [], competencia: [], habilidad: [], otro: [] };
  for (const s of skills.skills_programa) bycat[classifySkill(s.skill)].push(s);

  const ALL_CATS_P: SkillCat[] = ['herramienta', 'competencia', 'habilidad', 'otro'];
  const cols: { cat: SkillCat; items: SkillPrograma[] }[] = ALL_CATS_P
    .map(cat => ({ cat, items: bycat[cat].slice(0, 10) }))
    .filter(({ cat, items }) => items.length > 0 || cat !== 'otro');

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Qué Enseña el Programa</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>{skills.skills_programa.length} competencias en el microcurrículo · Tamaño = presencia (materias)</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" style={{ minHeight: 0 }}>
        {cols.map(({ cat, items }) => {
          const m = CAT_META[cat];
          const isEmpty = items.length === 0;
          return (
            <DashPanel
              key={cat}
              title={m.label}
              className={isEmpty ? 'min-h-[90px] lg:min-h-[280px]' : undefined}
              style={isEmpty ? undefined : { minHeight: 280 }}
            >
              {isEmpty ? (
                <div className="flex items-center justify-center flex-1">
                  <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin datos</p>
                </div>
              ) : (
                <div style={{ height: Math.max(items.length * 26 + 20, 200) }}>
                  <HorizBarChart
                    labels={items.map(s => s.skill)}
                    values={items.map(s => s.cobertura)}
                    valueLabel="materias"
                    color={cat === 'otro' ? '#94A3B8' : undefined}
                  />
                </div>
              )}
            </DashPanel>
          );
        })}
      </div>
    </div>
  );
}

function ViewCobertura({ coberturaPct, skills, univ, dataPobre }: ViewProps) {
  if (dataPobre) return <div style={{ padding: 24 }}><ExplorandoMsg /></div>;
  if (!skills)   return <div style={{ padding: 24 }}><Spinner /></div>;

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Cobertura Curricular</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>% de las skills del mercado que el programa ya cubre</p>
      </div>

      {/* Donut + stats: apilados en móvil, 220px+1fr en desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-3 flex-shrink-0">
        {/* Donut coverage */}
        <DashPanel title="Cobertura">
          <div style={{ height: 180 }}>
            <DonutChart
              labels={['Cubiertas', 'Brechas']}
              values={[coberturaPct, 100 - coberturaPct]}
              colors={['#10B981', '#FCA5A5']}
            />
          </div>
        </DashPanel>

        {/* Stats: 3 KPIs + fortalezas */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5" style={{ alignContent: 'start' }}>
          <MetricCard label="Cobertura" value={`${coberturaPct}%`} color="#059669" />
          <MetricCard label="Skills cubiertas" value={skills.fortalezas.length} color="#2563EB" />
          <MetricCard label="Brechas" value={skills.brechas.length} color="#DC2626" />
          <div className="sm:col-span-3">
            <DashPanel title="Fortalezas (en programa y en mercado)">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {skills.fortalezas.slice(0, 12).map(f => <SkillTag key={f.skill} skill={f.skill} variant="match" />)}
              </div>
            </DashPanel>
          </div>
        </div>
      </div>

      {/* SNIES table — 5 cols, scroll horizontal contenido.
          TODO(verificación visual pendiente): con datos SNIES reales en producción,
          verificar layout de la tabla con filas pobladas en 375px/768px/1440px. */}
      <DashPanel title={univ && univ.competitors.length > 0 ? `Benchmark SNIES — ${univ.total} programas similares activos` : 'Benchmark SNIES'}>
        {!univ ? (
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0, fontStyle: 'italic' }}>Cargando datos institucionales…</p>
        ) : univ.competitors.length === 0 ? (
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0, fontStyle: 'italic' }}>Sin programas similares en SNIES para este programa.</p>
        ) : (
          <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: 220 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 540 }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                  {['Universidad', 'Programa', 'Modalidad', 'Matr.', 'Grad.'].map(h => (
                    <th key={h} style={{ textAlign: h === 'Matr.' || h === 'Grad.' ? 'right' : 'left', padding: '4px 8px', color: '#9CA3AF', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {univ.competitors.slice(0, 12).map((c, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}`, background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                    <td style={{ padding: '6px 8px', color: '#374151', fontWeight: 600, whiteSpace: 'nowrap' }}>{c.nombre_ies}</td>
                    <td style={{ padding: '6px 8px', color: '#6B7280', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.nombre_programa}</td>
                    <td style={{ padding: '6px 8px', color: '#6B7280', whiteSpace: 'nowrap' }}>{c.modalidad}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, color: C.navy, whiteSpace: 'nowrap' }}>{(c.matriculados ?? 0).toLocaleString('es-CO')}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#6B7280', whiteSpace: 'nowrap' }}>{(c.graduados ?? 0).toLocaleString('es-CO')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DashPanel>
    </div>
  );
}

// ─── BrechasScatter ───────────────────────────────────────────────────────────
function BrechasScatter({ matriz, topThirdDemand }: { matriz: MatrizSkill[]; topThirdDemand: number }) {
  const QUAD_COLORS = {
    verde: { color: '#0ca30c', label: 'Bien cubiertas' },
    rojo:  { color: '#d03b3b', label: 'Brechas críticas' },
    azul:  { color: '#2a78d6', label: 'En desarrollo' },
    gris:  { color: '#898781', label: 'Sin relevancia' },
  } as const;
  type QKey = keyof typeof QUAD_COLORS;

  const groups: Record<QKey, { x: number; y: number; skill: string }[]> = { verde: [], rojo: [], azul: [], gris: [] };
  for (const m of matriz) {
    let key: QKey;
    if (m.demanda_mercado > 0 && m.oferta_programa > 0) key = 'verde';
    else if (topThirdDemand > 0 && m.demanda_mercado >= topThirdDemand && m.oferta_programa === 0) key = 'rojo';
    else if (m.demanda_mercado > 0 && m.oferta_programa === 0) key = 'azul';
    else key = 'gris';
    groups[key].push({ x: m.demanda_mercado, y: m.oferta_programa, skill: m.skill });
  }

  const datasets = (Object.keys(QUAD_COLORS) as QKey[]).map(k => ({
    label: QUAD_COLORS[k].label,
    data: groups[k],
    backgroundColor: QUAD_COLORS[k].color + 'CC',
    borderColor: QUAD_COLORS[k].color,
    borderWidth: 1,
    pointRadius: 5,
    pointHoverRadius: 7,
  }));

  const options = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      tooltip: { callbacks: { label: (ctx: any) => `${(ctx.raw as { skill?: string }).skill ?? ''} — Demanda: ${ctx.raw.x} · Cobertura: ${ctx.raw.y}` } },
    },
    scales: {
      x: { title: { display: true, text: 'Demanda del mercado (cuartiles)', font: { size: 10 }, color: '#9CA3AF' }, grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } },
      y: { title: { display: true, text: 'Cobertura en el currículo (0-10)', font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' }, ticks: { font: { size: 10 }, color: '#9CA3AF' } },
    },
  };

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', marginBottom: 10 }}>
        {(Object.keys(QUAD_COLORS) as QKey[]).map(k => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: QUAD_COLORS[k].color }} />
            <span style={{ fontSize: 10, color: '#6B7280' }}>{QUAD_COLORS[k].label}</span>
          </div>
        ))}
      </div>
      <div style={{ height: 300 }}>
        <Scatter data={{ datasets }} options={options} />
      </div>
    </div>
  );
}

function ViewBrechas({ skills, coberturaPct, dataPobre }: ViewProps) {
  if (dataPobre) return <div style={{ padding: 24 }}><ExplorandoMsg /></div>;
  if (!skills)   return <div style={{ padding: 24 }}><Spinner /></div>;

  const rawBrechas = skills.brechas.filter(b => !isNoiseSkill(b.skill));

  if (rawBrechas.length === 0) return (
    <div style={{ padding: 24 }}>
      <div style={{ background: '#D1FAE5', border: '1px solid #6EE7B7', borderRadius: 12, padding: '24px', textAlign: 'center' }}>
        <p style={{ fontSize: 15, fontWeight: 700, color: '#065F46' }}>✓ Sin brechas críticas identificadas</p>
        <p style={{ fontSize: 12, color: '#059669', margin: '6px 0 0' }}>El programa cubre las principales skills del mercado.</p>
      </div>
    </div>
  );

  const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

  const sorted = [...rawBrechas].sort((a, b) => (b.frecuencia_mercado ?? 0) - (a.frecuencia_mercado ?? 0));
  const bycat: Record<SkillCat, Brecha[]> = { herramienta: [], competencia: [], habilidad: [], otro: [] };
  for (const b of sorted) bycat[classifySkill(b.skill)].push(b);

  // Top-third threshold for "alta prioridad"
  const topThirdIdx = Math.max(0, Math.floor(sorted.length * 2 / 3));
  const topThirdThreshold = sorted[topThirdIdx]?.frecuencia_mercado ?? 0;
  const brechasAlta = sorted.filter(b => (b.frecuencia_mercado ?? 0) > topThirdThreshold);

  // KPI values
  const matriz = skills.matriz_completa ?? [];
  const skillsAnalizadas = matriz.length || rawBrechas.length + skills.fortalezas.length;
  const wellCovered = skills.fortalezas.length;
  const topBrechas = sorted.slice(0, 4);
  const topBrecha = sorted[0];

  // Scatter top-third demand threshold
  const demandsSorted = [...matriz.map(m => m.demanda_mercado)].sort((a, b) => a - b);
  const scatterTopThird = demandsSorted[Math.floor(demandsSorted.length * 2 / 3)] ?? 1;

  const CAT_ICONS: Record<SkillCat, React.ReactNode> = {
    herramienta: <IconTool size={16} />,
    competencia:  <IconBrain size={16} />,
    habilidad:    <IconBolt size={16} />,
    otro:         <IconListCheck size={16} />,
  };

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>

      {/* Header */}
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Brechas Curriculares</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
          {sorted.length} skills demandadas que el programa no cubre · {brechasAlta.length} de prioridad alta
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" style={{ flexShrink: 0 }}>
        {[
          { label: 'Índice de alineación', value: `${coberturaPct}%`,    Icon: IconChartDonut,    iconBg: '#E6F1FB', iconColor: '#0C447C', valueColor: C.navy  },
          { label: 'Skills analizadas',    value: skillsAnalizadas,      Icon: IconClipboardList, iconBg: '#E6F1FB', iconColor: '#0C447C', valueColor: C.navy  },
          { label: 'Brechas prioritarias', value: brechasAlta.length,    Icon: IconAlertTriangle, iconBg: '#FCEBEB', iconColor: '#791F1F', valueColor: '#C0392B' },
          { label: 'Skills bien cubiertas',value: wellCovered,            Icon: IconCircleCheck,   iconBg: '#EAF3DE', iconColor: '#27500A', valueColor: '#27500A' },
        ].map(({ label, value, Icon, iconBg, iconColor, valueColor }) => (
          <div key={label} style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: iconColor, flexShrink: 0 }}>
              <Icon size={18} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: valueColor, lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 3, fontWeight: 500 }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" style={{ flexShrink: 0 }}>
        {(['herramienta', 'competencia', 'habilidad', 'otro'] as SkillCat[]).filter(c => bycat[c].length > 0 || c !== 'otro').map(cat => {
          const m = CAT_META[cat];
          const items = bycat[cat];
          const isEmpty = items.length === 0;
          return (
            <DashPanel
              key={cat}
              title={m.label}
              badge={`${items.length} brechas`}
              className={isEmpty ? 'min-h-[90px] lg:min-h-[200px]' : undefined}
              style={isEmpty ? undefined : { minHeight: 200 }}
            >
              {isEmpty ? (
                <div className="flex items-center justify-center flex-1">
                  <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin brechas en esta categoría</p>
                </div>
              ) : (
                <SkillBarList
                  items={items.map(b => ({ label: cap(b.skill), value: b.frecuencia_mercado ?? 0 }))}
                  color={m.bar}
                  valueLabel="vacantes"
                />
              )}
            </DashPanel>
          );
        })}
      </div>

      {/* Prioridades de intervención */}
      {topBrechas.length > 0 && (
        <DashPanel title="Prioridades de intervención" style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {topBrechas.map((b, i) => {
              const isAlta = i < 2;
              const cat = classifySkill(b.skill);
              const m = CAT_META[cat];
              const desc = i === 0
                ? 'Mayor brecha detectada — alta demanda sin cobertura curricular'
                : i === 1
                ? 'Alta demanda del mercado, sin presencia en el microcurrículo'
                : 'Demanda media — oportunidad de incorporación gradual';
              return (
                <div key={b.skill} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: '#F9FAFB', borderRadius: 8 }}>
                  <div style={{ width: 34, height: 34, borderRadius: '50%', background: `${m.bar}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: m.color, flexShrink: 0 }}>
                    {CAT_ICONS[cat]}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.navy }}>{cap(b.skill)}</div>
                    <div style={{ fontSize: 11, color: '#6B7280', marginTop: 1 }}>{desc}</div>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, borderRadius: 20, padding: '3px 9px', whiteSpace: 'nowrap', flexShrink: 0, background: isAlta ? '#FEE2E2' : '#FEF3C7', color: isAlta ? '#B91C1C' : '#92400E' }}>
                    {isAlta ? 'Alta prioridad' : 'Media prioridad'}
                  </span>
                </div>
              );
            })}
          </div>
        </DashPanel>
      )}

      {/* Recomendación ejecutiva */}
      {topBrecha && (
        <div style={{ background: '#EAF3DE', border: '1px solid #B7E08A', borderRadius: 12, padding: '14px 18px', display: 'flex', gap: 12, alignItems: 'flex-start', flexShrink: 0 }}>
          <div style={{ color: '#27500A', flexShrink: 0, marginTop: 1 }}><IconTarget size={19} /></div>
          <p style={{ fontSize: 13, color: '#27500A', margin: 0, lineHeight: 1.65 }}>
            <strong>Recomendación:</strong> Enfocar recursos en <strong>{cap(topBrecha.skill)}</strong> para mejorar la alineación del programa con las demandas del mercado. Esta skill aparece en {topBrecha.frecuencia_mercado ?? 0} vacantes compatibles y actualmente no tiene cobertura curricular.
          </p>
        </div>
      )}

      {/* Skills diferenciadoras */}
      {skills.exclusivas_programa.length > 0 && (
        <DashPanel title="Skills diferenciadoras del programa" style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {[...skills.exclusivas_programa].sort((a, b) => b.cobertura - a.cobertura).slice(0, 8).map(e => (
              <span key={e.skill} style={{ fontSize: 12, color: C.navy, background: 'transparent', border: '0.5px solid #93C5FD', borderRadius: 8, padding: '5px 12px', fontWeight: 500 }}>{cap(e.skill)}</span>
            ))}
          </div>
          <p style={{ fontSize: 10, color: '#9CA3AF', margin: '8px 0 0' }}>Skills presentes en el programa sin demanda de mercado detectada — pueden ser relevantes en nichos emergentes.</p>
        </DashPanel>
      )}

      {/* Mapa currículo vs mercado */}
      {matriz.length > 0 && (
        <DashPanel title="Mapa currículo vs mercado" style={{ flexShrink: 0 }}>
          <BrechasScatter matriz={matriz} topThirdDemand={scatterTopThird} />
        </DashPanel>
      )}
    </div>
  );
}
function ViewEmpleos({ skill_matches, empCompatibles }: ViewProps) {
  // skill_matches comes from the backend pre-filtered (skills_en_comun non-empty), ordered by score DESC.
  const empleos = skill_matches.slice(0, 10);

  if (empleos.length === 0) return (
    <div style={{ padding: 24 }}>
      <div style={{ background: '#F3F4F6', borderRadius: 12, padding: 32, textAlign: 'center' }}>
        <p style={{ fontSize: 14, color: '#6B7280' }}>Sin empleos con solapamiento de skills para este programa.</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Empleos Compatibles</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>{empCompatibles} vacantes con solapamiento de skills</p>
      </div>

      <DashPanel title={`Top ${empleos.length} vacantes más compatibles`}>
        {/* TODO(verificación visual pendiente): con datos reales de vacantes en producción,
            verificar layout de las columnas "Skills en común" y "Gaps" con tags reales en 375px. */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 640 }}>
            <thead>
              <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                {['#', 'Empleo', 'Empresa', 'Score', 'Cobertura', 'Skills en común', 'Gaps'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '4px 8px', color: '#9CA3AF', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {empleos.map((m, i) => {
                const total    = m.skills_en_comun.length + m.skills_faltantes.length;
                const coverPct = total ? Math.round((m.skills_en_comun.length / total) * 100) : 0;
                return (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}`, background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                    <td style={{ padding: '8px', color: '#9CA3AF', fontWeight: 700, fontSize: 11, whiteSpace: 'nowrap' }}>{i + 1}</td>
                    <td style={{ padding: '8px', color: C.navy, fontWeight: 600, whiteSpace: 'nowrap' }}>{m.empleo}</td>
                    <td style={{ padding: '8px', color: '#6B7280', whiteSpace: 'nowrap' }}>{m.empresa}</td>
                    <td style={{ padding: '8px', fontWeight: 700, whiteSpace: 'nowrap', color: m.score >= 70 ? '#059669' : m.score >= 50 ? '#2563EB' : '#D97706' }}>{m.score.toFixed(0)}</td>
                    <td style={{ padding: '8px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 56, height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${coverPct}%`, background: coverPct >= 60 ? '#10B981' : '#F59E0B', borderRadius: 3 }} />
                        </div>
                        <span style={{ fontSize: 10, fontWeight: 700, color: coverPct >= 60 ? '#059669' : '#D97706' }}>{coverPct}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '8px', minWidth: 120 }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                        {m.skills_en_comun.slice(0, 3).map(s => <SkillTag key={s} skill={s} variant="match" />)}
                      </div>
                    </td>
                    <td style={{ padding: '8px', minWidth: 100 }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                        {m.skills_faltantes.slice(0, 2).map(s => <SkillTag key={s} skill={s} variant="gap" />)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </DashPanel>
    </div>
  );
}

function ViewRecomendaciones({
  skills, score, nivel, coberturaPct, brechaPct, empCompatibles, dataPobre,
  redesignJob, redesignDlError, onStartRedesign, onDownloadRedesign, onClearRedesign,
}: ViewProps) {
  const topBrechas   = [...(skills?.brechas ?? [])].sort((a, b) => (b.frecuencia_mercado ?? 0) - (a.frecuencia_mercado ?? 0));
  const brechasAlta  = topBrechas.filter(b => b.frecuencia_mercado >= 10);
  const topFortalezas = [...(skills?.fortalezas ?? [])].sort((a, b) => b.cobertura_programa - a.cobertura_programa);
  const ruido = (skills?.brechas ?? []).filter(b => classifySkill(b.skill) === 'otro' && (b.frecuencia_mercado ?? 0) < 3);

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Recomendaciones & Rediseño</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>Simulación, acciones prioritarias y rediseño curricular asistido por IA</p>
      </div>

      {dataPobre ? <ExplorandoMsg /> : (
        <>
          {/* Simulation scenarios */}
          <DashPanel title="Simulación Curricular — Impacto estimado de incorporar brechas" style={{ flexShrink: 0 }}>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {[
                { title: 'Escenario A — Mínimo',   sub: `Incorporar top ${Math.min(brechasAlta.length, 2)} brechas críticas`,         pertinencia: `+${Math.round(brechaPct * 0.25)}%`, cobertura: `${Math.min(coberturaPct + 15, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.2)}`, color: C.gold },
                { title: 'Escenario B — Moderado', sub: `Incorporar brechas de prioridad alta (${brechasAlta.length})`,                pertinencia: `+${Math.round(brechaPct * 0.45)}%`, cobertura: `${Math.min(coberturaPct + 25, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.4)}`, color: '#2563eb' },
                { title: 'Escenario C — Completo', sub: `Incorporar todas las brechas (${skills?.brechas.length ?? '—'})`,             pertinencia: `+${Math.round(brechaPct * 0.70)}%`, cobertura: `${Math.min(coberturaPct + 40, 99)}%`, empleos: `+${Math.round(empCompatibles * 0.65)}`, color: '#059669' },
              ].map(sc => (
                <div key={sc.title} style={{ border: `1px solid ${sc.color}44`, borderRadius: 10, padding: '12px 14px', background: `${sc.color}08` }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: sc.color, margin: '0 0 4px' }}>{sc.title}</p>
                  <p style={{ fontSize: 10, color: '#6B7280', margin: '0 0 10px' }}>{sc.sub}</p>
                  {[{ k: 'Pertinencia', v: sc.pertinencia }, { k: 'Cobertura', v: sc.cobertura }, { k: 'Empleos comp.', v: sc.empleos }].map(({ k, v }) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                      <span style={{ color: '#6B7280' }}>{k}</span>
                      <span style={{ fontWeight: 700, color: sc.color }}>{v}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </DashPanel>

          {/* Recommendations */}
          {skills && (skills.brechas.length > 0 || skills.fortalezas.length > 0) && (
            <DashPanel title="Acciones Prioritarias">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {topBrechas.slice(0, 3).map(b => (
                  <div key={b.skill} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8 }}>
                    <span style={{ fontSize: 16, flexShrink: 0 }}>⚠</span>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 12, fontWeight: 700, color: '#B91C1C', margin: '0 0 2px' }}>Incorporar "{b.skill}"</p>
                      <p style={{ fontSize: 11, color: '#7F1D1D', margin: 0 }}>{b.frecuencia_mercado} vacantes lo demandan — no está cubierto en el currículo.</p>
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 800, color: '#DC2626', background: '#FEE2E2', borderRadius: 20, padding: '2px 8px', flexShrink: 0, whiteSpace: 'nowrap' }}>
                      {b.frecuencia_mercado >= 10 ? 'Urgente' : 'Alta'}
                    </span>
                  </div>
                ))}
                {topFortalezas.slice(0, 2).map(f => (
                  <div key={f.skill} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8 }}>
                    <span style={{ fontSize: 16, flexShrink: 0 }}>💪</span>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 12, fontWeight: 700, color: '#1D4ED8', margin: '0 0 2px' }}>Profundizar "{f.skill}"</p>
                      <p style={{ fontSize: 11, color: '#1E40AF', margin: 0 }}>En {f.cobertura_programa} materias y demandado en {f.frecuencia_mercado} vacantes. Diferenciador potencial.</p>
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#2563EB', background: '#DBEAFE', borderRadius: 20, padding: '2px 8px', flexShrink: 0 }}>Media</span>
                  </div>
                ))}
                {ruido.length > 0 && (
                  <div style={{ padding: '10px 12px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8 }}>
                    <p style={{ fontSize: 11, fontWeight: 700, color: '#92400E', margin: '0 0 2px' }}>⚠ Verificar antes de incorporar: {ruido.slice(0, 3).map(b => `"${b.skill}"`).join(', ')}</p>
                    <p style={{ fontSize: 10, color: '#78350F', margin: 0 }}>Pocas vacantes y sin categoría clara — pueden ser ruido contextual.</p>
                  </div>
                )}
              </div>
            </DashPanel>
          )}
        </>
      )}

      {/* Redesign section */}
      <DashPanel title="Rediseño Curricular Asistido por IA">
        {(!redesignJob || redesignJob.job_id === '') ? (
          <div>
            <p style={{ fontSize: 12, color: '#4B5563', lineHeight: 1.7, marginBottom: 14 }}>
              Analiza los microcurrículos contra las brechas detectadas y genera propuestas de nuevos Resultados de Aprendizaje (RAs) por asignatura.
            </p>
            <button
              onClick={onStartRedesign}
              disabled={redesignJob?.status === 'queued' && redesignJob.job_id === ''}
              style={{ background: C.navy, color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
              🔬 Analizar y proponer mejoras curriculares
            </button>
          </div>
        ) : redesignJob.status === 'queued' || redesignJob.status === 'running' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="w-8 h-8 rounded-full border-4 border-blue-200 border-t-blue-800 animate-spin flex-shrink-0" />
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: C.navy, margin: 0 }}>{redesignJob.status === 'queued' ? 'En cola…' : 'Analizando con IA…'}</p>
              {redesignJob.current_step && <p style={{ fontSize: 11, color: '#6B7280', margin: '3px 0 0', fontStyle: 'italic' }}>{redesignJob.current_step}</p>}
            </div>
          </div>
        ) : redesignJob.status === 'error' ? (
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#B91C1C', marginBottom: 6 }}>Error: {redesignJob.error ?? 'Ocurrió un error inesperado.'}</p>
            <button onClick={onClearRedesign} style={{ background: C.navy, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Reintentar</button>
          </div>
        ) : redesignJob.result ? (() => {
          const { result } = redesignJob;
          const propuestas = result.propuestas ?? [];
          return (
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: C.navy, marginBottom: 12 }}>
                {result.asignaturas_analizadas} asignaturas · {propuestas.length} con propuestas
                {result.advertencia && <span style={{ fontSize: 10, color: '#92400E', background: '#FEF3C7', borderRadius: 20, padding: '2px 8px', marginLeft: 8 }}>⚠ {result.advertencia}</span>}
              </p>
              {propuestas.map((prop, idx) => <ProposalCard key={idx} prop={prop} />)}
              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button onClick={onDownloadRedesign} style={{ background: C.navy, color: '#fff', border: 'none', borderRadius: 8, padding: '10px 18px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                  📥 Descargar (.docx)
                </button>
                <button onClick={onClearRedesign} style={{ background: 'transparent', color: C.navy, border: `1px solid ${C.border}`, borderRadius: 8, padding: '10px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                  ↺ Nuevo análisis
                </button>
              </div>
              {redesignDlError && <p style={{ fontSize: 11, color: '#B91C1C', marginTop: 8, fontStyle: 'italic' }}>Archivo no disponible. Vuelve a analizar para descargar.</p>}
            </div>
          );
        })() : null}
      </DashPanel>
    </div>
  );
}

// ─── Market context static studies ───────────────────────────────────────────
const MARKET_STUDIES = [
  {
    icon: '🌐',
    title: 'World Economic Forum — Future of Jobs Report 2025',
    summary: 'La IA y el análisis de grandes datos encabezan la lista de habilidades de más rápido crecimiento a nivel global, seguidas de ciberseguridad y alfabetización tecnológica. Se proyecta que el 40% de las habilidades requeridas en el trabajo cambiarán para 2030, y el 63% de los empleadores ya identifican la brecha de habilidades como su principal barrera de transformación.',
    url: 'https://www.weforum.org/publications/the-future-of-jobs-report-2025',
    source: 'weforum.org · 2025',
  },
  {
    icon: '🇨🇴',
    title: 'OLE Colombia — Observatorio Laboral para la Educación',
    summary: 'Sistema oficial del gobierno colombiano que hace seguimiento a la inserción laboral de graduados de educación superior, midiendo la pertinencia entre la oferta educativa y la demanda real del mercado laboral nacional.',
    url: 'https://ole.mineducacion.gov.co',
    source: 'ole.mineducacion.gov.co · MEN',
  },
  {
    icon: '📊',
    title: 'Adecco Colombia — Tendencias del Mercado Laboral 2026',
    summary: 'El mercado laboral colombiano en 2026 prioriza la productividad sobre el volumen de contratación, impulsado por la aceleración de la IA y automatización. Las empresas están invirtiendo en upskilling y migrando hacia modelos de selección basados en competencias medibles.',
    url: 'https://www.eltiempo.com',
    source: 'El Tiempo · feb 2026',
  },
];

// ─── WEF domain detection (mirrors backend logic) ────────────────────────────
function detectDominio(nombre: string): 'datos_ia' | 'juridico_social' | 'salud_educacion' | 'otro' {
  const n = nombre.toLowerCase();
  if (/dato|analítica|analytics|inteligencia artificial|\bia\b|machine|big data/.test(n)) return 'datos_ia';
  if (/crimin|victimol|derecho|juridic|penal/.test(n)) return 'juridico_social';
  if (/neuropsicol|psicol|educaci|pedagog|clíni/.test(n)) return 'salud_educacion';
  return 'otro';
}

// ─── WEF Chart components ─────────────────────────────────────────────────────

const SRC_WEF = 'Fuente: WEF Future of Jobs Report 2025';

function WefSourceNote({ fig }: { fig: string }) {
  return (
    <p style={{ fontSize: 9, color: '#9CA3AF', margin: '8px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      {SRC_WEF} — {fig}
    </p>
  );
}

// G1: Disruption KPI cards (Colombia vs global)
function WefG1Disruption() {
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 12px' }}>
        Disrupción de habilidades: Colombia vs. mundo
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { val: '41%', label: 'de las competencias laborales cambiarán', sub: 'Colombia 2025-2030', color: '#2563EB' },
          { val: '39%', label: 'de las competencias laborales cambiarán', sub: 'Promedio global',     color: '#7C3AED' },
          { val: '+2 pts', label: 'Colombia por encima del promedio mundial', sub: 'Diferencia',      color: '#DC2626' },
        ].map(k => (
          <div key={k.sub} style={{ textAlign: 'center', padding: '12px 8px', borderRadius: 10, background: `${k.color}08`, border: `1px solid ${k.color}22` }}>
            <p style={{ fontSize: 26, fontWeight: 900, color: k.color, margin: '0 0 4px', lineHeight: 1 }}>{k.val}</p>
            <p style={{ fontSize: 10, color: '#374151', margin: '0 0 4px', lineHeight: 1.4 }}>{k.label}</p>
            <span style={{ fontSize: 9, fontWeight: 700, color: k.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k.sub}</span>
          </div>
        ))}
      </div>
      <WefSourceNote fig="Figura 3.2" />
    </div>
  );
}

// G2: Skills en auge vs. en declive (barras horizontales)
function WefG2SkillsTrends() {
  const items = [
    { label: 'IA y big data',                            val: 87  },
    { label: 'Redes y ciberseguridad',                   val: 70  },
    { label: 'Alfabetización tecnológica',               val: 68  },
    { label: 'Pensamiento creativo',                     val: 66  },
    { label: 'Resiliencia, flexibilidad y agilidad',     val: 66  },
    { label: 'Gestión del talento',                      val: 58  },
    { label: 'Pensamiento analítico',                    val: 55  },
    { label: 'Gestión ambiental',                        val: 53  },
    { label: 'Lectoescritura y matemáticas',             val:  -4 },
    { label: 'Destreza manual / resistencia / precisión',val: -24 },
  ];
  const data = {
    labels: items.map(i => i.label),
    datasets: [{
      data: items.map(i => i.val),
      backgroundColor: items.map(i => i.val >= 0 ? '#1D9E75' : '#D85A30'),
      borderRadius: 4,
    }],
  };
  const opts = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: {
      label: (ctx: { raw: unknown }) => ` ${ctx.raw}% aumento neto`,
    }}},
    scales: {
      x: { min: -30, max: 100, ticks: { font: { size: 10 }, callback: (v: unknown) => `${v}%` }, grid: { color: '#F1F5F9' } },
      y: { ticks: { font: { size: 10 }, color: '#374151' }, grid: { display: false } },
    },
  };
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 12px' }}>
        Qué habilidades están creciendo y cuáles están cayendo a nivel global
      </p>
      <div style={{ display: 'flex', gap: 12, fontSize: 9, fontWeight: 700, marginBottom: 8 }}>
        <span style={{ color: '#1D9E75' }}>▮ En auge</span>
        <span style={{ color: '#D85A30' }}>▮ En declive</span>
      </div>
      <div style={{ height: 270 }}>
        <Bar data={data} options={opts} />
      </div>
      <WefSourceNote fig="Figura 3.4" />
    </div>
  );
}

// G3: Balance global de empleos
function WefG3JobBalance() {
  const created = 170, displaced = 92, total = created + displaced;
  const pctCreated = (created / total * 100).toFixed(1);
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 12px' }}>
        Empleos creados vs. desplazados a nivel global, 2025-2030
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" style={{ marginBottom: 14 }}>
        {[
          { val: '170M', label: '14% del empleo formal actual', sub: 'Empleos creados',    color: '#1D9E75' },
          { val: '92M',  label: '8% del empleo formal actual',  sub: 'Empleos desplazados', color: '#D85A30' },
          { val: '+78M', label: '7% de crecimiento neto a 2030', sub: 'Crecimiento neto',  color: '#2563EB' },
        ].map(k => (
          <div key={k.sub} style={{ textAlign: 'center', padding: '10px 6px', borderRadius: 10, background: `${k.color}08`, border: `1px solid ${k.color}22` }}>
            <p style={{ fontSize: 22, fontWeight: 900, color: k.color, margin: '0 0 4px', lineHeight: 1 }}>{k.val}</p>
            <p style={{ fontSize: 10, color: '#374151', margin: '0 0 4px', lineHeight: 1.3 }}>{k.label}</p>
            <span style={{ fontSize: 9, fontWeight: 700, color: k.color, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{k.sub}</span>
          </div>
        ))}
      </div>
      {/* Proportional bar */}
      <div style={{ height: 14, borderRadius: 7, overflow: 'hidden', display: 'flex', background: '#F1F5F9' }}>
        <div style={{ width: `${pctCreated}%`, background: '#1D9E75', transition: 'width 0.6s ease' }} />
        <div style={{ flex: 1, background: '#D85A30' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 9, color: '#1D9E75', fontWeight: 700 }}>Creados {pctCreated}%</span>
        <span style={{ fontSize: 9, color: '#D85A30', fontWeight: 700 }}>Desplazados {(100 - parseFloat(pctCreated)).toFixed(1)}%</span>
      </div>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '10px 0 0', lineHeight: 1.5, fontStyle: 'italic' }}>
        El 22% del empleo formal global (1,2 mil millones de puestos analizados) estará en movimiento hacia 2030.
      </p>
      <WefSourceNote fig="Figura 2.1 · OIT" />
    </div>
  );
}

// G4: Top skills crecimiento (dominio datos/IA) — resalta las tech en azul
function WefG4DatosIA() {
  const items = [
    { label: 'IA y big data',                        val: 87, tech: true  },
    { label: 'Redes y ciberseguridad',               val: 70, tech: true  },
    { label: 'Alfabetización tecnológica',           val: 68, tech: true  },
    { label: 'Pensamiento creativo',                 val: 66, tech: false },
    { label: 'Resiliencia y agilidad',               val: 66, tech: false },
    { label: 'Curiosidad y aprendizaje continuo',    val: 61, tech: false },
    { label: 'Liderazgo e influencia social',        val: 58, tech: false },
    { label: 'Gestión del talento',                  val: 58, tech: false },
    { label: 'Pensamiento analítico',                val: 55, tech: false },
    { label: 'Gestión ambiental',                    val: 53, tech: false },
  ];
  const data = {
    labels: items.map(i => i.label),
    datasets: [{
      data: items.map(i => i.val),
      backgroundColor: items.map(i => i.tech ? '#378ADD' : '#888780'),
      borderRadius: 4,
    }],
  };
  const opts = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: {
      label: (ctx: { raw: unknown }) => ` ${ctx.raw}% aumento neto`,
    }}},
    scales: {
      x: { min: 0, max: 100, ticks: { font: { size: 10 }, callback: (v: unknown) => `${v}%` }, grid: { color: '#F1F5F9' } },
      y: { ticks: { font: { size: 10 }, color: '#374151' }, grid: { display: false } },
    },
  };
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 4px' }}>
        Habilidades de más rápido crecimiento global
      </p>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '0 0 10px' }}>Relevante para este programa — habilidades tecnológicas destacadas en azul</p>
      <div style={{ display: 'flex', gap: 12, fontSize: 9, fontWeight: 700, marginBottom: 8 }}>
        <span style={{ color: '#378ADD' }}>▮ Tecnológicas (relevantes para este programa)</span>
        <span style={{ color: '#888780' }}>▮ Transversales</span>
      </div>
      <div style={{ height: 260 }}>
        <Bar data={data} options={opts} />
      </div>
      <WefSourceNote fig="Figura 3.4" />
    </div>
  );
}

// G5: Empleos de cuidado y educación (dominio salud/educación) — barras cualitativas
function WefG5SaludEducacion() {
  const items = [
    { label: 'Profesionales de enfermería',                    color: '#5DCAA5' },
    { label: 'Trabajo social y consejería',                    color: '#5DCAA5' },
    { label: 'Docentes universitarios / educación superior',   color: '#7F77DD' },
    { label: 'Docentes de educación secundaria',               color: '#7F77DD' },
  ];
  const data = {
    labels: items.map(i => i.label),
    datasets: [{
      data: [100, 100, 100, 100],
      backgroundColor: items.map(i => i.color),
      borderRadius: 4,
    }],
  };
  const opts = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: () => ' Top 15 empleos de mayor crecimiento absoluto a 2030' } },
    },
    scales: {
      x: { display: false },
      y: { ticks: { font: { size: 11 }, color: '#374151' }, grid: { display: false } },
    },
  };
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 4px' }}>
        Empleos de cuidado y educación entre los de mayor crecimiento
      </p>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '0 0 10px' }}>Relevante para este programa</p>
      <div style={{ display: 'flex', gap: 12, fontSize: 9, fontWeight: 700, marginBottom: 8 }}>
        <span style={{ color: '#5DCAA5' }}>▮ Cuidado / salud</span>
        <span style={{ color: '#7F77DD' }}>▮ Educación</span>
      </div>
      <div style={{ height: 150 }}>
        <Bar data={data} options={opts} />
      </div>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '10px 0 0', lineHeight: 1.5, fontStyle: 'italic' }}>
        Las cuatro ocupaciones figuran dentro de los 15 empleos de mayor crecimiento absoluto proyectados para 2030 a nivel global.
      </p>
      <WefSourceNote fig="Figura 2.4" />
    </div>
  );
}

// G6: Roles de seguridad (dominio jurídico/social) — barras por posición en ranking
function WefG6SeguridadJuridico() {
  // Position in top-15 ranking → bar length = 15 - position + 1 (inverted so lower position = longer bar)
  const items = [
    { label: 'Security management specialists', pos: 5,  color: '#D85A30' },
    { label: 'Information security analysts',   pos: 13, color: '#F0997B' },
  ];
  const data = {
    labels: items.map(i => i.label),
    datasets: [{
      data: items.map(i => 16 - i.pos), // pos 5 → length 11, pos 13 → length 3
      backgroundColor: items.map(i => i.color),
      borderRadius: 4,
    }],
  };
  const opts = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: {
        label: (ctx: { dataIndex: number }) => ` Posición #${items[ctx.dataIndex].pos} de 15 en crecimiento porcentual global`,
      }},
    },
    scales: {
      x: { display: false, min: 0, max: 15 },
      y: { ticks: { font: { size: 11 }, color: '#374151' }, grid: { display: false } },
    },
  };
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid #E5E7EB`, padding: '16px 20px' }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 4px' }}>
        Roles de seguridad entre los de mayor crecimiento porcentual
      </p>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '0 0 10px' }}>Relevante para este programa</p>
      <div style={{ display: 'flex', gap: 12, fontSize: 9, fontWeight: 700, marginBottom: 8 }}>
        <span style={{ color: '#D85A30' }}>▮ Mayor crecimiento</span>
        <span style={{ color: '#F0997B' }}>▮ Crecimiento significativo</span>
      </div>
      <div style={{ height: 110 }}>
        <Bar data={data} options={opts} />
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
        {items.map(i => (
          <span key={i.label} style={{ fontSize: 10, color: i.color, fontWeight: 700 }}>
            {i.label}: #{i.pos}/15
          </span>
        ))}
      </div>
      <p style={{ fontSize: 10, color: '#6B7280', margin: '10px 0 0', lineHeight: 1.5, fontStyle: 'italic' }}>
        Ambos roles figuran en el top 15 global de empleos de más rápido crecimiento porcentual a 2030, impulsados por el aumento de tensiones geopolíticas y de fragmentación tecnológica.
      </p>
      <WefSourceNote fig="Figura 2.2" />
    </div>
  );
}

// ─── WEF Charts section (3 general + 1 conditional) ──────────────────────────
function WefChartsSection({ nombrePrograma }: { nombrePrograma: string }) {
  const dominio = detectDominio(nombrePrograma);
  return (
    <div className="flex flex-col gap-3">
      <p style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', margin: 0, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
        Visualizaciones WEF Future of Jobs Report 2025
      </p>
      {/* G1+G3 apilados a la izquierda, G2 a la derecha — en móvil todo apilado en 1 col */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="flex flex-col gap-3">
          <WefG1Disruption />
          <WefG3JobBalance />
        </div>
        <WefG2SkillsTrends />
      </div>
      {/* Gráfico condicional por dominio */}
      {dominio === 'datos_ia'          && <WefG4DatosIA />}
      {dominio === 'salud_educacion'   && <WefG5SaludEducacion />}
      {dominio === 'juridico_social'   && <WefG6SeguridadJuridico />}
    </div>
  );
}

function ViewContexto({ meta, programaId, score, skills }: ViewProps) {
  const [analisis, setAnalisis]   = useState<string | null>(null);
  const [loading, setLoading]     = useState(false);
  const [generated, setGenerated] = useState<string | null>(null);
  const [aiError, setAiError]     = useState(false);

  const hasBrechas = (skills?.brechas?.length ?? 0) > 0;

  function generate() {
    setLoading(true); setAiError(false);
    fetch(`${API}/api/dashboard/market-context/${programaId}`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: { analisis: string; generado_en: string; error?: boolean }) => {
        setAnalisis(d.analisis);
        setGenerated(d.generado_en ? new Date(d.generado_en).toLocaleString('es-CO') : null);
        setAiError(!!d.error);
        setLoading(false);
      })
      .catch(() => { setAiError(true); setAnalisis('Error de conexión: no se pudo contactar el servidor. Verifica que el servicio esté disponible e inténtalo de nuevo.'); setLoading(false); });
  }

  return (
    <div className="flex flex-col gap-3 lg:h-full lg:overflow-y-auto" style={{ padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Contexto de Mercado — Estudios de Referencia</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>Hallazgos de informes externos + análisis personalizado por IA para {meta.label}</p>
      </div>

      {/* Parte A — 3 static study cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" style={{ flexShrink: 0 }}>
        {MARKET_STUDIES.map(s => (
          <div key={s.title} style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 20 }}>{s.icon}</span>
              <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: 0, lineHeight: 1.3 }}>{s.title}</p>
            </div>
            <p style={{ fontSize: 11, color: '#374151', fontStyle: 'italic', lineHeight: 1.7, margin: 0, flex: 1 }}>"{s.summary}"</p>
            <a href={s.url} target="_blank" rel="noopener noreferrer"
               style={{ fontSize: 9, fontWeight: 700, color: '#6B7280', textDecoration: 'none', textTransform: 'uppercase', letterSpacing: '0.06em', borderTop: `1px solid ${C.border}`, paddingTop: 8, marginTop: 4 }}>
              📎 {s.source}
            </a>
          </div>
        ))}
      </div>

      {/* WEF Charts — 3 generales + 1 condicional por dominio */}
      <WefChartsSection nombrePrograma={meta.nombre} />

      {/* Parte B — AI personalized analysis */}
      <div style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: '18px 20px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div>
            <p style={{ fontSize: 12, fontWeight: 700, color: C.navy, margin: '0 0 2px' }}>
              Análisis personalizado IA — {meta.nombre}
            </p>
            <p style={{ fontSize: 10, color: '#9CA3AF', margin: 0 }}>
              Conecta los estudios anteriores con la situación específica de este programa (score: {score.toFixed(0)}/100)
            </p>
          </div>
          {!loading && (
            <button
              onClick={generate}
              style={{ background: C.navy, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer', flexShrink: 0 }}>
              {analisis ? '↺ Regenerar' : '✨ Generar análisis'}
            </button>
          )}
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 0' }}>
            <div className="w-6 h-6 rounded-full border-4 border-blue-200 border-t-blue-800 animate-spin flex-shrink-0" />
            <p style={{ fontSize: 12, color: '#6B7280', margin: 0, fontStyle: 'italic' }}>Consultando estudios y generando análisis…</p>
          </div>
        ) : analisis ? (
          <div>
            {aiError ? (
              <p style={{ fontSize: 12, color: '#B91C1C', margin: 0 }}>{analisis}</p>
            ) : (
              <div style={{ background: '#F8FAFC', borderRadius: 8, borderLeft: `4px solid ${C.navy}`, padding: '14px 16px' }}>
                <p style={{ fontSize: 13, color: '#1E293B', lineHeight: 1.8, margin: 0 }}>{analisis}</p>
              </div>
            )}
            {generated && <p style={{ fontSize: 9, color: '#9CA3AF', margin: '8px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Generado: {generated}</p>}
          </div>
        ) : (
          <div style={{ background: '#F8FAFC', borderRadius: 8, border: `1px dashed ${C.border}`, padding: '24px', textAlign: 'center' }}>
            <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0 }}>
              {hasBrechas
                ? `Haz clic en "Generar análisis" para obtener un diagnóstico personalizado basado en las ${skills!.brechas.length} brechas y ${skills!.fortalezas.length} fortalezas de este programa.`
                : 'Carga los datos del programa primero para habilitar el análisis personalizado.'}
            </p>
          </div>
        )}
      </div>

      {/* Quick reference bullets */}
      <DashPanel title="Indicadores clave de los estudios">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: '39%',   desc: 'de las habilidades laborales cambiarán a nivel global para 2030', color: '#2563EB', source: 'WEF 2025' },
            { label: '170M',  desc: 'empleos nuevos netos proyectados globalmente para 2030', color: '#059669', source: 'WEF 2025' },
            { label: '91,3%', desc: 'tasa de vinculación laboral de graduados de posgrado en Colombia (2023)', color: '#7C3AED', source: 'OLE MEN 2023' },
          ].map(kpi => (
            <div key={kpi.label} style={{ textAlign: 'center', padding: '12px 8px', borderRadius: 10, background: `${kpi.color}08`, border: `1px solid ${kpi.color}22` }}>
              <p style={{ fontSize: 28, fontWeight: 900, color: kpi.color, margin: '0 0 6px', lineHeight: 1 }}>{kpi.label}</p>
              <p style={{ fontSize: 11, color: '#374151', margin: '0 0 4px', lineHeight: 1.4 }}>{kpi.desc}</p>
              <span style={{ fontSize: 9, fontWeight: 700, color: kpi.color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{kpi.source}</span>
            </div>
          ))}
        </div>
      </DashPanel>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ObservatorioStorytelling() {
  const [summary, setSummary]               = useState<Summary | null>(null);
  const [skills, setSkills]                 = useState<SkillsAnalysis | null>(null);
  const [univ, setUniv]                     = useState<UniversityData | null>(null);
  const [loading, setLoading]               = useState(true);
  const [isFallback, setIsFallback]         = useState(false);
  const [programaId, setProgramaId]         = useState(94);
  const [activeView, setActiveView]         = useState<ViewId>('resumen');
  const [pipelineLogOpen, setPipelineLogOpen] = useState(false);
  const [pipelineStatus, setPipelineStatus]   = useState<string>('idle');
  const [pipelineStep, setPipelineStep]       = useState<string | null>(null);
  const [redesignJob, setRedesignJob]         = useState<RediseniJob | null>(null);
  const [redesignDlError, setRedesignDlError] = useState(false);
  const [sidebarOpen, setSidebarOpen]         = useState(false);
  const pollRef         = useRef<ReturnType<typeof setInterval> | null>(null);
  const redesignPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch summary
  useEffect(() => {
    setLoading(true); setIsFallback(false);
    fetch(`${API}/api/dashboard/summary?program_id=${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: Summary) => { setSummary(d); setLoading(false); })
      .catch(() => {
        const fb = { ...FALLBACK, programas: FALLBACK.programas.filter(p => p.id === programaId) };
        const prog = fb.programas[0];
        if (prog) fb.totales = { matches: prog.matches_total, alta: prog.labels.high, media: prog.labels.medium, baja: prog.labels.low, empleos_compatibles: 0 };
        setSummary(fb); setIsFallback(true); setLoading(false);
      });
  }, [programaId]);

  // Fetch skills
  useEffect(() => {
    setSkills(null);
    fetch(`${API}/api/dashboard/skills-analysis/${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: SkillsAnalysis) => setSkills(d))
      .catch(() => setSkills(FALLBACK_SKILLS[programaId] ?? null));
  }, [programaId]);

  // Fetch universities
  useEffect(() => {
    setUniv(null);
    fetch(`${API}/api/programs/related-universities/${programaId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: UniversityData) => setUniv(d))
      .catch(() => setUniv(null));
  }, [programaId]);

  // Reset redesign on program change
  useEffect(() => {
    setRedesignJob(null); setRedesignDlError(false);
    if (redesignPollRef.current) { clearInterval(redesignPollRef.current); redesignPollRef.current = null; }
  }, [programaId]);

  useEffect(() => () => { if (redesignPollRef.current) clearInterval(redesignPollRef.current); }, []);

  function startRedesign() {
    setRedesignDlError(false);
    setRedesignJob({ job_id: '', status: 'queued', current_step: 'Iniciando análisis…' });
    fetch(`${API}/api/curriculum/redesign/${programaId}`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: { job_id: string }) => {
        setRedesignJob({ job_id: d.job_id, status: 'queued', current_step: 'En cola…' });
        redesignPollRef.current = setInterval(() => pollRedesign(d.job_id), 3000);
      })
      .catch(() => setRedesignJob({ job_id: '', status: 'error', error: 'No se pudo iniciar el análisis.' }));
  }

  function pollRedesign(jobId: string) {
    fetch(`${API}/api/curriculum/redesign/status/${jobId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d: RediseniJob) => {
        setRedesignJob(d);
        if (d.status === 'done' || d.status === 'error') {
          if (redesignPollRef.current) { clearInterval(redesignPollRef.current); redesignPollRef.current = null; }
        }
      }).catch(() => {});
  }

  async function downloadRedesign() {
    setRedesignDlError(false);
    try {
      const res = await fetch(`${API}/api/curriculum/redesign/${programaId}/download`);
      if (!res.ok) { setRedesignDlError(true); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `rediseno_curricular_${programaId}.docx`; a.click();
      URL.revokeObjectURL(url);
    } catch { setRedesignDlError(true); }
  }

  function startPipeline() {
    setPipelineStatus('launching');
    fetch(`${API}/api/pipeline/run`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ program_id: programaId, steps: ['microcurriculos', 'matching'] }),
    })
      .then(r => r.json())
      .then((d: { job_id: string }) => {
        setPipelineStatus('queued');
        pollRef.current = setInterval(() => {
          fetch(`${API}/api/pipeline/status/${d.job_id}`)
            .then(r => r.json())
            .then((s: { status: string; current_step: string | null }) => {
              setPipelineStatus(s.status); setPipelineStep(s.current_step);
              if (s.status === 'done' || s.status === 'error') {
                if (pollRef.current) clearInterval(pollRef.current);
                if (s.status === 'done') setTimeout(() => window.location.reload(), 1500);
              }
            }).catch(() => {});
        }, 3000);
      })
      .catch(() => setPipelineStatus('error'));
  }
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg }}>
      <div style={{ textAlign: 'center' }}>
        <div className="mx-auto w-14 h-14 rounded-full border-4 border-blue-200 border-t-blue-900 animate-spin" style={{ marginBottom: 16 }} />
        <p style={{ fontSize: 13, fontWeight: 500, color: C.navy }}>Cargando observatorio…</p>
      </div>
    </div>
  );

  const d = summary!;
  const { totales, programas, top_matches, skill_matches } = d;
  const prog  = programas.find(p => p.id === programaId) ?? programas[0];
  const meta  = PROGRAMS.find(p => p.id === programaId) ?? PROGRAMS[0];
  const score = prog?.score_promedio ?? 0;
  const nivel = pertinenciaLevel(score);
  const coberturaPct   = skills?.cobertura_pct ?? 0;
  const brechaPct      = skills ? 100 - coberturaPct : 0;
  // Use the backend-aggregated count over ALL matches (not the truncated top-30 sample).
  const empCompatibles = totales.empleos_compatibles ?? top_matches.filter(m => m.skills_en_comun.length > 0).length;
  const dataPobre      = totales.matches < 10 || totales.empleos_compatibles < 3;

  // Deduplicated market skills
  const skillsMercadoDeduped: SkillMercado[] = (() => {
    if (!skills) return [];
    const seen = new Map<string, SkillMercado>();
    for (const s of skills.skills_mercado) {
      if (isNoiseSkill(s.skill)) continue;
      const norm = normalizeSkill(s.skill);
      if (seen.has(norm)) seen.get(norm)!.frecuencia += s.frecuencia;
      else seen.set(norm, { ...s, skill: norm });
    }
    return Array.from(seen.values()).sort((a, b) => b.frecuencia - a.frecuencia);
  })();

  const viewProps: ViewProps = {
    summary: d, prog, meta, score, nivel, coberturaPct, brechaPct, empCompatibles,
    skills, skillsMercadoDeduped, univ, totales, top_matches, skill_matches, dataPobre, programaId,
    redesignJob, redesignDlError,
    onStartRedesign: startRedesign,
    onDownloadRedesign: downloadRedesign,
    onClearRedesign: () => { setRedesignJob(null); setRedesignDlError(false); },
  };

  const viewMap: Record<ViewId, React.ReactNode> = {
    resumen:         <ViewResumen         {...viewProps} />,
    mercado:         <ViewMercado         {...viewProps} />,
    programa:        <ViewPrograma        {...viewProps} />,
    cobertura:       <ViewCobertura       {...viewProps} />,
    brechas:         <ViewBrechas         {...viewProps} />,
    empleos:         <ViewEmpleos         {...viewProps} />,
    recomendaciones: <ViewRecomendaciones {...viewProps} />,
    contexto:        <ViewContexto        {...viewProps} />,
  };

  return (
    <div className="flex min-h-screen lg:h-screen lg:overflow-hidden" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>

      {/* Mobile: hamburger button (fixed, only visible <lg) */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 flex items-center justify-center w-10 h-10 rounded-lg shadow-lg"
        style={{ background: '#0B1730', border: 'none', cursor: 'pointer', color: '#fff' }}
        onClick={() => setSidebarOpen(true)}
        aria-label="Abrir menú"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Mobile: backdrop overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.55)' }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── SIDEBAR ── */}
      <aside
        className={[
          'fixed lg:static inset-y-0 left-0 z-50',
          'flex-shrink-0 flex flex-col',
          'transition-transform duration-300 ease-in-out',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        ].join(' ')}
        style={{ width: 200, background: '#0B1730' }}
      >

        {/* Logo */}
        <div style={{ padding: '20px 16px 14px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1, marginBottom: 2 }}>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 24, fontWeight: 700, color: '#fff' }}>un</span>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 24, fontWeight: 700, color: '#fff', position: 'relative', display: 'inline-block' }}>
              i<span style={{ position: 'absolute', top: -3, left: '50%', transform: 'translateX(-50%)', width: 4, height: 4, background: '#5BC4F5', borderRadius: '50%' }} />
            </span>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 26, fontWeight: 900, color: '#fff' }}>R</span>
          </div>
          <div style={{ fontSize: 7, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase' as const, color: '#7B8AAE', marginBottom: 14 }}>
            Observatorio
          </div>

          {/* Program selector */}
          <div style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, padding: '7px 10px' }}>
            <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase' as const, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>Programa</div>
            <select
              value={programaId}
              onChange={e => setProgramaId(Number(e.target.value))}
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer', outline: 'none', width: '100%' }}>
              {PROGRAMS.map(p => (
                <option key={p.id} value={p.id} style={{ color: '#111', background: '#fff' }}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* KPI strip */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4, padding: '0 12px 12px' }}>
          {([
            { v: score.toFixed(0), l: 'Score', c: nivel.color },
            { v: `${coberturaPct}%`, l: 'Cob.', c: '#38BDF8' },
            { v: String(empCompatibles), l: 'Emp.', c: '#34D399' },
          ] as { v: string; l: string; c: string }[]).map(({ v, l, c }) => (
            <div key={l} style={{ textAlign: 'center', padding: '5px 3px', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: c, lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>{l}</div>
            </div>
          ))}
        </div>

        <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', margin: '0 12px 6px' }} />

        {/* Nav */}
        <nav style={{ flex: 1, padding: '4px 8px' }}>
          {NAV_ITEMS.map(({ id, label, Icon }) => {
            const isActive = activeView === id;
            return (
              <button
                key={id}
                onClick={() => { setActiveView(id); setSidebarOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 9,
                  width: '100%', padding: '8px 10px', marginBottom: 2,
                  background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
                  border: 'none',
                  borderRadius: 8,
                  cursor: 'pointer', textAlign: 'left' as const,
                  transition: 'background 0.12s',
                }}>
                <Icon size={15} color={isActive ? '#FFFFFF' : '#8B9AC0'} />
                <span style={{ fontSize: 12, fontWeight: isActive ? 600 : 400, color: isActive ? '#FFFFFF' : '#8B9AC0' }}>
                  {label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div style={{ padding: '10px 12px 16px', borderTop: '1px solid rgba(255,255,255,0.07)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.28)' }}>Run #{d.run_id} · {d.fecha}</span>
            <span style={{ fontSize: 8, fontWeight: 800, letterSpacing: '0.10em', textTransform: 'uppercase' as const, color: 'rgba(255,255,255,0.45)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 20, padding: '2px 6px' }}>Beta</span>
          </div>
          {isFallback && <p style={{ fontSize: 9, color: C.gold, margin: '0 0 8px', fontWeight: 600 }}>⚠ Datos de referencia</p>}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setPipelineLogOpen(o => !o)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, color: 'rgba(255,255,255,0.50)', fontSize: 10, fontWeight: 600, cursor: 'pointer', padding: '6px 8px', display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ fontSize: 12 }}>↻</span> Actualizar datos
            </button>
            {pipelineLogOpen && (
              <div style={{ position: 'absolute', bottom: 40, left: 0, right: 0, background: '#0a3d8f', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, padding: '12px 14px', boxShadow: '0 -8px 24px rgba(0,0,0,0.35)', zIndex: 50 }}>
                <p style={{ fontSize: 11, color: '#86efac', marginBottom: 6, fontWeight: 700 }}>Último análisis: {d.fecha}</p>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5, margin: '0 0 8px' }}>
                  Matching corre automáticamente cada noche vía GitHub Actions.
                </p>
                {pipelineStatus !== 'idle' && (
                  <p style={{ fontSize: 10, color: '#fff', margin: '0 0 8px' }}>
                    {pipelineStatus === 'queued'  && '⏳ Iniciando…'}
                    {pipelineStatus === 'running' && `⚙ ${pipelineStep ?? '…'}`}
                    {pipelineStatus === 'done'    && '✓ Listo'}
                    {pipelineStatus === 'error'   && '⚠ Error'}
                  </p>
                )}
                <button
                  onClick={() => { startPipeline(); setPipelineLogOpen(false); }}
                  disabled={pipelineStatus === 'running' || pipelineStatus === 'queued'}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: '5px' }}>
                  {pipelineStatus === 'running' || pipelineStatus === 'queued' ? 'En proceso…' : '▶ Ejecutar análisis'}
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main className="flex-1 min-w-0 lg:overflow-y-auto pt-14 lg:pt-0" style={{ background: C.bg }}>
        {viewMap[activeView]}
      </main>
    </div>
  );
}
