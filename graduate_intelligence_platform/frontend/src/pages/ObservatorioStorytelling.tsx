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
interface SkillPrograma { skill: string; cobertura: number }
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

// ─── Static program metadata ──────────────────────────────────────────────────
const PROGRAMS = [
  { id: 94,  label: 'Visual Analytics & Big Data',    nombre: 'Especialización en Visual Analytics y Big Data', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 92,  label: 'Inteligencia Artificial',        nombre: 'Especialización en Inteligencia Artificial',     creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  { id: 108, label: 'Especialización en Criminología', nombre: 'Especialización en Criminología',               creditos: 24, duracion: '2', periodicidad: 'Semestral' },
  { id: 20,  label: 'Neuropsicología y Educación',    nombre: 'Especialización en Neuropsicología y Educación', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
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

// ─── Skill classification ─────────────────────────────────────────────────────
const SKILL_CATS = {
  herramienta: new Set([
    'python','sql','power bi','tableau','excel','aws','azure','gcp','docker',
    'spark','databricks','tensorflow','r','hadoop','kafka','looker','salesforce',
    'pytorch','kubernetes','git','postgresql','mysql','mongodb','redis',
    'numpy','pandas','sklearn','scikit-learn','jupyter','colab','sap','crm',
  ]),
  competencia: new Set([
    'machine learning','deep learning','nlp','data visualization','big data','etl',
    'business intelligence','analisis de datos','data engineering','mlops',
    'estadistica','data warehouse','data lake','cloud computing','feature engineering',
    'computer vision','forecasting','data governance','data mining','series de tiempo',
  ]),
  habilidad: new Set([
    'gestion','liderazgo','comunicacion','trabajo en equipo','pensamiento critico',
    'innovacion','negociacion','planeacion','scrum','agile','kanban',
    'gestion de proyectos','orientacion a resultados','toma de decisiones',
  ]),
};
type SkillCat = 'herramienta' | 'competencia' | 'habilidad' | 'otro';
function classifySkill(s: string): SkillCat {
  const key = s.toLowerCase();
  if (SKILL_CATS.herramienta.has(key)) return 'herramienta';
  if (SKILL_CATS.competencia.has(key)) return 'competencia';
  if (SKILL_CATS.habilidad.has(key))   return 'habilidad';
  return 'otro';
}
const CAT_STYLE: Record<SkillCat, { bg: string; color: string; icon: string; label: string }> = {
  herramienta: { bg: 'rgba(147,197,253,0.2)', color: '#3b82f6', icon: '⚙', label: 'Herramienta' },
  competencia:  { bg: 'rgba(134,239,172,0.2)', color: '#16a34a', icon: '◈', label: 'Competencia'  },
  habilidad:    { bg: 'rgba(251,191,36,0.2)',  color: '#d97706', icon: '◇', label: 'Habilidad'    },
  otro:         { bg: 'rgba(148,163,184,0.15)',color: '#64748b', icon: '·', label: 'Otro'         },
};

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ n, title, children, dark = false, id }: {
  n: string; title: string; children: React.ReactNode; dark?: boolean; id?: string;
}) {
  return (
    <section id={id} className="relative py-14 px-4" style={{ background: dark ? C.navy : C.bg }}>
      <span className="absolute top-4 right-6 font-black select-none pointer-events-none"
        style={{ fontSize: '7rem', lineHeight: 1, opacity: dark ? 0.07 : 0.04, color: dark ? C.white : C.navy }}>
        {n}
      </span>
      <div className="max-w-4xl mx-auto relative z-10">
        <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: dark ? C.light : C.red }}>
          Sección {n}
        </p>
        <h2 className="text-2xl sm:text-3xl font-extrabold mb-6" style={{ color: dark ? C.white : C.navy }}>
          {title}
        </h2>
        {children}
      </div>
    </section>
  );
}

// ─── Insight block ─────────────────────────────────────────────────────────────
function Insight({ text, dark = false }: { text: string; dark?: boolean }) {
  const bg    = dark ? 'rgba(183,121,31,0.15)' : C.navyBg;
  const bord  = dark ? C.gold : C.navy;
  const label = dark ? C.gold : C.navy;
  const body  = dark ? '#e2e8f0' : '#1e293b';
  return (
    <div className="rounded-r-xl px-5 py-4 my-5" style={{ background: bg, borderLeft: `4px solid ${bord}` }}>
      <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: label }}>✦ Lectura Clave</p>
      <p className="text-sm leading-relaxed" style={{ color: body }}>{text}</p>
    </div>
  );
}

