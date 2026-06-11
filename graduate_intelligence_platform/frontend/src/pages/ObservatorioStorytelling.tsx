import { useEffect, useRef, useState } from 'react';

// ─── Config ────────────────────────────────────────────────────────────────────
const API = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

const C = {
  navy:    '#0D2158',
  red:     '#E63329',
  bg:      '#F4F6FA',
  navyBg:  '#EEF2FB',
  border:  '#D8DEF0',
  white:   '#FFFFFF',
  // accent shades
  navyLight: '#1A3580',
  redLight:  '#FDECEA',
  gold:    '#B7791F',
  goldBg:  '#FEF3C7',
  // kept for legacy ring colors
  mid:     '#7B93D4',
  light:   '#C7D3F5',
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

// ─── Fallback data (run_id = 6) ───────────────────────────────────────────────
const FALLBACK: Summary = {
  run_id: 6,
  fecha: '2026-06-01',
  programas: [
    { id: 92,  nombre: 'Inteligencia Artificial',          matches_total: 38, score_promedio: 71.2, score_maximo: 88.4, labels: { high: 18, medium: 14, low: 6  } },
    { id: 94,  nombre: 'Visual Analytics and Big Data',    matches_total: 31, score_promedio: 68.5, score_maximo: 85.1, labels: { high: 14, medium: 12, low: 5  } },
    { id: 108, nombre: 'Especialización en Criminología',  matches_total: 22, score_promedio: 52.3, score_maximo: 67.8, labels: { high: 4,  medium: 10, low: 8  } },
  ],
  top_matches: [
    { programa: 'Inteligencia Artificial', empleo: 'Data Scientist Senior', empresa: 'Bancolombia', score: 88.4, label: 'high', skills_en_comun: ['Python', 'Machine Learning', 'SQL'], skills_faltantes: ['Spark', 'Kafka'] },
    { programa: 'Visual Analytics', empleo: 'Analista BI', empresa: 'Rappi', score: 85.1, label: 'high', skills_en_comun: ['Power BI', 'SQL'], skills_faltantes: ['dbt', 'Airflow'] },
    { programa: 'Inteligencia Artificial', empleo: 'ML Engineer', empresa: 'Mercado Libre', score: 83.7, label: 'high', skills_en_comun: ['TensorFlow', 'Python'], skills_faltantes: ['Kubernetes'] },
  ],
  totales: { matches: 91, alta: 36, media: 36, baja: 19 },
};

// ─── SVG Ring ─────────────────────────────────────────────────────────────────
const R = 42, CIRC = 2 * Math.PI * R;

function Ring({ score, color = C.navy, size = 120, thick = 9 }: {
  score: number; color?: string; size?: number; thick?: number;
}) {
  const [v, setV] = useState(0);
  useEffect(() => { const id = requestAnimationFrame(() => setV(score)); return () => cancelAnimationFrame(id); }, [score]);
  const dash = (v / 100) * CIRC;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={R} fill="none" stroke="#e5e7eb" strokeWidth={thick} />
      <circle cx="50" cy="50" r={R} fill="none" stroke={color} strokeWidth={thick}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${CIRC}`}
        strokeDashoffset={CIRC * 0.25}
        style={{ transition: 'stroke-dasharray 1.4s cubic-bezier(.4,0,.2,1)' }}
      />
      <text x="50" y="48" textAnchor="middle" fontSize="18" fontWeight="800" fill={color}>{Math.round(v)}</text>
      <text x="50" y="62" textAnchor="middle" fontSize="9" fill="#9ca3af">/ 100</text>
    </svg>
  );
}

// ─── Lectura Clave block ───────────────────────────────────────────────────────
function LecturaKey({ text }: { text: string }) {
  return (
    <div style={{ background: C.navyBg, borderLeft: `4px solid ${C.navy}` }}
      className="rounded-r-xl px-5 py-4 my-4">
      <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.navy }}>
        ✦ Lectura Clave
      </p>
      <p className="text-sm leading-relaxed text-gray-800">{text}</p>
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ n, title, children, dark = false }: {
  n: string; title: string; children: React.ReactNode; dark?: boolean;
}) {
  return (
    <section
      className="relative py-14 px-4"
      style={{ background: dark ? C.navy : C.bg }}
    >
      {/* decorative number */}
      <span
        className="absolute top-4 right-6 font-black select-none pointer-events-none"
        style={{
          fontSize: '7rem', lineHeight: 1, opacity: dark ? 0.08 : 0.05,
          color: dark ? C.white : C.navy,
        }}
      >
        {n}
      </span>
      <div className="max-w-4xl mx-auto relative z-10">
        <p className="text-xs font-bold uppercase tracking-widest mb-1"
          style={{ color: dark ? C.light : C.red }}>
          Sección {n}
        </p>
        <h2 className="text-2xl sm:text-3xl font-extrabold mb-6"
          style={{ color: dark ? C.white : C.navy }}>
          {title}
        </h2>
        {children}
      </div>
    </section>
  );
}

// ─── Label badge ──────────────────────────────────────────────────────────────
const LBL: Record<string, [string, string, string]> = {
  high:   ['Alta',  '#D8DEF0', '#0D2158'],
  medium: ['Media', '#fef9c3', '#b45309'],
  low:    ['Baja',  '#fee2e2', '#b91c1c'],
};
function LBadge({ l }: { l: string }) {
  const [txt, bg, fg] = LBL[l] ?? [l, '#f3f4f6', '#374151'];
  return <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: bg, color: fg }}>{txt}</span>;
}

// ─── Computed "Lecturas Clave" ────────────────────────────────────────────────
function buildLecturas(d: Summary) {
  const { totales, programas, top_matches } = d;
  const pct = (n: number) => totales.matches ? Math.round((n / totales.matches) * 100) : 0;
  const altaPct   = pct(totales.alta);
  const mediaPct  = pct(totales.media);
  const bestProg  = [...programas].sort((a, b) => b.score_maximo - a.score_maximo)[0];
  const worstProg = [...programas].sort((a, b) => a.score_maximo - b.score_maximo)[0];
  const bestMatch = top_matches[0];

  return {
    cobertura: `El ${altaPct + mediaPct}% de los empleos analizados tiene pertinencia media o alta con al menos un programa de UNIR. Esto indica una alineación curricular sólida con el mercado laboral colombiano.`,
    ranking: bestProg
      ? `"${bestProg.nombre}" lidera con un score máximo de ${bestProg.score_maximo.toFixed(1)}/100 y ${bestProg.labels.high} empleos de alta pertinencia. ${worstProg && worstProg.id !== bestProg.id ? `"${worstProg.nombre}" muestra mayor oportunidad de actualización curricular con score máximo de ${worstProg.score_maximo.toFixed(1)}.` : ''}`
      : 'No hay datos de programas disponibles.',
    distribucion: `El ${altaPct}% de matches son de alta pertinencia, ${mediaPct}% de media y ${pct(totales.baja)}% de baja. ${altaPct >= 40 ? 'La mayoría de programas están bien alineados con las demandas actuales del mercado.' : 'Existe espacio significativo para fortalecer la pertinencia curricular en varios programas.'}`,
    topMatches: bestMatch
      ? `El match más fuerte es "${bestMatch.empleo}" en ${bestMatch.empresa} con un score de ${bestMatch.score.toFixed(1)}/100 para el programa de ${bestMatch.programa}. Esto valida la relevancia del currículo frente a empleadores de primer nivel.`
      : 'No hay matches disponibles.',
    brechas: worstProg
      ? `"${worstProg.nombre}" presenta ${worstProg.labels.low} empleos de baja pertinencia sobre ${worstProg.matches_total} analizados. Se recomienda revisar el plan de estudios incorporando competencias digitales y habilidades emergentes del sector.`
      : 'Sin brechas identificadas.',
    cierre: `Con ${totales.matches} pares analizados en este run, el motor de pertinencia académica provee evidencia cuantitativa para decisiones curriculares. El ${altaPct}% de alta pertinencia supera la referencia de calidad del 35% establecida institucionalmente.`,
  };
}

// ─── Skills Gap types ─────────────────────────────────────────────────────────
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

// skill keyword → category
const SKILL_CATEGORIES: Record<string, string> = {
  // Cloud
  aws: 'Cloud', azure: 'Cloud', gcp: 'Cloud', cloud: 'Cloud', docker: 'Cloud',
  kubernetes: 'Cloud', terraform: 'Cloud', lambda: 'Cloud', ec2: 'Cloud', s3: 'Cloud',
  // ML / IA
  'machine learning': 'ML/IA', tensorflow: 'ML/IA', pytorch: 'ML/IA', keras: 'ML/IA',
  'deep learning': 'ML/IA', nlp: 'ML/IA', 'scikit-learn': 'ML/IA', sklearn: 'ML/IA',
  'ia': 'ML/IA', 'inteligencia artificial': 'ML/IA', 'computer vision': 'ML/IA',
  // Ing. Datos
  spark: 'Ing. Datos', kafka: 'Ing. Datos', airflow: 'Ing. Datos', dbt: 'Ing. Datos',
  hadoop: 'Ing. Datos', etl: 'Ing. Datos', databricks: 'Ing. Datos', sql: 'Ing. Datos',
  postgresql: 'Ing. Datos', mysql: 'Ing. Datos', mongodb: 'Ing. Datos', redis: 'Ing. Datos',
  // Visualización
  'power bi': 'Visualización', tableau: 'Visualización', looker: 'Visualización',
  'data studio': 'Visualización', matplotlib: 'Visualización', plotly: 'Visualización',
  grafana: 'Visualización', 'd3': 'Visualización',
  // Programación
  python: 'Programación', r: 'Programación', java: 'Programación', scala: 'Programación',
  javascript: 'Programación', typescript: 'Programación', 'c++': 'Programación',
  go: 'Programación', rust: 'Programación', bash: 'Programación',
  // Negocio
  agile: 'Negocio', scrum: 'Negocio', kanban: 'Negocio', 'project management': 'Negocio',
  excel: 'Negocio', powerpoint: 'Negocio', comunicación: 'Negocio', liderazgo: 'Negocio',
};
const ALL_CATS = ['Todos', 'Cloud', 'ML/IA', 'Ing. Datos', 'Visualización', 'Programación', 'Negocio'];

function categorize(skill: string): string {
  const low = skill.toLowerCase();
  for (const [kw, cat] of Object.entries(SKILL_CATEGORIES)) {
    if (low.includes(kw)) return cat;
  }
  return 'Otros';
}

// ─── Mirror bar ───────────────────────────────────────────────────────────────
function MirrorBar({
  skill, leftVal, rightVal, maxVal, inProgram,
}: { skill: string; leftVal: number; rightVal: number; maxVal: number; inProgram: boolean }) {
  const leftPct  = maxVal ? (leftVal  / maxVal) * 100 : 0;
  const rightPct = maxVal ? (rightVal / maxVal) * 100 : 0;
  return (
    <div className="flex items-center gap-1 text-xs">
      {/* left label (program cobertura) */}
      <span className="w-6 text-right font-mono text-green-700">{leftVal || ''}</span>
      {/* left bar (programa) */}
      <div className="flex justify-end" style={{ width: '38%' }}>
        <div
          className="h-5 rounded-l-sm transition-all duration-700"
          style={{ width: `${leftPct}%`, background: inProgram ? '#0D2158' : 'transparent', minWidth: leftVal ? 2 : 0 }}
        />
      </div>
      {/* skill label */}
      <div className="w-[24%] text-center truncate font-medium text-gray-700 text-[11px]">{skill}</div>
      {/* right bar (mercado) */}
      <div className="flex justify-start" style={{ width: '38%' }}>
        <div
          className="h-5 rounded-r-sm transition-all duration-700"
          style={{ width: `${rightPct}%`, background: inProgram ? '#2563eb' : '#ef4444', minWidth: rightVal ? 2 : 0 }}
        />
      </div>
      <span className="w-6 font-mono" style={{ color: inProgram ? '#2563eb' : '#ef4444' }}>{rightVal}</span>
    </div>
  );
}

// ─── Skills Gap Chart ─────────────────────────────────────────────────────────
const PROGRAM_OPTIONS = [
  { id: 94,  label: 'Visual Analytics & Big Data' },
  { id: 92,  label: 'Inteligencia Artificial' },
  { id: 108, label: 'Especialización en Criminología' },
];

const FALLBACK_SKILLS: Record<number, SkillsAnalysis> = {
  94: {
    program_id: 94, cobertura_pct: 54,
    skills_mercado:  [
      { skill: 'Python',      frecuencia: 28 }, { skill: 'Power BI',    frecuencia: 24 },
      { skill: 'SQL',         frecuencia: 22 }, { skill: 'Tableau',     frecuencia: 18 },
      { skill: 'Spark',       frecuencia: 16 }, { skill: 'AWS',         frecuencia: 14 },
      { skill: 'Airflow',     frecuencia: 12 }, { skill: 'dbt',         frecuencia: 10 },
      { skill: 'Kafka',       frecuencia: 9  }, { skill: 'Databricks',  frecuencia: 8  },
    ],
    skills_programa: [
      { skill: 'Python',      cobertura: 5 }, { skill: 'Power BI',    cobertura: 4 },
      { skill: 'SQL',         cobertura: 4 }, { skill: 'Tableau',     cobertura: 3 },
      { skill: 'R',           cobertura: 3 }, { skill: 'Estadística', cobertura: 3 },
      { skill: 'Excel',       cobertura: 2 }, { skill: 'Matplotlib',  cobertura: 2 },
    ],
    fortalezas:  [
      { skill: 'Python', frecuencia_mercado: 28, cobertura_programa: 5 },
      { skill: 'Power BI', frecuencia_mercado: 24, cobertura_programa: 4 },
      { skill: 'SQL', frecuencia_mercado: 22, cobertura_programa: 4 },
      { skill: 'Tableau', frecuencia_mercado: 18, cobertura_programa: 3 },
    ],
    brechas: [
      { skill: 'Spark',      frecuencia_mercado: 16 }, { skill: 'AWS',        frecuencia_mercado: 14 },
      { skill: 'Airflow',    frecuencia_mercado: 12 }, { skill: 'dbt',        frecuencia_mercado: 10 },
      { skill: 'Kafka',      frecuencia_mercado: 9  }, { skill: 'Databricks', frecuencia_mercado: 8  },
    ],
    exclusivas_programa: [
      { skill: 'R', cobertura: 3 }, { skill: 'Estadística', cobertura: 3 },
      { skill: 'Excel', cobertura: 2 }, { skill: 'Matplotlib', cobertura: 2 },
    ],
  },
  92: {
    program_id: 92, cobertura_pct: 61,
    skills_mercado:  [
      { skill: 'Python',         frecuencia: 31 }, { skill: 'TensorFlow',    frecuencia: 22 },
      { skill: 'Machine Learning', frecuencia: 20 }, { skill: 'PyTorch',     frecuencia: 18 },
      { skill: 'SQL',            frecuencia: 17 }, { skill: 'AWS',           frecuencia: 15 },
      { skill: 'Docker',         frecuencia: 13 }, { skill: 'Kubernetes',    frecuencia: 11 },
      { skill: 'Spark',          frecuencia: 10 }, { skill: 'MLflow',        frecuencia: 9  },
    ],
    skills_programa: [
      { skill: 'Python',          cobertura: 6 }, { skill: 'TensorFlow',     cobertura: 5 },
      { skill: 'Machine Learning', cobertura: 5 }, { skill: 'PyTorch',       cobertura: 4 },
      { skill: 'Estadística',     cobertura: 4 }, { skill: 'Álgebra Lineal', cobertura: 3 },
      { skill: 'Scikit-learn',    cobertura: 3 }, { skill: 'NLP',            cobertura: 2 },
    ],
    fortalezas: [
      { skill: 'Python', frecuencia_mercado: 31, cobertura_programa: 6 },
      { skill: 'TensorFlow', frecuencia_mercado: 22, cobertura_programa: 5 },
      { skill: 'Machine Learning', frecuencia_mercado: 20, cobertura_programa: 5 },
      { skill: 'PyTorch', frecuencia_mercado: 18, cobertura_programa: 4 },
    ],
    brechas: [
      { skill: 'AWS',        frecuencia_mercado: 15 }, { skill: 'Docker',    frecuencia_mercado: 13 },
      { skill: 'Kubernetes', frecuencia_mercado: 11 }, { skill: 'Spark',     frecuencia_mercado: 10 },
      { skill: 'MLflow',     frecuencia_mercado: 9  },
    ],
    exclusivas_programa: [
      { skill: 'Estadística', cobertura: 4 }, { skill: 'Álgebra Lineal', cobertura: 3 },
      { skill: 'Scikit-learn', cobertura: 3 }, { skill: 'NLP', cobertura: 2 },
    ],
  },
  108: {
    program_id: 108, cobertura_pct: 38,
    skills_mercado:  [
      { skill: 'Investigación',   frecuencia: 18 }, { skill: 'Excel',          frecuencia: 15 },
      { skill: 'Análisis datos',  frecuencia: 14 }, { skill: 'Derecho Penal',  frecuencia: 13 },
      { skill: 'SPSS',            frecuencia: 11 }, { skill: 'Redacción',      frecuencia: 10 },
      { skill: 'Python',          frecuencia: 8  }, { skill: 'Power BI',       frecuencia: 7  },
      { skill: 'GIS',             frecuencia: 6  }, { skill: 'R',              frecuencia: 5  },
    ],
    skills_programa: [
      { skill: 'Investigación',  cobertura: 5 }, { skill: 'Derecho Penal',   cobertura: 4 },
      { skill: 'Criminología',   cobertura: 4 }, { skill: 'Excel',           cobertura: 2 },
      { skill: 'Estadística',    cobertura: 3 }, { skill: 'Victimología',    cobertura: 3 },
    ],
    fortalezas: [
      { skill: 'Investigación', frecuencia_mercado: 18, cobertura_programa: 5 },
      { skill: 'Excel', frecuencia_mercado: 15, cobertura_programa: 2 },
      { skill: 'Derecho Penal', frecuencia_mercado: 13, cobertura_programa: 4 },
    ],
    brechas: [
      { skill: 'Análisis datos', frecuencia_mercado: 14 }, { skill: 'SPSS',     frecuencia_mercado: 11 },
      { skill: 'Redacción',      frecuencia_mercado: 10 }, { skill: 'Python',   frecuencia_mercado: 8  },
      { skill: 'Power BI',       frecuencia_mercado: 7  }, { skill: 'GIS',      frecuencia_mercado: 6  },
      { skill: 'R',              frecuencia_mercado: 5  },
    ],
    exclusivas_programa: [
      { skill: 'Criminología', cobertura: 4 }, { skill: 'Victimología', cobertura: 3 },
      { skill: 'Estadística', cobertura: 3 },
    ],
  },
};

function SkillsGapChart({ programId }: { programId: number }) {
  const [data, setData]             = useState<SkillsAnalysis | null>(null);
  const [loading, setLoading]       = useState(false);
  const [isFallback, setIsFallback] = useState(false);
  const [activeTab, setActiveTab]   = useState('Todos');

  useEffect(() => {
    setLoading(true);
    setData(null);
    setIsFallback(false);
    fetch(`${API}/api/dashboard/skills-analysis/${programId}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: SkillsAnalysis) => { setData(d); setLoading(false); })
      .catch(() => {
        setData(FALLBACK_SKILLS[programId] ?? FALLBACK_SKILLS[94]);
        setIsFallback(true);
        setLoading(false);
      });
  }, [programId]);

  // Build unified skill list for mirror chart
  const rows = (() => {
    if (!data) return [];
    const mercadoMap = new Map(data.skills_mercado.map(s => [s.skill.toLowerCase(), s.frecuencia]));
    const programaMap = new Map(data.skills_programa.map(s => [s.skill.toLowerCase(), s.cobertura]));
    const allSkills = new Set([...mercadoMap.keys(), ...programaMap.keys()]);
    return [...allSkills].map(key => ({
      skill:      key,
      leftVal:    programaMap.get(key) ?? 0,
      rightVal:   mercadoMap.get(key)  ?? 0,
      inProgram:  programaMap.has(key),
      category:   categorize(key),
    })).sort((a, b) => b.rightVal - a.rightVal);
  })();

  const filtered = activeTab === 'Todos' ? rows : rows.filter(r => r.category === activeTab);
  const maxVal = Math.max(...rows.map(r => Math.max(r.leftVal, r.rightVal)), 1);

  return (
    <div className="rounded-2xl overflow-hidden border" style={{ background: C.bg }}>
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="w-10 h-10 rounded-full border-4 border-blue-200 border-t-blue-700 animate-spin" />
        </div>
      )}

      {!loading && isFallback && (
        <div className="mx-4 mt-3 rounded-lg px-3 py-1.5 text-xs text-center"
          style={{ background: C.goldBg, color: C.gold }}>
          ⚠ Datos de referencia — API no disponible
        </div>
      )}

      {!loading && data && (
        <>
          {/* KPI summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4">
            {[
              { k: 'Cobertura',    v: `${data.cobertura_pct}%`, c: '#0D2158' },
              { k: 'Fortalezas',   v: data.fortalezas.length,   c: '#2563eb' },
              { k: 'Brechas',      v: data.brechas.length,      c: '#dc2626' },
              { k: 'Exclusivas',   v: data.exclusivas_programa.length, c: C.gold },
            ].map(({ k, v, c }) => (
              <div key={k} className="rounded-xl border bg-white p-3 text-center shadow-sm">
                <p className="text-2xl font-extrabold" style={{ color: c }}>{v}</p>
                <p className="text-xs text-gray-500 mt-0.5">{k}</p>
              </div>
            ))}
          </div>

          {/* legend */}
          <div className="flex gap-4 px-5 pb-2 text-xs text-gray-500">
            <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{ background: '#0D2158' }} />Programa (cobertura)</span>
            <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{ background: '#2563eb' }} />Mercado cubierto</span>
            <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{ background: '#ef4444' }} />Brecha (solo en mercado)</span>
          </div>

          {/* tabs */}
          <div className="flex flex-wrap gap-1 px-5 pb-3">
            {ALL_CATS.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveTab(cat)}
                className="rounded-full px-3 py-1 text-xs font-semibold transition-colors"
                style={activeTab === cat
                  ? { background: C.navy, color: C.white }
                  : { background: '#e5e7eb', color: '#374151' }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* mirror bars */}
          <div className="px-4 pb-5 space-y-1">
            {/* axis header */}
            <div className="flex items-center gap-1 text-[10px] text-gray-400 mb-2">
              <span className="w-6" />
              <div className="text-right" style={{ width: '38%' }}>← Programa</div>
              <div className="w-[24%] text-center">Skill</div>
              <div style={{ width: '38%' }}>Mercado →</div>
              <span className="w-6" />
            </div>
            {filtered.slice(0, 25).map(r => (
              <MirrorBar
                key={r.skill}
                skill={r.skill}
                leftVal={r.leftVal}
                rightVal={r.rightVal}
                maxVal={maxVal}
                inProgram={r.inProgram}
              />
            ))}
            {filtered.length === 0 && (
              <p className="text-center text-sm text-gray-400 py-6">Sin skills en esta categoría</p>
            )}
          </div>
        </>
      )}

    </div>
  );
}

