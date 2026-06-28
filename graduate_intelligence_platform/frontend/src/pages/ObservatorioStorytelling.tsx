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
  programas: Programa[]; top_matches: TopMatch[];
  totales: { matches: number; alta: number; media: number; baja: number };
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
];

// ─── Nav items ────────────────────────────────────────────────────────────────
type ViewId = 'resumen' | 'mercado' | 'programa' | 'cobertura' | 'brechas' | 'empleos' | 'recomendaciones';

const NAV_ITEMS: { id: ViewId; label: string; Icon: ForwardRefExoticComponent<IconProps & RefAttributes<SVGSVGElement>> }[] = [
  { id: 'resumen',         label: 'Resumen',         Icon: IconGauge         },
  { id: 'mercado',         label: 'Mercado',          Icon: IconChartBar      },
  { id: 'programa',        label: 'Programa',         Icon: IconSchool        },
  { id: 'cobertura',       label: 'Cobertura',        Icon: IconTarget        },
  { id: 'brechas',         label: 'Brechas',          Icon: IconAlertTriangle },
  { id: 'empleos',         label: 'Empleos',          Icon: IconBriefcase     },
  { id: 'recomendaciones', label: 'Recomendaciones',  Icon: IconListCheck     },
];

// ─── Fallback data ─────────────────────────────────────────────────────────────
const FALLBACK: Summary = {
  run_id: 6, fecha: '2026-06-01',
  programas: [
    { id: 92,  nombre: 'Inteligencia Artificial',         matches_total: 38, score_promedio: 71.2, score_maximo: 88.4, labels: { high: 18, medium: 14, low: 6 } },
    { id: 94,  nombre: 'Visual Analytics and Big Data',   matches_total: 31, score_promedio: 68.5, score_maximo: 85.1, labels: { high: 14, medium: 12, low: 5 } },
    { id: 108, nombre: 'Especialización en Criminología', matches_total: 22, score_promedio: 52.3, score_maximo: 67.8, labels: { high: 4,  medium: 10, low: 8 } },
    { id: 20,  nombre: 'Neuropsicología y Educación',     matches_total: 0,  score_promedio: 0,    score_maximo: 0,    labels: { high: 0,  medium: 0,  low: 0 } },
  ],
  top_matches: [
    { programa: 'Visual Analytics', empleo: 'Data Scientist Senior', empresa: 'Bancolombia', score: 88.4, label: 'high', skills_en_comun: ['Python', 'Machine Learning', 'SQL'], skills_faltantes: ['Spark', 'Kafka'] },
    { programa: 'Visual Analytics', empleo: 'Analista BI',           empresa: 'Rappi',       score: 85.1, label: 'high', skills_en_comun: ['Power BI', 'SQL'],                  skills_faltantes: ['dbt', 'Airflow'] },
    { programa: 'Visual Analytics', empleo: 'ML Engineer',           empresa: 'Mercado Libre', score: 83.7, label: 'high', skills_en_comun: ['TensorFlow', 'Python'],           skills_faltantes: ['Kubernetes'] },
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

function DashPanel({ title, children, style }: { title: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, border: `1px solid ${C.border}`, padding: 16, display: 'flex', flexDirection: 'column', ...style }}>
      <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#9CA3AF', margin: '0 0 12px' }}>{title}</p>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: 0, lineHeight: 1.2 }}>{meta.nombre}</h1>
          <p style={{ fontSize: 11, color: '#9CA3AF', margin: '3px 0 0' }}>
            {totales.matches} vacantes analizadas · Run #{summary.run_id} · {summary.fecha}
          </p>
        </div>
        <span style={{ fontSize: 9, fontWeight: 800, border: '1px solid #D1D5DB', color: '#9CA3AF', borderRadius: 20, padding: '3px 10px', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          {prog.labels.high}↑ · {prog.labels.medium}→ · {prog.labels.low}↓
        </span>
      </div>

      {/* 4 KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, flexShrink: 0 }}>
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
          <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 10, flexShrink: 0 }}>
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, flexShrink: 0 }}>
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
                <div style={{ overflowY: 'auto', maxHeight: 160 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Qué Demanda el Mercado</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
          {skillsMercadoDeduped.length} skills en vacantes compatibles con el programa
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols.length}, 1fr)`, gap: 12, flex: 1, minHeight: 0 }}>
        {cols.map(({ cat, items }) => {
          const m = CAT_META[cat];
          return (
            <DashPanel key={cat} title={m.label} style={{ minHeight: 320 }}>
              <p style={{ fontSize: 10, color: '#9CA3AF', margin: '-8px 0 10px' }}>{bycat[cat].length} identificadas</p>
              {items.length === 0 ? (
                <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin datos suficientes</p>
              ) : (
                <div style={{ height: Math.max(items.length * 26 + 20, 200) }}>
                  <HorizBarChart
                    labels={items.map(s => s.skill)}
                    values={items.map(s => s.frecuencia)}
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

function ViewPrograma({ skills, dataPobre }: ViewProps) {
  if (!skills) return <div style={{ padding: 24 }}><Spinner /></div>;

  const bycat: Record<SkillCat, SkillPrograma[]> = { herramienta: [], competencia: [], habilidad: [], otro: [] };
  for (const s of skills.skills_programa) bycat[classifySkill(s.skill)].push(s);

  const ALL_CATS_P: SkillCat[] = ['herramienta', 'competencia', 'habilidad', 'otro'];
  const cols: { cat: SkillCat; items: SkillPrograma[] }[] = ALL_CATS_P
    .map(cat => ({ cat, items: bycat[cat].slice(0, 10) }))
    .filter(({ cat, items }) => items.length > 0 || cat !== 'otro');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Qué Enseña el Programa</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>{skills.skills_programa.length} competencias en el microcurrículo · Tamaño = presencia (materias)</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols.length}, 1fr)`, gap: 12, flex: 1, minHeight: 0 }}>
        {cols.map(({ cat, items }) => {
          const m = CAT_META[cat];
          return (
            <DashPanel key={cat} title={m.label} style={{ minHeight: 280 }}>
              {items.length === 0 ? (
                <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin datos</p>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Cobertura Curricular</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>% de las skills del mercado que el programa ya cubre</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 12, flexShrink: 0 }}>
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

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, alignContent: 'start' }}>
          <MetricCard label="Cobertura" value={`${coberturaPct}%`} color="#059669" />
          <MetricCard label="Skills cubiertas" value={skills.fortalezas.length} color="#2563EB" />
          <MetricCard label="Brechas" value={skills.brechas.length} color="#DC2626" />
          <div style={{ gridColumn: '1 / -1' }}>
            <DashPanel title="Fortalezas (en programa y en mercado)">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {skills.fortalezas.slice(0, 12).map(f => <SkillTag key={f.skill} skill={f.skill} variant="match" />)}
              </div>
            </DashPanel>
          </div>
        </div>
      </div>

      {/* SNIES table */}
      {univ && univ.competitors.length > 0 && (
        <DashPanel title={`Benchmark SNIES — ${univ.total} programas similares activos`}>
          <div style={{ overflowY: 'auto', maxHeight: 220 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                  {['Universidad', 'Programa', 'Modalidad', 'Matr.', 'Grad.'].map(h => (
                    <th key={h} style={{ textAlign: h === 'Matr.' || h === 'Grad.' ? 'right' : 'left', padding: '4px 8px', color: '#9CA3AF', fontWeight: 600, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {univ.competitors.slice(0, 12).map((c, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}`, background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                    <td style={{ padding: '6px 8px', color: '#374151', fontWeight: 600 }}>{c.nombre_ies}</td>
                    <td style={{ padding: '6px 8px', color: '#6B7280', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.nombre_programa}</td>
                    <td style={{ padding: '6px 8px', color: '#6B7280' }}>{c.modalidad}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, color: C.navy }}>{(c.matriculados ?? 0).toLocaleString('es-CO')}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#6B7280' }}>{(c.graduados ?? 0).toLocaleString('es-CO')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DashPanel>
      )}
    </div>
  );
}

function ViewBrechas({ skills, dataPobre }: ViewProps) {
  if (dataPobre) return <div style={{ padding: 24 }}><ExplorandoMsg /></div>;
  if (!skills)   return <div style={{ padding: 24 }}><Spinner /></div>;
  if (skills.brechas.length === 0) return (
    <div style={{ padding: 24 }}>
      <div style={{ background: '#D1FAE5', border: '1px solid #6EE7B7', borderRadius: 12, padding: '24px', textAlign: 'center' }}>
        <p style={{ fontSize: 15, fontWeight: 700, color: '#065F46' }}>✓ Sin brechas críticas identificadas</p>
        <p style={{ fontSize: 12, color: '#059669', margin: '6px 0 0' }}>El programa cubre las principales skills del mercado.</p>
      </div>
    </div>
  );

  const sorted = [...skills.brechas].sort((a, b) => (b.frecuencia_mercado ?? 0) - (a.frecuencia_mercado ?? 0));
  const bycat: Record<SkillCat, Brecha[]> = { herramienta: [], competencia: [], habilidad: [], otro: [] };
  for (const b of sorted) bycat[classifySkill(b.skill)].push(b);

  const brechasAlta = sorted.filter(b => b.frecuencia_mercado >= 10);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Brechas Curriculares</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>
          {skills.brechas.length} skills demandadas que el programa no cubre · {brechasAlta.length} de prioridad alta
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${(['herramienta','competencia','habilidad','otro'] as SkillCat[]).filter(c => bycat[c].length > 0 || c !== 'otro').length}, 1fr)`, gap: 12 }}>
        {(['herramienta', 'competencia', 'habilidad', 'otro'] as SkillCat[]).filter(c => bycat[c].length > 0 || c !== 'otro').map(cat => {
          const m = CAT_META[cat];
          const items = bycat[cat];
          return (
            <DashPanel key={cat} title={`${m.label} faltantes`} style={{ minHeight: 240 }}>
              <p style={{ fontSize: 10, color: '#9CA3AF', margin: '-8px 0 10px' }}>{items.length} brechas</p>
              {items.length === 0 ? (
                <p style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>Sin brechas en esta categoría</p>
              ) : (
                <div style={{ height: Math.max(items.length * 26 + 20, 160) }}>
                  <HorizBarChart labels={items.map(b => b.skill)} values={items.map(b => b.frecuencia_mercado ?? 0)} color="#EF4444" />
                </div>
              )}
            </DashPanel>
          );
        })}
      </div>

      {/* Scatter: Currículo vs Mercado */}
      {skills.matriz_completa && skills.matriz_completa.length > 0 && (
        <DashPanel title="Mapa Currículo vs Mercado — posición de cada skill por cuadrante">
          <div style={{ height: 340 }}>
            <SkillScatter matriz={skills.matriz_completa} />
          </div>
        </DashPanel>
      )}

      {skills.exclusivas_programa.length > 0 && (
        <DashPanel title="Skills exclusivas del programa (no demandadas aún en el mercado)">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {skills.exclusivas_programa.map(e => (
              <span key={e.skill} style={{ fontSize: 11, background: '#EEF2FB', color: C.navy, borderRadius: 20, padding: '3px 10px', fontWeight: 600, border: `1px solid ${C.border}` }}>{e.skill}</span>
            ))}
          </div>
          <p style={{ fontSize: 10, color: '#9CA3AF', margin: '8px 0 0' }}>Pueden ser relevantes en un futuro cercano o nicho específico.</p>
        </DashPanel>
      )}
    </div>
  );
}

function ViewEmpleos({ top_matches, empCompatibles }: ViewProps) {
  const empleos = top_matches.filter(m => m.skills_en_comun.length > 0 && m.score >= 45).slice(0, 10);

  if (empleos.length === 0) return (
    <div style={{ padding: 24 }}>
      <div style={{ background: '#F3F4F6', borderRadius: 12, padding: 32, textAlign: 'center' }}>
        <p style={{ fontSize: 14, color: '#6B7280' }}>Sin empleos con solapamiento de skills para este programa.</p>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Empleos Compatibles</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>{empCompatibles} vacantes con solapamiento de skills</p>
      </div>

      <DashPanel title={`Top ${empleos.length} vacantes más compatibles`}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
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
                  <td style={{ padding: '8px', color: '#9CA3AF', fontWeight: 700, fontSize: 11 }}>{i + 1}</td>
                  <td style={{ padding: '8px', color: C.navy, fontWeight: 600 }}>{m.empleo}</td>
                  <td style={{ padding: '8px', color: '#6B7280' }}>{m.empresa}</td>
                  <td style={{ padding: '8px', fontWeight: 700, color: m.score >= 70 ? '#059669' : m.score >= 50 ? '#2563EB' : '#D97706' }}>{m.score.toFixed(0)}</td>
                  <td style={{ padding: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 56, height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${coverPct}%`, background: coverPct >= 60 ? '#10B981' : '#F59E0B', borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, color: coverPct >= 60 ? '#059669' : '#D97706' }}>{coverPct}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '8px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {m.skills_en_comun.slice(0, 3).map(s => <SkillTag key={s} skill={s} variant="match" />)}
                    </div>
                  </td>
                  <td style={{ padding: '8px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {m.skills_faltantes.slice(0, 2).map(s => <SkillTag key={s} skill={s} variant="gap" />)}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ flexShrink: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: C.navy, margin: '0 0 2px' }}>Recomendaciones & Rediseño</h1>
        <p style={{ fontSize: 11, color: '#9CA3AF', margin: 0 }}>Simulación, acciones prioritarias y rediseño curricular asistido por IA</p>
      </div>

      {dataPobre ? <ExplorandoMsg /> : (
        <>
          {/* Simulation scenarios */}
          <DashPanel title="Simulación Curricular — Impacto estimado de incorporar brechas">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
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
        if (prog) fb.totales = { matches: prog.matches_total, alta: prog.labels.high, media: prog.labels.medium, baja: prog.labels.low };
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
  const { totales, programas, top_matches } = d;
  const prog  = programas.find(p => p.id === programaId) ?? programas[0];
  const meta  = PROGRAMS.find(p => p.id === programaId) ?? PROGRAMS[0];
  const score = prog?.score_promedio ?? 0;
  const nivel = pertinenciaLevel(score);
  const coberturaPct   = skills?.cobertura_pct ?? 0;
  const brechaPct      = skills ? 100 - coberturaPct : 0;
  const empCompatibles = top_matches.filter(m => m.skills_en_comun.length > 0).length;
  const qualityMatches = top_matches.filter(m => (m.skills_en_comun?.length ?? 0) > 0).length;
  const dataPobre      = totales.matches < 10 || qualityMatches < 3;

  // Deduplicated market skills
  const skillsMercadoDeduped: SkillMercado[] = (() => {
    if (!skills) return [];
    const seen = new Map<string, SkillMercado>();
    for (const s of skills.skills_mercado) {
      const norm = normalizeSkill(s.skill);
      if (seen.has(norm)) seen.get(norm)!.frecuencia += s.frecuencia;
      else seen.set(norm, { ...s, skill: norm });
    }
    return Array.from(seen.values()).sort((a, b) => b.frecuencia - a.frecuencia);
  })();

  const viewProps: ViewProps = {
    summary: d, prog, meta, score, nivel, coberturaPct, brechaPct, empCompatibles,
    skills, skillsMercadoDeduped, univ, totales, top_matches, dataPobre, programaId,
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
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'system-ui, -apple-system, sans-serif', overflow: 'hidden' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{ width: 200, flexShrink: 0, background: '#0B1730', display: 'flex', flexDirection: 'column', zIndex: 10 }}>

        {/* Logo */}
        <div style={{ padding: '20px 16px 14px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1, marginBottom: 2 }}>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 24, fontWeight: 700, color: '#fff' }}>un</span>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 24, fontWeight: 700, color: '#fff', position: 'relative', display: 'inline-block' }}>
              i<span style={{ position: 'absolute', top: -3, left: '50%', transform: 'translateX(-50%)', width: 4, height: 4, background: '#5BC4F5', borderRadius: '50%' }} />
            </span>
            <span style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 26, fontWeight: 900, color: '#fff' }}>R</span>
          </div>
          <div style={{ fontSize: 7, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase' as const, color: 'rgba(255,255,255,0.35)', marginBottom: 14 }}>
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
                onClick={() => setActiveView(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 9,
                  width: '100%', padding: '9px 10px', marginBottom: 1,
                  background: isActive ? 'rgba(255,255,255,0.10)' : 'transparent',
                  border: 'none',
                  borderLeft: `3px solid ${isActive ? '#60A5FA' : 'transparent'}`,
                  borderRadius: '0 7px 7px 0',
                  cursor: 'pointer', textAlign: 'left' as const,
                  transition: 'background 0.12s',
                }}>
                <Icon size={15} color={isActive ? '#93C5FD' : 'rgba(255,255,255,0.35)'} />
                <span style={{ fontSize: 12, fontWeight: isActive ? 700 : 400, color: isActive ? '#fff' : 'rgba(255,255,255,0.55)' }}>
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
      <main style={{ flex: 1, minWidth: 0, background: C.bg, overflowY: 'auto' }}>
        {viewMap[activeView]}
      </main>
    </div>
  );
}