// ─── Semicircular SVG gauge ────────────────────────────────────────────────────
function SemiGauge({ pct, color, size = 200 }: { pct: number; color: string; size?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => { const id = setTimeout(() => setV(pct), 80); return () => clearTimeout(id); }, [pct]);
  const r = 80;
  const stroke = 14;
  const cx = 100, cy = 100;
  // arc from 180° to 0° (left to right, top)
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const arcX = (deg: number) => cx + r * Math.cos(toRad(deg));
  const arcY = (deg: number) => cy + r * Math.sin(toRad(deg));
  const startDeg = 180, endDeg = 0;
  const totalAngle = 180;
  const filled = (v / 100) * totalAngle;
  const filledEnd = 180 - filled;

  function describeArc(start: number, end: number) {
    const s = { x: arcX(start), y: arcY(start) };
    const e = { x: arcX(end),   y: arcY(end) };
    const large = Math.abs(end - start) > 180 ? 1 : 0;
    const sweep = end > start ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} ${sweep} ${e.x} ${e.y}`;
  }

  const scale = size / 200;

  return (
    <svg width={size} height={size * 0.6} viewBox={`0 60 200 120`} style={{ overflow: 'visible' }}>
      {/* track */}
      <path d={describeArc(180, 0)} fill="none" stroke="#e5e7eb" strokeWidth={stroke} strokeLinecap="round" />
      {/* fill */}
      {v > 0 && (
        <path
          d={describeArc(180, 180 - filled)}
          fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          style={{ transition: 'all 1.4s cubic-bezier(.4,0,.2,1)' }}
        />
      )}
      {/* value text */}
      <text x="100" y="115" textAnchor="middle" fontSize="28" fontWeight="800" fill={color}>
        {Math.round(v)}%
      </text>
    </svg>
  );
}

// ─── Skill tag ─────────────────────────────────────────────────────────────────
function SkillTag({ skill, variant = 'default' }: { skill: string; variant?: 'default' | 'gap' | 'match' }) {
  if (variant === 'gap') {
    return (
      <span className="rounded-full px-2 py-0.5 text-xs font-medium"
        style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626', border: '1px solid rgba(220,38,38,0.25)' }}>
        − {skill}
      </span>
    );
  }
  if (variant === 'match') {
    return (
      <span className="rounded-full px-2 py-0.5 text-xs font-medium"
        style={{ background: 'rgba(5,150,105,0.1)', color: '#059669', border: '1px solid rgba(5,150,105,0.25)' }}>
        ✓ {skill}
      </span>
    );
  }
  const cat = classifySkill(skill);
  const st  = CAT_STYLE[cat];
  return (
    <span className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: st.bg, color: st.color, border: `1px solid ${st.color}33` }}
      title={st.label}>
      {st.icon} {skill}
    </span>
  );
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
      <div style={{ fontSize: 15, fontWeight: 600, color: '#334670', marginBottom: 8 }}>
        Mercado laboral en exploración
      </div>
      <div style={{ fontSize: 13, color: '#6B7A9E', maxWidth: 400, margin: '0 auto', lineHeight: 1.6 }}>
        La oferta digital para este perfil en Colombia es limitada.
        Estamos ampliando la cobertura de vacantes con términos
        especializados. Los datos estarán disponibles en la próxima
        adquisición.
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

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ObservatorioStorytelling() {
  const [summary, setSummary]     = useState<Summary | null>(null);
  const [skills, setSkills]       = useState<SkillsAnalysis | null>(null);
  const [univ, setUniv]           = useState<UniversityData | null>(null);
  const [loading, setLoading]     = useState(true);
  const [isFallback, setIsFallback] = useState(false);
  const [programaId, setProgramaId] = useState(94);

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

  // pipeline state
  const [pipelineJobId, setPipelineJobId] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<string>('idle');
  const [pipelineStep, setPipelineStep]   = useState<string | null>(null);
  const [pipelineLog, setPipelineLog]     = useState<string[]>([]);
  const [pipelineLogOpen, setPipelineLogOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function startPipeline() {
    setPipelineStatus('launching');
    setPipelineLog([]);
    setPipelineStep(null);
    fetch(`${API}/api/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ program_id: programaId, steps: ['microcurriculos', 'acquisition', 'matching'] }),
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
          if (d.status === 'done') {
            // Refresh all data
            setTimeout(() => window.location.reload(), 1500);
          }
        }
      })
      .catch(() => {});
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: C.bg }}>
      <div className="text-center space-y-4">
        <div className="mx-auto w-14 h-14 rounded-full border-4 border-blue-200 border-t-blue-900 animate-spin" />
        <p className="text-sm font-medium" style={{ color: C.navy }}>Cargando observatorio…</p>
      </div>
    </div>
  );

  const d = summary!;
  const { totales, programas, top_matches } = d;
  const prog  = programas.find(p => p.id === programaId) ?? programas[0];
  const meta  = PROGRAMS.find(p => p.id === programaId) ?? PROGRAMS[0];
  const score = prog?.score_promedio ?? 0;
  const nivel = pertinenciaLevel(score);
  const coberturaPct = skills?.cobertura_pct ?? 0;
  const brechaPct    = skills ? 100 - coberturaPct : 0;
  const empCompatibles = top_matches.filter(m => m.skills_en_comun.length > 0).length;
  const maxFrecuencia  = skills ? Math.max(...skills.skills_mercado.map(s => s.frecuencia), 1) : 1;
  const maxCobertura   = skills ? Math.max(...skills.skills_programa.map(s => s.cobertura), 1) : 1;

  // Group skills by category for section 3
  const skillsByCategory: Record<string, SkillPrograma[]> = {};
  if (skills) {
    for (const s of skills.skills_programa) {
      const cat = CAT_STYLE[classifySkill(s.skill)].label;
      if (!skillsByCategory[cat]) skillsByCategory[cat] = [];
      skillsByCategory[cat].push(s);
    }
  }

  // Top-gap brechas split by priority
  const brechasAlta  = skills?.brechas.filter(b => b.frecuencia_mercado >= 10) ?? [];
  const brechasMedia = skills?.brechas.filter(b => b.frecuencia_mercado < 10)  ?? [];

  // Matching empleos for section 6
  const empleosCompatibles = top_matches
    .filter(m => m.skills_en_comun.length > 0 && m.score >= 45)
    .slice(0, 8);

  // Insufficient data guard (e.g. Criminología)
  const qualityMatches = top_matches.filter(m => (m.skills_en_comun?.length ?? 0) > 0).length;
  const dataPobre = totales.matches < 10 || qualityMatches < 3;

  return (
    <div style={{ background: C.bg, fontFamily: 'system-ui, sans-serif' }}>

      {isFallback && (
        <div className="text-center text-xs py-2 px-4" style={{ background: C.goldBg, color: C.gold }}>
          ⚠ Mostrando datos de referencia (run #6) — API no disponible
        </div>
      )}

      {/* ── PORTADA / HERO ── */}
      <header className="relative overflow-hidden py-14 px-4" style={{ background: C.navy }}>
        <span className="absolute inset-0 flex items-center justify-center text-white font-black select-none pointer-events-none"
          style={{ fontSize: '18rem', opacity: 0.03 }}>OI</span>

        {/* nav bar */}
        <div className="relative z-10 max-w-4xl mx-auto flex items-center gap-4 mb-10">
          <div className="flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center font-extrabold text-white text-lg"
            style={{ background: C.red }}>U</div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">UNIR Colombia</p>
            <p className="text-xs font-medium" style={{ color: C.light }}>Observatorio Institucional</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <select
              value={programaId}
              onChange={e => setProgramaId(Number(e.target.value))}
              style={{ background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6, padding: '6px 12px', fontSize: 11 }}>
              {PROGRAMS.map(p => (
                <option key={p.id} value={p.id} style={{ color: '#111', background: '#fff' }}>{p.label}</option>
              ))}
            </select>
            <span className="rounded-full px-3 py-1 text-xs font-semibold"
              style={{ background: 'rgba(255,255,255,0.1)', color: C.light, border: `1px solid rgba(255,255,255,0.15)` }}>
              Run #{d.run_id} · {d.fecha}
            </span>
            {/* Pipeline button */}
            <button
              onClick={startPipeline}
              disabled={pipelineStatus === 'running' || pipelineStatus === 'queued' || pipelineStatus === 'launching'}
              className="rounded-full px-3 py-1.5 text-xs font-bold transition-all"
              style={{
                background: pipelineStatus === 'done' ? 'rgba(134,239,172,0.2)'
                  : pipelineStatus === 'error' ? 'rgba(252,165,165,0.2)'
                  : pipelineStatus === 'running' || pipelineStatus === 'queued' ? 'rgba(147,197,253,0.2)'
                  : 'rgba(255,255,255,0.1)',
                color: pipelineStatus === 'done' ? '#86efac'
                  : pipelineStatus === 'error' ? '#fca5a5'
                  : pipelineStatus === 'running' || pipelineStatus === 'queued' ? '#93c5fd'
                  : C.light,
                border: '1px solid rgba(255,255,255,0.15)',
                cursor: (pipelineStatus === 'running' || pipelineStatus === 'queued') ? 'not-allowed' : 'pointer',
              }}
            >
              {pipelineStatus === 'launching' ? '⏳ Iniciando…'
                : pipelineStatus === 'queued'  ? '⏳ En cola…'
                : pipelineStatus === 'running' ? `⚙ ${pipelineStep ?? 'Procesando'}…`
                : pipelineStatus === 'done'    ? '✓ Actualizado'
                : pipelineStatus === 'error'   ? '⚠ Error'
                : '↻ Actualizar análisis'}
            </button>
          </div>
        </div>

        {/* Pipeline progress panel */}
        {pipelineStatus !== 'idle' && (
          <div className="relative z-10 max-w-4xl mx-auto mt-2 mb-0">
            <div className="rounded-xl px-4 py-3 flex items-center gap-3"
              style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)' }}>
              {(pipelineStatus === 'running' || pipelineStatus === 'queued') && (
                <div className="w-4 h-4 rounded-full border-2 border-blue-300 border-t-transparent animate-spin flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold" style={{ color: C.light }}>
                  {pipelineStatus === 'queued'  && 'Pipeline en cola — iniciando…'}
                  {pipelineStatus === 'running' && `Ejecutando: ${pipelineStep ?? '…'}`}
                  {pipelineStatus === 'done'    && '✓ Pipeline completado — recargando datos…'}
                  {pipelineStatus === 'error'   && '⚠ Pipeline completado con errores'}
                </p>
                {pipelineJobId && (
                  <p className="text-[10px] text-blue-400">job: {pipelineJobId}</p>
                )}
              </div>
              <button
                onClick={() => setPipelineLogOpen(o => !o)}
                className="text-xs font-semibold flex-shrink-0"
                style={{ color: C.mid }}>
                {pipelineLogOpen ? 'ocultar log' : 'ver log'}
              </button>
            </div>
            {pipelineLogOpen && pipelineLog.length > 0 && (
              <div className="mt-1 rounded-xl p-3 overflow-y-auto max-h-48 font-mono text-[10px]"
                style={{ background: 'rgba(0,0,0,0.4)', color: '#a5f3fc' }}>
                {pipelineLog.slice(-30).map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* hero headline */}
        <div className="relative z-10 max-w-3xl mx-auto text-center space-y-3">
          <p className="text-xs uppercase tracking-widest font-bold" style={{ color: C.light }}>
            Motor de Pertinencia Académica
          </p>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight">{meta.label}</h1>
          <p className="text-sm max-w-xl mx-auto" style={{ color: C.light }}>
            {totales.matches.toLocaleString('es-CO')} pares programa–empleo analizados
          </p>

          {/* 4 KPI cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-8">
            {[
              { label: 'Pertinencia curricular', value: `${score.toFixed(0)}/100`, sub: nivel.label, color: nivel.color },
              { label: 'Cobertura de skills',    value: `${coberturaPct}%`,         sub: `de ${skills?.skills_mercado.length ?? '—'} skills mercado`, color: '#93c5fd' },
              { label: 'Brecha curricular',      value: `${brechaPct}%`,            sub: `${skills?.brechas.length ?? '—'} skills sin cubrir`, color: '#fca5a5' },
              { label: 'Empleos con alineación', value: String(empCompatibles),     sub: `de ${totales.matches} analizados`, color: '#86efac' },
            ].map(({ label, value, sub, color }) => (
              <div key={label} className="rounded-2xl p-4 text-center"
                style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)' }}>
                <p className="text-2xl font-extrabold" style={{ color }}>{value}</p>
                <p className="text-xs font-semibold text-white mt-0.5">{label}</p>
                <p className="text-[10px] mt-0.5" style={{ color: C.light }}>{sub}</p>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── S1: Estado de Pertinencia ── */}
      <Section n="1" title="Estado de Pertinencia" id="s1">
        <div className="flex flex-col sm:flex-row gap-8 items-center">
          {/* gauge */}
          <div className="flex flex-col items-center gap-3 flex-shrink-0">
            <SemiGauge pct={score} color={nivel.color} size={240} />
            <span className="rounded-full px-5 py-1.5 text-sm font-extrabold" style={{ background: nivel.bg, color: nivel.color }}>
              {nivel.label}
            </span>
          </div>
          {/* scale + description */}
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
      </Section>

      {/* ── S2: Qué Demanda el Mercado ── */}
      <Section n="2" title="Qué Demanda el Mercado" dark id="s2">
        {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (
          <>
            <p className="text-sm text-blue-200 mb-5">
              Skills más frecuentes en las {totales.matches} vacantes analizadas para este perfil de programa.
            </p>

            {/* top skills mercado */}
            <div className="space-y-2 mb-6">
              {skills.skills_mercado.slice(0, 10).map(s => (
                <div key={s.skill} className="flex items-center gap-3">
                  <span className="text-xs text-blue-200 w-32 flex-shrink-0 truncate">{s.skill}</span>
                  <div className="flex-1 h-3 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${(s.frecuencia / maxFrecuencia) * 100}%`, background: C.mid }} />
                  </div>
                  <span className="text-xs font-semibold w-6 text-right" style={{ color: C.mid }}>{s.frecuencia}</span>
                </div>
              ))}
            </div>

            {/* skill category summary */}
            <div className="grid grid-cols-3 gap-4">
              {(['herramienta','competencia','habilidad'] as SkillCat[]).map(cat => {
                const st = CAT_STYLE[cat];
                const count = skills.skills_mercado.filter(s => classifySkill(s.skill) === cat).length;
                return (
                  <div key={cat} className="rounded-xl p-4 text-center"
                    style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <p className="text-2xl mb-1">{st.icon}</p>
                    <p className="text-lg font-extrabold text-white">{count}</p>
                    <p className="text-xs text-blue-300">{st.label}s</p>
                  </div>
                );
              })}
            </div>

            <Insight dark text={`El mercado demanda ${skills.skills_mercado.length} skills distintas. Las 3 más frecuentes son: ${skills.skills_mercado.slice(0,3).map(s=>s.skill).join(', ')}.`} />
          </>
        )}
      </Section>

      {/* ── S3: Qué Enseña el Programa ── */}
      <Section n="3" title="Qué Enseña el Programa" id="s3">
        {!skills ? <Spinner /> : (
          <>
            <p className="text-sm text-gray-600 mb-5">
              Skills identificadas en el plan de estudios, agrupadas por tipo.
            </p>

            {/* by category */}
            <div className="space-y-6">
              {Object.entries(skillsByCategory).map(([cat, skList]) => {
                const catKey = (Object.entries(CAT_STYLE).find(([, v]) => v.label === cat)?.[0] ?? 'otro') as SkillCat;
                const st = CAT_STYLE[catKey];
                return (
                  <div key={cat}>
                    <p className="text-xs font-bold uppercase tracking-widest mb-2 flex items-center gap-2"
                      style={{ color: st.color }}>
                      <span>{st.icon}</span> {cat}s
                    </p>
                    <div className="space-y-1.5">
                      {skList.map(s => (
                        <HBar key={s.skill} label={s.skill} val={s.cobertura} max={maxCobertura} color={st.color} />
                      ))}
                    </div>
                  </div>
                );
              })}
              {skills.skills_programa.length === 0 && (
                <p className="text-sm text-gray-400 py-6 text-center">Cargando competencias del programa... (ejecuta el pipeline para poblar los datos)</p>
              )}
            </div>

            {skills.skills_programa.length > 0 && (
              <Insight text={`El programa cubre ${skills.skills_programa.length} skills. Sus fortalezas son: ${skills.fortalezas.slice(0,3).map(f=>f.skill).join(', ') || 'por determinar'}.`} />
            )}
          </>
        )}
      </Section>

      {/* ── S4: Cobertura Curricular ── */}
      <Section n="4" title="Cobertura Curricular" dark id="s4">
        {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (
          <>
            <p className="text-sm text-blue-200 mb-6">
              Porcentaje de las skills demandadas por el mercado que ya están cubiertas en el plan de estudios.
            </p>

            <div className="flex flex-col sm:flex-row gap-8 items-center">
              {/* semicircle gauge */}
              <div className="flex flex-col items-center gap-2 flex-shrink-0">
                <SemiGauge pct={coberturaPct} color="#86efac" size={220} />
                <p className="text-sm font-semibold" style={{ color: '#86efac' }}>Cobertura Curricular</p>
              </div>

              {/* right panel */}
              <div className="flex-1 space-y-4">
                {/* KPI row */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { k: 'Skills cubiertas', v: skills.fortalezas.length, c: '#86efac' },
                    { k: 'Brechas',          v: skills.brechas.length,    c: '#fca5a5' },
                    { k: 'Exclusivas prog.', v: skills.exclusivas_programa.length, c: C.mid },
                  ].map(({ k, v, c }) => (
                    <div key={k} className="rounded-xl p-3 text-center"
                      style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                      <p className="text-2xl font-extrabold" style={{ color: c }}>{v}</p>
                      <p className="text-xs text-blue-300 mt-0.5">{k}</p>
                    </div>
                  ))}
                </div>

                {/* fortalezas list */}
                {skills.fortalezas.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: '#86efac' }}>✓ Fortalezas (presentes en ambos)</p>
                    <div className="flex flex-wrap gap-1.5">
                      {skills.fortalezas.slice(0, 8).map(f => (
                        <SkillTag key={f.skill} skill={f.skill} variant="match" />
                      ))}
                    </div>
                  </div>
                )}

                {/* SNIES benchmark if available */}
                {univ && (
                  <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>
                      Contexto SNIES — {univ.total} programas similares
                    </p>
                    <p className="text-xs text-blue-300">
                      Competidores activos en modalidad virtual · Colombia 2024
                    </p>
                  </div>
                )}
              </div>
            </div>

            <Insight dark text={`El programa cubre el ${coberturaPct}% de las skills que el mercado laboral demanda. ${coberturaPct >= 60 ? 'Cobertura sólida con oportunidades de mejora.' : 'Existe una brecha significativa que requiere actualización curricular.'}`} />
          </>
        )}
      </Section>

      {/* ── S5: Brechas Curriculares ── */}
      <Section n="5" title="Brechas Curriculares" id="s5">
        {dataPobre ? <ExplorandoMsg /> : !skills ? <Spinner /> : (
          <>
            <p className="text-sm text-gray-600 mb-6">
              Skills con alta demanda en el mercado que el programa aún no cubre.
            </p>

            {skills.brechas.length === 0 ? (
              <div className="rounded-xl px-5 py-8 text-center" style={{ background: '#d1fae5', border: '1px solid #6ee7b7' }}>
                <p className="text-sm font-semibold text-green-800">✓ Sin brechas críticas identificadas</p>
                <p className="text-xs text-green-600 mt-1">El programa cubre las principales skills del mercado.</p>
              </div>
            ) : (
              <>
                {brechasAlta.length > 0 && (
                  <div className="mb-6">
                    <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: '#dc2626' }}>
                      Prioridad Alta — Frecuencia ≥ 10
                    </p>
                    <div className="space-y-2">
                      {brechasAlta.map(b => (
                        <div key={b.skill} className="flex items-center gap-3 rounded-xl px-4 py-2.5"
                          style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                          <span className="text-sm font-semibold flex-1 text-red-800">{b.skill}</span>
                          <div className="h-2 rounded-full w-24" style={{ background: '#fecaca' }}>
                            <div className="h-full rounded-full" style={{ width: `${(b.frecuencia_mercado / maxFrecuencia) * 100}%`, background: '#dc2626' }} />
                          </div>
                          <span className="text-xs font-bold text-red-600">{b.frecuencia_mercado} vacantes</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {brechasMedia.length > 0 && (
                  <div className="mb-6">
                    <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: C.gold }}>
                      Prioridad Media — Frecuencia &lt; 10
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {brechasMedia.map(b => (
                        <SkillTag key={b.skill} skill={b.skill} variant="gap" />
                      ))}
                    </div>
                  </div>
                )}

                {skills.exclusivas_programa.length > 0 && (
                  <div className="rounded-xl p-4 mb-4" style={{ background: C.navyBg, border: `1px solid ${C.border}` }}>
                    <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: C.navy }}>
                      Skills Exclusivas del Programa (no demandadas aún)
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {skills.exclusivas_programa.map(e => (
                        <span key={e.skill} className="rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{ background: '#EEF2FB', color: C.navy, border: `1px solid ${C.border}` }}>
                          {e.skill}
                        </span>
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
      </Section>

      {/* ── S6: Empleos Compatibles ── */}
      <Section n="6" title="Empleos Compatibles" dark id="s6">
        {empleosCompatibles.length === 0 ? (
          <div className="rounded-xl px-5 py-8 text-center" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <p className="text-sm text-blue-300 leading-relaxed">
              Aún no hay empleos con solapamiento de skills para este programa.<br />
              Se requiere re-ejecutar el pipeline de matching en Railway.
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm text-blue-200 mb-5">
              Vacantes con mayor compatibilidad de skills con el programa seleccionado.
            </p>
            <div className="space-y-3">
              {empleosCompatibles.map((m, i) => {
                const total   = m.skills_en_comun.length + m.skills_faltantes.length;
                const coverPct = total ? Math.round((m.skills_en_comun.length / total) * 100) : 0;
                return (
                  <div key={i} className="rounded-xl p-4"
                    style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <div className="flex items-start gap-3 mb-3">
                      <span className="text-xl font-black w-7 text-center flex-shrink-0"
                        style={{ color: 'rgba(255,255,255,0.2)' }}>{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{m.empleo}</p>
                        <p className="text-xs text-blue-300">{m.empresa} · Score {m.score.toFixed(0)}/100</p>
                      </div>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                        style={{ background: coverPct >= 60 ? 'rgba(134,239,172,0.2)' : 'rgba(252,165,165,0.2)', color: coverPct >= 60 ? '#86efac' : '#fca5a5' }}>
                        {coverPct}% cubierto
                      </span>
                    </div>
                    {/* coverage bar */}
                    <div className="ml-10 mb-2">
                      <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                        <div className="h-full rounded-full transition-all duration-700"
                          style={{ width: `${coverPct}%`, background: '#86efac' }} />
                      </div>
                    </div>
                    {/* skill tags */}
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
      </Section>

      {/* ── S7: Simulación Curricular ── */}
      <Section n="7" title="Simulación Curricular" id="s7">
        {dataPobre ? <ExplorandoMsg /> : (
          <>
            <p className="text-sm text-gray-600 mb-6">
              Impacto estimado de incorporar las principales brechas al plan de estudios.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              {[
                {
                  title: 'Escenario A — Mínimo',
                  sub: `Incorporar top ${Math.min(brechasAlta.length, 2)} brechas críticas`,
                  pertinencia: `+${Math.round(brechaPct * 0.25)}%`,
                  cobertura:   `${Math.min(coberturaPct + 15, 99)}%`,
                  empleos:     `+${Math.round(empCompatibles * 0.2)}`,
                  color: C.gold,
                },
                {
                  title: 'Escenario B — Moderado',
                  sub: `Incorporar todas las brechas de prioridad alta (${brechasAlta.length})`,
                  pertinencia: `+${Math.round(brechaPct * 0.45)}%`,
                  cobertura:   `${Math.min(coberturaPct + 25, 99)}%`,
                  empleos:     `+${Math.round(empCompatibles * 0.4)}`,
                  color: '#2563eb',
                },
                {
                  title: 'Escenario C — Completo',
                  sub: `Incorporar todas las brechas identificadas (${skills?.brechas.length ?? '—'})`,
                  pertinencia: `+${Math.round(brechaPct * 0.70)}%`,
                  cobertura:   `${Math.min(coberturaPct + 40, 99)}%`,
                  empleos:     `+${Math.round(empCompatibles * 0.65)}`,
                  color: '#059669',
                },
              ].map(sc => (
                <div key={sc.title} className="rounded-2xl border p-5 space-y-3"
                  style={{ borderColor: sc.color, background: C.navyBg }}>
                  <p className="text-sm font-bold" style={{ color: sc.color }}>{sc.title}</p>
                  <p className="text-xs text-gray-500">{sc.sub}</p>
                  <div className="space-y-2">
                    {[
                      { k: 'Pertinencia',   v: sc.pertinencia },
                      { k: 'Cobertura',     v: sc.cobertura   },
                      { k: 'Empleos comp.', v: sc.empleos     },
                    ].map(({ k, v }) => (
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
      </Section>

      {/* ── S8: Recomendaciones ── */}
      <Section n="8" title="Recomendaciones" dark id="s8">
        {dataPobre ? <ExplorandoMsg /> : (
          <>
            <p className="text-sm text-blue-200 mb-6">
              Acciones prioritarias para mejorar la pertinencia curricular del programa.
            </p>
            <div className="space-y-4">
              {[
                {
                  n: 1,
                  action: `Incorporar ${brechasAlta.slice(0, 2).map(b => b.skill).join(' y ') || 'skills de alta prioridad'} como contenidos obligatorios.`,
                  detail: 'Mayor demanda identificada en vacantes. Sin presencia actual en el currículo.',
                  urgency: 'Urgente',
                  color: '#dc2626', urgBg: '#fee2e2',
                },
                {
                  n: 2,
                  action: 'Actualizar los módulos de herramientas para incluir versiones actuales de las plataformas cloud.',
                  detail: `AWS, Azure y GCP aparecen en ${skills?.skills_mercado.find(s => s.skill.toLowerCase().includes('aws'))?.frecuencia ?? '—'} vacantes.`,
                  urgency: 'Alta',
                  color: '#d97706', urgBg: '#fef3c7',
                },
                {
                  n: 3,
                  action: 'Incorporar un módulo de MLOps y despliegue de modelos en producción.',
                  detail: 'Competencia emergente con alta frecuencia en perfiles de IA y datos.',
                  urgency: 'Alta',
                  color: '#d97706', urgBg: '#fef3c7',
                },
                {
                  n: 4,
                  action: `Profundizar la cobertura de ${skills?.fortalezas[0]?.skill ?? 'la principal fortaleza'} de nivel básico a avanzado.`,
                  detail: 'Presencia en currículo confirmada. Potencial de diferenciación con mayor profundidad.',
                  urgency: 'Media',
                  color: '#2563eb', urgBg: '#dbeafe',
                },
                {
                  n: 5,
                  action: 'Revisar contenidos con baja o nula demanda para liberar espacio curricular.',
                  detail: 'El espacio liberado permite incorporar nuevas competencias sin aumentar la carga total.',
                  urgency: 'Media',
                  color: '#2563eb', urgBg: '#dbeafe',
                },
              ].map(rec => (
                <div key={rec.n} className="rounded-xl p-4 flex gap-4"
                  style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span className="text-2xl font-black flex-shrink-0 mt-0.5" style={{ color: 'rgba(255,255,255,0.2)' }}>
                    {rec.n}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <p className="text-sm font-semibold text-white leading-snug">{rec.action}</p>
                      <span className="rounded-full px-2 py-0.5 text-xs font-bold flex-shrink-0"
                        style={{ background: rec.urgBg, color: rec.color }}>
                        {rec.urgency}
                      </span>
                    </div>
                    <p className="text-xs text-blue-300">{rec.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </Section>

      {/* ── CIERRE ── */}
      <section className="py-16 px-4 text-center" style={{ background: C.navy }}>
        <div className="max-w-xl mx-auto space-y-4">
          <p className="text-2xl font-extrabold text-white">Evidencia para la Decisión Curricular</p>
          <p className="text-sm text-blue-200 leading-relaxed">
            Con {totales.matches.toLocaleString('es-CO')} pares analizados, este observatorio provee inteligencia
            curricular accionable para UNIR Colombia. El motor actualiza los scores en cada run de adquisición.
          </p>
          <p className="text-xs text-blue-400 pt-2">Run #{d.run_id} · {d.fecha} · Motor de Pertinencia Académica v2</p>
        </div>
      </section>

    </div>
  );
}