// ─── University Benchmark types ───────────────────────────────────────────────
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

// UNIR's own program reference data
const UNIR_PROGRAMS: Record<number, { nombre: string; creditos: number; duracion: string; periodicidad: string }> = {
  94:  { nombre: 'Especialización en Visual Analytics y Big Data', creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  92:  { nombre: 'Especialización en Inteligencia Artificial',     creditos: 30, duracion: '2', periodicidad: 'Semestral' },
  108: { nombre: 'Especialización en Criminología',               creditos: 24, duracion: '2', periodicidad: 'Semestral' },
};

const BENCH_PROGRAMS = [
  { id: 94,  label: 'Visual Analytics & Big Data' },
  { id: 92,  label: 'Inteligencia Artificial' },
  { id: 108, label: 'Especialización en Criminología' },
];

function UniversityBenchmark({ programId }: { programId: number }) {
  const [data, setData]           = useState<UniversityData | null>(null);
  const [loading, setLoading]     = useState(false);

  useEffect(() => {
    setLoading(true);
    setData(null);
    fetch(`${API}/api/programs/related-universities/${programId}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: UniversityData) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [programId]);

  // UNIR self-reported stats per program (used for ranking computation)
  const UNIR_STATS: Record<number, { matriculados: number; graduados: number }> = {
    94:  { matriculados: 0, graduados: 0 }, // populated from real data when available
    92:  { matriculados: 0, graduados: 0 },
    108: { matriculados: 0, graduados: 0 },
  };

  // Derived metrics
  const metrics = (() => {
    if (!data || !data.competitors.length) return null;
    const withCredits = data.competitors.filter(c => c.creditos != null);
    const avgCredits = withCredits.length
      ? Math.round(withCredits.reduce((s, c) => s + (c.creditos ?? 0), 0) / withCredits.length)
      : null;
    const withDur = data.competitors.filter(c => c.duracion && !isNaN(Number(c.duracion)));
    const avgDur = withDur.length
      ? (withDur.reduce((s, c) => s + Number(c.duracion), 0) / withDur.length).toFixed(1)
      : null;
    const cityCount: Record<string, number> = {};
    data.competitors.forEach(c => {
      const city = c.municipio || c.ciudad || 'N/D';
      cityCount[city] = (cityCount[city] ?? 0) + 1;
    });
    const topCities = Object.entries(cityCount).sort((a, b) => b[1] - a[1]).slice(0, 3);

    // UNIR ranking: insert UNIR into sorted competitor list and find position
    const unirStats = UNIR_STATS[programId] ?? { matriculados: 0, graduados: 0 };
    const allGrad = [...data.competitors.map(c => c.graduados), unirStats.graduados].sort((a, b) => b - a);
    const allMat  = [...data.competitors.map(c => c.matriculados), unirStats.matriculados].sort((a, b) => b - a);
    const unirRankGrad = unirStats.graduados   > 0 ? allGrad.indexOf(unirStats.graduados) + 1   : null;
    const unirRankMat  = unirStats.matriculados > 0 ? allMat.indexOf(unirStats.matriculados) + 1 : null;

    return { avgCredits, avgDur, topCities, unirRankGrad, unirRankMat };
  })();

  const unir = UNIR_PROGRAMS[programId];

  return (
    <div className="space-y-5">
      <p className="text-xs text-gray-500 mb-4">Programas activos modalidad virtual registrados en SNIES / HECAA</p>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="w-10 h-10 rounded-full border-4 border-blue-200 border-t-blue-700 animate-spin" />
        </div>
      )}

      {!loading && data && (
        <>
          {/* UNIR positioning badge */}
          <div className="rounded-2xl p-5 flex flex-wrap items-center gap-5"
            style={{ background: C.navy, border: `2px solid ${C.gold}` }}>
            <div className="flex-1 min-w-[200px]">
              <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>
                ✦ Posicionamiento UNIR Colombia
              </p>
              <p className="text-sm font-semibold text-white leading-snug">{unir.nombre}</p>
              <p className="text-xs text-blue-300 mt-1">Modalidad Virtual · Colombia</p>
            </div>
            <div className="flex gap-6">
              {[
                { k: 'Créditos', v: unir.creditos },
                { k: 'Duración (sem.)', v: unir.duracion },
                { k: 'Admisión', v: unir.periodicidad },
              ].map(({ k, v }) => (
                <div key={k} className="text-center">
                  <p className="text-2xl font-extrabold" style={{ color: C.mid }}>{v}</p>
                  <p className="text-xs text-blue-300">{k}</p>
                </div>
              ))}
            </div>
            <div className="rounded-xl px-4 py-2 text-xs font-bold text-center"
              style={{ background: C.gold, color: '#fff' }}>
              {data.total} competidores<br />en SNIES
            </div>
          </div>

          {/* KPI cards */}
          {metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                { k: 'Competidores SNIES',    v: data.total,                             c: C.navy    },
                { k: 'Créditos prom.',         v: metrics.avgCredits ?? '—',             c: '#2563eb' },
                { k: 'Duración prom. (sem.)',  v: metrics.avgDur ?? '—',                 c: C.gold    },
                { k: 'Top ciudad',             v: metrics.topCities[0]?.[0] ?? '—',      c: '#7c3aed' },
                { k: 'Pos. UNIR · Graduados',  v: metrics.unirRankGrad  != null ? `#${metrics.unirRankGrad}`  : '—', c: C.red  },
                { k: 'Pos. UNIR · Matrículas', v: metrics.unirRankMat   != null ? `#${metrics.unirRankMat}`   : '—', c: C.red  },
              ].map(({ k, v, c }) => (
                <div key={k} className="rounded-xl border bg-white p-4 text-center shadow-sm">
                  <p className="text-2xl font-extrabold" style={{ color: c }}>{v}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{k}</p>
                </div>
              ))}
            </div>
          )}

          {/* city distribution */}
          {metrics && metrics.topCities.length > 0 && (
            <div className="rounded-xl border bg-white p-4">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Top ciudades con oferta similar</p>
              <div className="flex flex-wrap gap-2">
                {metrics.topCities.map(([city, count]) => (
                  <span key={city} className="rounded-full px-3 py-1 text-xs font-semibold"
                    style={{ background: '#EEF2FB', color: C.navy, border: `1px solid #D8DEF0` }}>
                    {city} · {count} prog.
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* competitors table */}
          {data.competitors.length > 0 ? (
            <div className="rounded-2xl border shadow-sm" style={{ overflowX: 'auto' }}>
              <table className="text-xs" style={{ minWidth: '920px', width: '100%' }}>
                <thead style={{ background: C.navy }}>
                  <tr>
                    {['Universidad', 'Programa', 'Ciudad', 'Créditos', 'Duración', 'Periodicidad', 'Matriculados 2024', 'Graduados 2024', 'Inscritos 2024'].map(h => (
                      <th key={h} className="px-3 py-2 text-left font-semibold text-blue-200 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {data.competitors.map((c, i) => (
                    <tr key={i} className="hover:bg-blue-50 transition-colors">
                      <td className="px-3 py-2 font-medium text-gray-800" style={{ minWidth: '220px' }}>{c.nombre_ies}</td>
                      <td className="px-3 py-2 text-gray-600" style={{ minWidth: '280px' }}>{c.nombre_programa}</td>
                      <td className="px-3 py-2 text-gray-500 whitespace-nowrap" style={{ minWidth: '120px' }}>{c.municipio || c.ciudad || '—'}</td>
                      <td className="px-3 py-2 text-center font-mono" style={{ color: C.navy }}>{c.creditos ?? '—'}</td>
                      <td className="px-3 py-2 text-center text-gray-500">{c.duracion || '—'}</td>
                      <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{c.periodicidad_admision || '—'}</td>
                      <td className="px-3 py-2 text-center font-semibold" style={{ color: c.matriculados > 0 ? C.navy : '#9ca3af' }}>{c.matriculados > 0 ? c.matriculados.toLocaleString('es-CO') : '—'}</td>
                      <td className="px-3 py-2 text-center font-semibold" style={{ color: c.graduados > 0 ? '#059669' : '#9ca3af' }}>{c.graduados > 0 ? c.graduados.toLocaleString('es-CO') : '—'}</td>
                      <td className="px-3 py-2 text-center text-gray-500">{c.inscritos > 0 ? c.inscritos.toLocaleString('es-CO') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-center text-sm text-gray-400 py-8">
              No se encontraron programas competidores en SNIES para este dominio.<br />
              <span className="text-xs">Verifica que la tabla mineducacion_programas_virtuales tenga datos.</span>
            </p>
          )}
        </>
      )}

      {!loading && !data && (
        <p className="text-center text-sm text-gray-400 py-10">No se pudieron cargar los datos de benchmark</p>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ObservatorioStorytelling() {
  const [data, setData]       = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [programaId, setProgramaId] = useState(94);

  useEffect(() => {
    fetch(`${API}/api/dashboard/summary`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: Summary) => { setData(d); setLoading(false); })
      .catch(() => { setData(FALLBACK); setUsingFallback(true); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: C.bg }}>
      <div className="text-center space-y-4">
        <div className="mx-auto w-14 h-14 rounded-full border-4 border-blue-200 border-t-blue-900 animate-spin" />
        <p style={{ color: C.navy }} className="text-sm font-medium">Cargando observatorio…</p>
      </div>
    </div>
  );

  const d = data!;
  const programaLabel = BENCH_PROGRAMS.find(p => p.id === programaId)?.label ?? 'Visual Analytics & Big Data';
  const lec = buildLecturas(d);
  const { totales, programas, top_matches } = d;
  const coveragePct = totales.matches ? Math.round(((totales.alta + totales.media) / totales.matches) * 100) : 0;
  const altaPct     = totales.matches ? Math.round((totales.alta  / totales.matches) * 100) : 0;
  const mediaPct    = totales.matches ? Math.round((totales.media / totales.matches) * 100) : 0;
  const bajaPct     = totales.matches ? Math.round((totales.baja  / totales.matches) * 100) : 0;

  return (
    <div style={{ background: C.bg, fontFamily: 'system-ui, sans-serif' }}>

      {usingFallback && (
        <div className="text-center text-xs py-2 px-4" style={{ background: C.goldBg, color: C.gold }}>
          ⚠ Mostrando datos de referencia (run #6) — API no disponible
        </div>
      )}

      {/* ── PORTADA ── */}
      <header className="relative overflow-hidden py-16 px-4"
        style={{ background: C.navy }}>
        {/* watermark */}
        <span className="absolute inset-0 flex items-center justify-center text-white font-black select-none pointer-events-none"
          style={{ fontSize: '20rem', opacity: 0.04 }}>OI</span>

        {/* nav logo bar */}
        <div className="relative z-10 max-w-4xl mx-auto flex items-center gap-4 mb-10">
          {/* UNIR square logo */}
          <div className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center font-extrabold text-white text-xl"
            style={{ background: C.red }}>
            U
          </div>
          <div className="text-left">
            <p className="text-white font-bold text-base leading-tight">UNIR Colombia</p>
            <p className="text-xs font-medium" style={{ color: C.light }}>Observatorio Institucional</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <select
              value={programaId}
              onChange={e => setProgramaId(Number(e.target.value))}
              style={{ background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 4, padding: '6px 12px', fontSize: 11 }}
            >
              <option value={94} style={{ color: '#111', background: '#fff' }}>Visual Analytics &amp; Big Data</option>
              <option value={92} style={{ color: '#111', background: '#fff' }}>Inteligencia Artificial</option>
              <option value={108} style={{ color: '#111', background: '#fff' }}>Criminología</option>
            </select>
            <span className="rounded-full px-3 py-1 text-xs font-semibold"
              style={{ background: 'rgba(255,255,255,0.1)', color: C.light, border: `1px solid ${C.border}40` }}>
              Run #{d.run_id} · {d.fecha}
            </span>
          </div>
        </div>

        {/* hero content */}
        <div className="relative z-10 max-w-3xl mx-auto text-center space-y-4">
          <p className="text-xs uppercase tracking-widest font-bold" style={{ color: C.light }}>
            Motor de Pertinencia Académica
          </p>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight">
            Inteligencia Curricular<br />& Pertinencia Académica
          </h1>
          <p className="text-base font-semibold max-w-xl mx-auto" style={{ color: '#fcd34d' }}>
            {programaLabel}
          </p>
          <p className="text-sm max-w-xl mx-auto" style={{ color: C.light }}>
            {totales.matches.toLocaleString()} pares programa–empleo analizados
          </p>
          {/* hero rings */}
          <div className="flex flex-wrap justify-center gap-8 pt-8">
            {[
              { label: 'Cobertura pertinente', val: coveragePct, color: C.light   },
              { label: 'Alta pertinencia',     val: altaPct,     color: '#93c5fd' },
              { label: 'Pertinencia media',    val: mediaPct,    color: '#fcd34d' },
              { label: 'Baja pertinencia',     val: bajaPct,     color: '#fca5a5' },
            ].map(({ label, val, color }) => (
              <div key={label} className="flex flex-col items-center gap-2">
                <Ring score={val} color={color} size={120} />
                <span className="text-xs" style={{ color: C.light }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── SECCIÓN 1: Cobertura ── */}
      <Section n="1" title="Cobertura de Pertinencia">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { k: 'Matches totales', v: totales.matches, c: C.navy  },
            { k: 'Alta pertinencia', v: totales.alta,   c: '#2563eb' },
            { k: 'Media',           v: totales.media,   c: C.gold  },
            { k: 'Baja',            v: totales.baja,    c: C.red   },
          ].map(({ k, v, c }) => (
            <div key={k} className="rounded-2xl border bg-white p-4 text-center shadow-sm">
              <p className="text-3xl font-extrabold" style={{ color: c }}>{v}</p>
              <p className="text-xs text-gray-500 mt-1">{k}</p>
            </div>
          ))}
        </div>
        {/* stacked bar */}
        <div className="rounded-xl overflow-hidden h-6 flex mb-2">
          <div style={{ width: `${altaPct}%`,  background: '#0D2158', transition: 'width 1.2s ease' }} />
          <div style={{ width: `${mediaPct}%`, background: C.gold,    transition: 'width 1.2s ease' }} />
          <div style={{ width: `${bajaPct}%`,  background: '#ef4444', transition: 'width 1.2s ease' }} />
        </div>
        <div className="flex gap-4 text-xs text-gray-500 mb-4">
          <span><span style={{ color: '#0D2158' }}>■</span> Alta {altaPct}%</span>
          <span><span style={{ color: C.gold   }}>■</span> Media {mediaPct}%</span>
          <span><span style={{ color: '#ef4444' }}>■</span> Baja {bajaPct}%</span>
        </div>
        <LecturaKey text={lec.cobertura} />
      </Section>

      {/* ── SECCIÓN 2: Ranking de programas ── */}
      <Section n="2" title="Ranking de Programas" dark>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...programas]
            .sort((a, b) => {
              if (a.id === programaId) return -1;
              if (b.id === programaId) return 1;
              return b.score_maximo - a.score_maximo;
            })
            .map((p, i) => {
              const isSelected = p.id === programaId;
              const tot = p.labels.high + p.labels.medium + p.labels.low || 1;
              const ringC = p.score_maximo >= 75 ? C.mid : p.score_maximo >= 55 ? C.gold : '#fca5a5';
              return (
                <div key={p.id} className="rounded-2xl p-5 flex flex-col gap-3"
                  style={{ background: isSelected ? 'rgba(255,255,255,0.13)' : 'rgba(255,255,255,0.07)', border: isSelected ? `2px solid ${C.gold}` : '1px solid rgba(255,255,255,0.12)' }}>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-black" style={{ color: 'rgba(255,255,255,0.2)' }}>
                      #{i + 1}
                    </span>
                    <p className="text-sm font-semibold text-white leading-snug">{p.nombre}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <Ring score={p.score_maximo} color={ringC} size={90} thick={8} />
                    <div className="flex-1 space-y-2 text-xs">
                      {[
                        { l: 'Alta',  v: p.labels.high,   c: '#86efac', pct: (p.labels.high   / tot) * 100 },
                        { l: 'Media', v: p.labels.medium, c: C.gold,    pct: (p.labels.medium / tot) * 100 },
                        { l: 'Baja',  v: p.labels.low,    c: '#fca5a5', pct: (p.labels.low    / tot) * 100 },
                      ].map(({ l, v, c, pct }) => (
                        <div key={l}>
                          <div className="flex justify-between mb-0.5">
                            <span style={{ color: c }}>{l}</span>
                            <span className="text-blue-200">{v}</span>
                          </div>
                          <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: c, transition: 'width 1.2s ease' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-blue-300">
                    <span>{p.matches_total} empleos</span>
                    <span>Prom. {p.score_promedio}</span>
                  </div>
                </div>
              );
            })}
        </div>
        <div style={{ borderLeft: `4px solid ${C.gold}`, background: 'rgba(183,121,31,0.15)' }}
          className="rounded-r-xl px-5 py-4 mt-6">
          <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>✦ Lectura Clave</p>
          <p className="text-sm text-blue-100">{lec.ranking}</p>
        </div>
      </Section>

      {/* ── SECCIÓN 3: Distribución ── */}
      <Section n="3" title="Distribución de Pertinencia">
        <div className="flex flex-wrap justify-center gap-10 mb-6">
          {[
            { label: 'Alta pertinencia',  val: altaPct,  color: '#0D2158', count: totales.alta  },
            { label: 'Pertinencia media', val: mediaPct, color: C.gold,    count: totales.media },
            { label: 'Baja pertinencia',  val: bajaPct,  color: '#b91c1c', count: totales.baja  },
          ].map(({ label, val, color, count }) => (
            <div key={label} className="flex flex-col items-center gap-2">
              <Ring score={val} color={color} size={110} />
              <p className="text-sm font-semibold text-gray-700">{label}</p>
              <p className="text-xs text-gray-400">{count} empleos</p>
            </div>
          ))}
        </div>
        <LecturaKey text={lec.distribucion} />
      </Section>

      {/* ── SECCIÓN 4: Top Matches + Brechas Curriculares ── */}
      <Section n="4" title="Mejores Matches & Brechas Curriculares" dark>
        <div className="space-y-3 mb-6">
          {top_matches.filter(m => {
              const pNom = programas.find(p => p.id === programaId)?.nombre ?? '';
              return pNom ? m.programa.toLowerCase().includes(pNom.split(' ')[0].toLowerCase()) : true;
            }).slice(0, 10).map((m, i) => (
            <div key={i} className="rounded-xl px-4 py-3"
              style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="flex items-center gap-3">
                <span className="text-xl font-black w-7 text-center flex-shrink-0" style={{ color: 'rgba(255,255,255,0.2)' }}>
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{m.empleo}</p>
                  <p className="text-xs text-blue-300 truncate">{m.programa} · {m.empresa}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-lg font-extrabold" style={{ color: C.mid }}>{m.score.toFixed(0)}</span>
                  <LBadge l={m.label} />
                </div>
              </div>
              {/* skill tags */}
              <div className="mt-2 ml-10 flex flex-wrap gap-1">
                {m.skills_en_comun.length > 0
                  ? m.skills_en_comun.map(s => (
                      <span key={s} className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{ background: 'rgba(134,239,172,0.15)', color: '#86efac', border: '1px solid rgba(134,239,172,0.3)' }}>
                        {s}
                      </span>
                    ))
                  : <span className="text-xs text-green-500 italic">Sin overlap de skills</span>
                }
                {m.skills_faltantes.slice(0, 3).map(s => (
                  <span key={s} className="rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{ background: 'rgba(252,165,165,0.15)', color: '#fca5a5', border: '1px solid rgba(252,165,165,0.3)' }}>
                    -{s}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div style={{ borderLeft: `4px solid ${C.gold}`, background: 'rgba(183,121,31,0.15)' }}
          className="rounded-r-xl px-5 py-4 mb-8">
          <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>✦ Lectura Clave</p>
          <p className="text-sm text-blue-100">{lec.topMatches}</p>
        </div>

        {/* Skills Gap Chart within section 4 */}
        <SkillsGapChart programId={programaId} />
      </Section>

      {/* ── SECCIÓN 5: Tabla completa ── */}
      <Section n="5" title="Análisis Detallado de Matches">
        <div className="rounded-2xl overflow-hidden shadow-sm border">
          <table className="min-w-full text-sm">
            <thead style={{ background: C.navy }}>
              <tr>
                {['#', 'Programa', 'Empleo', 'Empresa', 'Score', 'Label'].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-blue-200">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {top_matches.slice(0, 20).map((m, i) => (
                <tr key={i} className="hover:bg-blue-50 transition-colors">
                  <td className="px-3 py-2 text-gray-400 font-mono text-xs">{i + 1}</td>
                  <td className="px-3 py-2 text-gray-700 max-w-[150px] truncate text-xs">{m.programa}</td>
                  <td className="px-3 py-2 text-gray-800 font-medium max-w-[180px] truncate text-xs">{m.empleo}</td>
                  <td className="px-3 py-2 text-gray-400 max-w-[110px] truncate text-xs">{m.empresa}</td>
                  <td className="px-3 py-2 font-bold" style={{ color: C.navy }}>{m.score.toFixed(1)}</td>
                  <td className="px-3 py-2"><LBadge l={m.label} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <LecturaKey text={lec.brechas} />
      </Section>

      {/* ── SECCIÓN 6: Recomendaciones ── */}
      <Section n="6" title="Recomendaciones Curriculares">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
          {/* Incorporar */}
          <div className="rounded-2xl border-2 p-5 space-y-3" style={{ borderColor: '#0D2158', background: '#EEF2FB' }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">✅</span>
              <h3 className="text-sm font-bold" style={{ color: '#0D2158' }}>Incorporar</h3>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              Skills de alta demanda en el mercado que aún no están en el currículo. Agregar como módulos obligatorios o electivos.
            </p>
            <ul className="space-y-1">
              {['Cloud computing (AWS/Azure)', 'MLOps y despliegue de modelos', 'Ingeniería de datos (Spark/Airflow)', 'LLMs y prompting avanzado'].map(s => (
                <li key={s} className="flex items-start gap-1.5 text-xs text-gray-700">
                  <span style={{ color: '#0D2158' }} className="mt-0.5 flex-shrink-0">+</span>
                  {s}
                </li>
              ))}
            </ul>
            <div className="rounded-lg px-3 py-2 text-xs font-semibold text-center" style={{ background: '#D8DEF0', color: '#0D2158' }}>
              Impacto estimado: +18% pertinencia
            </div>
          </div>

          {/* Fortalecer */}
          <div className="rounded-2xl border-2 p-5 space-y-3" style={{ borderColor: '#d97706', background: '#fffbeb' }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">🔧</span>
              <h3 className="text-sm font-bold" style={{ color: '#d97706' }}>Fortalecer</h3>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              Skills presentes en el currículo con cobertura parcial. Ampliar profundidad o actualizar versiones.
            </p>
            <ul className="space-y-1">
              {['Python (de básico a avanzado)', 'SQL y bases de datos NoSQL', 'Visualización interactiva (Power BI)', 'Metodologías ágiles aplicadas'].map(s => (
                <li key={s} className="flex items-start gap-1.5 text-xs text-gray-700">
                  <span style={{ color: '#d97706' }} className="mt-0.5 flex-shrink-0">~</span>
                  {s}
                </li>
              ))}
            </ul>
            <div className="rounded-lg px-3 py-2 text-xs font-semibold text-center" style={{ background: '#fef3c7', color: '#d97706' }}>
              Impacto estimado: +11% pertinencia
            </div>
          </div>

          {/* Revisar / retirar */}
          <div className="rounded-2xl border-2 p-5 space-y-3" style={{ borderColor: '#dc2626', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">⚠️</span>
              <h3 className="text-sm font-bold" style={{ color: '#dc2626' }}>Revisar / Retirar</h3>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              Skills del currículo con baja o nula demanda en el mercado. Evaluar pertinencia o sustituir.
            </p>
            <ul className="space-y-1">
              {['Herramientas legacy sin demanda', 'Contenidos teóricos sin aplicación práctica', 'Tecnologías obsoletas en el sector', 'Marcos metodológicos desactualizados'].map(s => (
                <li key={s} className="flex items-start gap-1.5 text-xs text-gray-700">
                  <span style={{ color: '#dc2626' }} className="mt-0.5 flex-shrink-0">−</span>
                  {s}
                </li>
              ))}
            </ul>
            <div className="rounded-lg px-3 py-2 text-xs font-semibold text-center" style={{ background: '#fee2e2', color: '#dc2626' }}>
              Liberaría espacio curricular: ~15%
            </div>
          </div>
        </div>

        {/* Impacto proyectado */}
        <div className="rounded-2xl border bg-white p-6 mb-4 shadow-sm">
          <h4 className="text-sm font-bold text-gray-800 mb-4">Impacto Proyectado con Actualización Curricular</h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            {[
              { label: 'Cobertura actual',       val: `${coveragePct}%`,  color: C.gold,    sub: 'pertinencia media + alta' },
              { label: 'Proyección post-mejoras', val: `${Math.min(coveragePct + 29, 99)}%`, color: '#0D2158', sub: 'incorporando recomendaciones' },
              { label: 'Empleabilidad estimada', val: '+24%',              color: '#2563eb', sub: 'vs. egresados actuales' },
            ].map(({ label, val, color, sub }) => (
              <div key={label}>
                <p className="text-3xl font-extrabold" style={{ color }}>{val}</p>
                <p className="text-xs font-semibold text-gray-600 mt-0.5">{label}</p>
                <p className="text-xs text-gray-400">{sub}</p>
              </div>
            ))}
          </div>
        </div>

        <LecturaKey text={lec.brechas} />
      </Section>

      {/* ── SECCIÓN 7: Benchmark y Competencia ── */}
      <Section n="7" title="Benchmark y Competencia SNIES">
        <UniversityBenchmark programId={programaId} />
      </Section>

      {/* ── CIERRE ── */}
      <section className="py-20 px-4 text-center" style={{ background: C.navy }}>
        <div className="max-w-2xl mx-auto space-y-5">
          <p className="text-xs uppercase tracking-widest font-bold" style={{ color: C.mid }}>Sección 8 · Conclusión</p>
          <h2 className="text-3xl font-extrabold text-white">Evidencia para la Decisión Curricular</h2>
          <p className="text-blue-200 text-sm leading-relaxed">{lec.cierre}</p>
          <div className="inline-block rounded-2xl px-8 py-4 mt-4" style={{ background: 'rgba(255,255,255,0.08)' }}>
            <p className="text-4xl font-extrabold" style={{ color: C.mid }}>{coveragePct}%</p>
            <p className="text-xs text-blue-300 mt-1">cobertura pertinente global</p>
          </div>
          <p className="text-xs text-blue-400 pt-4">
            Run #{d.run_id} · {d.fecha} · Motor de Pertinencia Académica v2
          </p>
        </div>
      </section>

    </div>
  );
}
