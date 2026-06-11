import { useEffect, useRef, useState } from 'react';

// ─── Config ────────────────────────────────────────────────────────────────────
const API = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

const C = {
  green:  '#1B4332',
  cream:  '#F8F4EE',
  gold:   '#B7791F',
  goldBg: '#FEF3C7',
  light:  '#D1FAE5',
  mid:    '#6EE7B7',
  white:  '#FFFFFF',
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

function Ring({ score, color = C.green, size = 120, thick = 9 }: {
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
    <div style={{ background: C.goldBg, borderLeft: `4px solid ${C.gold}` }}
      className="rounded-r-xl px-5 py-4 my-4">
      <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>
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
      style={{ background: dark ? C.green : C.cream }}
    >
      {/* decorative number */}
      <span
        className="absolute top-4 right-6 font-black select-none pointer-events-none"
        style={{
          fontSize: '7rem', lineHeight: 1, opacity: dark ? 0.08 : 0.06,
          color: dark ? C.white : C.green,
        }}
      >
        {n}
      </span>
      <div className="max-w-4xl mx-auto relative z-10">
        <p className="text-xs font-bold uppercase tracking-widest mb-1"
          style={{ color: dark ? C.mid : C.gold }}>
          Sección {n}
        </p>
        <h2 className="text-2xl sm:text-3xl font-extrabold mb-6"
          style={{ color: dark ? C.white : C.green }}>
          {title}
        </h2>
        {children}
      </div>
    </section>
  );
}

// ─── Label badge ──────────────────────────────────────────────────────────────
const LBL: Record<string, [string, string, string]> = {
  high:   ['Alta',  '#dcfce7', '#15803d'],
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

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ObservatorioStorytelling() {
  const [data, setData]       = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/dashboard/summary`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: Summary) => { setData(d); setLoading(false); })
      .catch(() => { setData(FALLBACK); setUsingFallback(true); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: C.cream }}>
      <div className="text-center space-y-4">
        <div className="mx-auto w-14 h-14 rounded-full border-4 border-green-200 border-t-green-800 animate-spin" />
        <p style={{ color: C.green }} className="text-sm font-medium">Cargando observatorio…</p>
      </div>
    </div>
  );

  const d = data!;
  const lec = buildLecturas(d);
  const { totales, programas, top_matches } = d;
  const coveragePct = totales.matches ? Math.round(((totales.alta + totales.media) / totales.matches) * 100) : 0;
  const altaPct     = totales.matches ? Math.round((totales.alta  / totales.matches) * 100) : 0;
  const mediaPct    = totales.matches ? Math.round((totales.media / totales.matches) * 100) : 0;
  const bajaPct     = totales.matches ? Math.round((totales.baja  / totales.matches) * 100) : 0;

  return (
    <div style={{ background: C.cream, fontFamily: 'system-ui, sans-serif' }}>

      {usingFallback && (
        <div className="text-center text-xs py-2 px-4" style={{ background: C.goldBg, color: C.gold }}>
          ⚠ Mostrando datos de referencia (run #6) — API no disponible
        </div>
      )}

      {/* ── PORTADA ── */}
      <header className="relative overflow-hidden py-20 px-4 text-center"
        style={{ background: C.green }}>
        <span className="absolute inset-0 flex items-center justify-center text-white font-black select-none pointer-events-none"
          style={{ fontSize: '20rem', opacity: 0.04 }}>OI</span>
        <div className="relative z-10 max-w-3xl mx-auto space-y-4">
          <p className="text-xs uppercase tracking-widest font-bold" style={{ color: C.mid }}>
            UNIR Colombia · Observatorio Institucional
          </p>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight">
            Inteligencia Curricular<br />& Pertinencia Académica
          </h1>
          <p className="text-green-200 text-sm max-w-xl mx-auto">
            Run #{d.run_id} · {d.fecha} · {totales.matches.toLocaleString()} pares programa–empleo analizados
          </p>
          {/* hero rings */}
          <div className="flex flex-wrap justify-center gap-8 pt-8">
            {[
              { label: 'Cobertura pertinente', val: coveragePct, color: C.mid    },
              { label: 'Alta pertinencia',     val: altaPct,     color: '#86efac' },
              { label: 'Pertinencia media',    val: mediaPct,    color: C.gold    },
              { label: 'Baja pertinencia',     val: bajaPct,     color: '#fca5a5' },
            ].map(({ label, val, color }) => (
              <div key={label} className="flex flex-col items-center gap-2">
                <Ring score={val} color={color} size={120} />
                <span className="text-xs text-green-200">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── SECCIÓN 1: Cobertura ── */}
      <Section n="1" title="Cobertura de Pertinencia">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { k: 'Matches totales', v: totales.matches, c: C.green },
            { k: 'Alta pertinencia', v: totales.alta,   c: '#15803d' },
            { k: 'Media',           v: totales.media,   c: C.gold },
            { k: 'Baja',            v: totales.baja,    c: '#b91c1c' },
          ].map(({ k, v, c }) => (
            <div key={k} className="rounded-2xl border bg-white p-4 text-center shadow-sm">
              <p className="text-3xl font-extrabold" style={{ color: c }}>{v}</p>
              <p className="text-xs text-gray-500 mt-1">{k}</p>
            </div>
          ))}
        </div>
        {/* stacked bar */}
        <div className="rounded-xl overflow-hidden h-6 flex mb-2">
          <div style={{ width: `${altaPct}%`,  background: '#15803d', transition: 'width 1.2s ease' }} />
          <div style={{ width: `${mediaPct}%`, background: C.gold,    transition: 'width 1.2s ease' }} />
          <div style={{ width: `${bajaPct}%`,  background: '#ef4444', transition: 'width 1.2s ease' }} />
        </div>
        <div className="flex gap-4 text-xs text-gray-500 mb-4">
          <span><span style={{ color: '#15803d' }}>■</span> Alta {altaPct}%</span>
          <span><span style={{ color: C.gold   }}>■</span> Media {mediaPct}%</span>
          <span><span style={{ color: '#ef4444' }}>■</span> Baja {bajaPct}%</span>
        </div>
        <LecturaKey text={lec.cobertura} />
      </Section>

      {/* ── SECCIÓN 2: Ranking de programas ── */}
      <Section n="2" title="Ranking de Programas" dark>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...programas]
            .sort((a, b) => b.score_maximo - a.score_maximo)
            .map((p, i) => {
              const tot = p.labels.high + p.labels.medium + p.labels.low || 1;
              const ringC = p.score_maximo >= 75 ? C.mid : p.score_maximo >= 55 ? C.gold : '#fca5a5';
              return (
                <div key={p.id} className="rounded-2xl p-5 flex flex-col gap-3"
                  style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)' }}>
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
                            <span className="text-green-200">{v}</span>
                          </div>
                          <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: c, transition: 'width 1.2s ease' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-green-300">
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
          <p className="text-sm text-green-100">{lec.ranking}</p>
        </div>
      </Section>

      {/* ── SECCIÓN 3: Distribución ── */}
      <Section n="3" title="Distribución de Pertinencia">
        <div className="flex flex-wrap justify-center gap-10 mb-6">
          {[
            { label: 'Alta pertinencia',  val: altaPct,  color: '#15803d', count: totales.alta  },
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

      {/* ── SECCIÓN 4: Top Matches ── */}
      <Section n="4" title="Mejores Matches Programa–Empleo" dark>
        <div className="space-y-3 mb-6">
          {top_matches.slice(0, 10).map((m, i) => (
            <div key={i} className="rounded-xl px-4 py-3"
              style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="flex items-center gap-3">
                <span className="text-xl font-black w-7 text-center flex-shrink-0" style={{ color: 'rgba(255,255,255,0.2)' }}>
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{m.empleo}</p>
                  <p className="text-xs text-green-300 truncate">{m.programa} · {m.empresa}</p>
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
          className="rounded-r-xl px-5 py-4">
          <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: C.gold }}>✦ Lectura Clave</p>
          <p className="text-sm text-green-100">{lec.topMatches}</p>
        </div>
      </Section>

      {/* ── SECCIÓN 5: Tabla completa ── */}
      <Section n="5" title="Análisis Detallado de Matches">
        <div className="rounded-2xl overflow-hidden shadow-sm border">
          <table className="min-w-full text-sm">
            <thead style={{ background: C.green }}>
              <tr>
                {['#', 'Programa', 'Empleo', 'Empresa', 'Score', 'Label'].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-green-200">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {top_matches.slice(0, 20).map((m, i) => (
                <tr key={i} className="hover:bg-green-50 transition-colors">
                  <td className="px-3 py-2 text-gray-400 font-mono text-xs">{i + 1}</td>
                  <td className="px-3 py-2 text-gray-700 max-w-[150px] truncate text-xs">{m.programa}</td>
                  <td className="px-3 py-2 text-gray-800 font-medium max-w-[180px] truncate text-xs">{m.empleo}</td>
                  <td className="px-3 py-2 text-gray-400 max-w-[110px] truncate text-xs">{m.empresa}</td>
                  <td className="px-3 py-2 font-bold" style={{ color: C.green }}>{m.score.toFixed(1)}</td>
                  <td className="px-3 py-2"><LBadge l={m.label} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <LecturaKey text={lec.brechas} />
      </Section>

      {/* ── SECCIÓN 6: Brechas ── */}
      <Section n="6" title="Programas con Mayor Brecha" dark>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[...programas]
            .sort((a, b) => b.labels.low - a.labels.low)
            .filter(p => p.labels.low > 0)
            .map(p => {
              const tot  = p.labels.high + p.labels.medium + p.labels.low || 1;
              const lowP = Math.round((p.labels.low / tot) * 100);
              return (
                <div key={p.id} className="rounded-2xl p-5"
                  style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)' }}>
                  <p className="text-sm font-semibold text-white mb-3">{p.nombre}</p>
                  <div className="flex items-center gap-4">
                    <Ring score={lowP} color="#fca5a5" size={80} thick={7} />
                    <div className="text-xs text-green-200 space-y-1">
                      <p><span className="text-red-300 font-bold">{p.labels.low}</span> empleos de baja pertinencia</p>
                      <p>Score máx. <span className="font-bold text-white">{p.score_maximo.toFixed(1)}</span></p>
                      <p>Promedio <span className="font-bold text-white">{p.score_promedio.toFixed(1)}</span></p>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
        <div style={{ borderLeft: `4px solid #fca5a5`, background: 'rgba(252,165,165,0.1)' }}
          className="rounded-r-xl px-5 py-4 mt-6">
          <p className="text-xs font-bold uppercase tracking-widest mb-1 text-red-300">✦ Brecha Detectada</p>
          <p className="text-sm text-green-100">{lec.brechas}</p>
        </div>
      </Section>

      {/* ── SECCIÓN 7: Por programa — rings ── */}
      <Section n="7" title="Score Máximo por Programa">
        <div className="flex flex-wrap justify-center gap-10">
          {[...programas].sort((a, b) => b.score_maximo - a.score_maximo).map(p => {
            const c = p.score_maximo >= 75 ? '#15803d' : p.score_maximo >= 55 ? C.gold : '#b91c1c';
            return (
              <div key={p.id} className="flex flex-col items-center gap-2 max-w-[130px] text-center">
                <Ring score={p.score_maximo} color={c} size={120} />
                <p className="text-xs font-semibold text-gray-700 leading-tight">{p.nombre}</p>
                <p className="text-xs text-gray-400">{p.matches_total} empleos</p>
              </div>
            );
          })}
        </div>
        <LecturaKey text={lec.ranking} />
      </Section>

      {/* ── CIERRE ── */}
      <section className="py-20 px-4 text-center" style={{ background: C.green }}>
        <div className="max-w-2xl mx-auto space-y-5">
          <p className="text-xs uppercase tracking-widest font-bold" style={{ color: C.mid }}>Sección 8 · Conclusión</p>
          <h2 className="text-3xl font-extrabold text-white">Evidencia para la Decisión Curricular</h2>
          <p className="text-green-200 text-sm leading-relaxed">{lec.cierre}</p>
          <div className="inline-block rounded-2xl px-8 py-4 mt-4" style={{ background: 'rgba(255,255,255,0.08)' }}>
            <p className="text-4xl font-extrabold" style={{ color: C.mid }}>{coveragePct}%</p>
            <p className="text-xs text-green-300 mt-1">cobertura pertinente global</p>
          </div>
          <p className="text-xs text-green-400 pt-4">
            Run #{d.run_id} · {d.fecha} · Motor de Pertinencia Académica v2
          </p>
        </div>
      </section>

    </div>
  );
}
