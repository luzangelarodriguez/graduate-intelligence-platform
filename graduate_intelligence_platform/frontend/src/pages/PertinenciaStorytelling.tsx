import { useEffect, useRef, useState } from 'react';

const API = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

// ─── types ────────────────────────────────────────────────────────────────────

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
}

interface Summary {
  run_id: number | null;
  fecha: string;
  programas: Programa[];
  top_matches: TopMatch[];
  totales: { matches: number; alta: number; media: number; baja: number };
}

// ─── SVG ring ─────────────────────────────────────────────────────────────────

const R = 40;
const CIRC = 2 * Math.PI * R;

function ScoreRing({
  score,
  label,
  color,
  size = 100,
}: {
  score: number;
  label: string;
  color: string;
  size?: number;
}) {
  const [animated, setAnimated] = useState(0);
  const ref = useRef<SVGCircleElement>(null);

  useEffect(() => {
    const raf = requestAnimationFrame(() => setAnimated(score));
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const dash = (animated / 100) * CIRC;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 100 100">
        {/* track */}
        <circle cx="50" cy="50" r={R} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        {/* fill */}
        <circle
          ref={ref}
          cx="50"
          cy="50"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${CIRC}`}
          strokeDashoffset={CIRC * 0.25}          /* start at top */
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)' }}
        />
        <text x="50" y="46" textAnchor="middle" fontSize="16" fontWeight="700" fill={color}>
          {Math.round(animated)}
        </text>
        <text x="50" y="60" textAnchor="middle" fontSize="9" fill="#6b7280">
          / 100
        </text>
      </svg>
      <span className="text-xs text-gray-500 text-center max-w-[90px] leading-tight">{label}</span>
    </div>
  );
}

// ─── label badge ──────────────────────────────────────────────────────────────

const LABEL_META: Record<string, { text: string; bg: string; fg: string }> = {
  high:   { text: 'Alta',  bg: '#dcfce7', fg: '#16a34a' },
  medium: { text: 'Media', bg: '#fef9c3', fg: '#ca8a04' },
  low:    { text: 'Baja',  bg: '#fee2e2', fg: '#dc2626' },
};

function LabelBadge({ label }: { label: string }) {
  const m = LABEL_META[label] ?? { text: label, bg: '#f3f4f6', fg: '#374151' };
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ background: m.bg, color: m.fg }}
    >
      {m.text}
    </span>
  );
}

// ─── Program card ──────────────────────────────────────────────────────────────

function ProgramCard({ p, index }: { p: Programa; index: number }) {
  const total = p.labels.high + p.labels.medium + p.labels.low || 1;
  const highPct = (p.labels.high / total) * 100;

  const ringColor =
    p.score_maximo >= 75 ? '#16a34a' : p.score_maximo >= 55 ? '#d97706' : '#dc2626';

  return (
    <div
      className="rounded-2xl border bg-white p-5 shadow-sm flex flex-col gap-4"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-800 leading-snug">{p.nombre}</h3>
        <span className="text-xs text-gray-400 whitespace-nowrap">{p.matches_total} empleos</span>
      </div>

      {/* ring + bars */}
      <div className="flex items-center gap-5">
        <ScoreRing score={p.score_maximo} label="Score máx." color={ringColor} size={90} />

        <div className="flex-1 space-y-2">
          {/* Alta bar */}
          <div>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-green-600 font-medium">Alta</span>
              <span className="text-gray-500">{p.labels.high}</span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-green-500"
                style={{
                  width: `${(p.labels.high / total) * 100}%`,
                  transition: 'width 1s ease',
                }}
              />
            </div>
          </div>
          {/* Media bar */}
          <div>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-yellow-600 font-medium">Media</span>
              <span className="text-gray-500">{p.labels.medium}</span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-yellow-400"
                style={{
                  width: `${(p.labels.medium / total) * 100}%`,
                  transition: 'width 1s ease',
                }}
              />
            </div>
          </div>
          {/* Baja bar */}
          <div>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-red-500 font-medium">Baja</span>
              <span className="text-gray-500">{p.labels.low}</span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-red-400"
                style={{
                  width: `${(p.labels.low / total) * 100}%`,
                  transition: 'width 1s ease',
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 border-t pt-2">
        <span>Promedio <strong className="text-gray-700">{p.score_promedio}</strong></span>
        <span className="text-green-600 font-medium">{Math.round(highPct)}% alta pertinencia</span>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PertinenciaStorytelling() {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/dashboard/summary`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} — ${r.url}`);
        return r.json();
      })
      .then((d: Summary) => { setData(d); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-full border-4 border-indigo-200 border-t-indigo-600 animate-spin" />
          <p className="text-gray-500 text-sm">Cargando inteligencia curricular…</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-2xl shadow p-8 max-w-sm text-center space-y-2">
          <p className="text-red-600 font-semibold">No se pudieron cargar los datos</p>
          <p className="text-gray-400 text-xs break-all">{error}</p>
        </div>
      </div>
    );
  }

  const { programas, top_matches, totales, run_id, fecha } = data;
  const coveragePct = totales.matches
    ? Math.round(((totales.alta + totales.media) / totales.matches) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 py-10 px-4">
      <div className="max-w-5xl mx-auto space-y-10">

        {/* ── Hero ── */}
        <header className="text-center space-y-2">
          <p className="text-xs uppercase tracking-widest text-indigo-400 font-semibold">
            Motor de Pertinencia Académica · Run #{run_id} · {fecha}
          </p>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight">
            ¿Qué tan relevantes son<br className="hidden sm:block" /> nuestros programas?
          </h1>
          <p className="text-gray-500 max-w-xl mx-auto text-sm">
            Análisis semántico de {totales.matches.toLocaleString()} pares programa–empleo.
            El {coveragePct}% tiene pertinencia media o alta.
          </p>
        </header>

        {/* ── KPI rings ── */}
        <section className="bg-white rounded-3xl shadow-sm p-6 flex flex-wrap justify-center gap-8">
          <ScoreRing score={coveragePct}   label="Cobertura pertinente" color="#6366f1" size={110} />
          <ScoreRing
            score={totales.matches ? Math.round((totales.alta / totales.matches) * 100) : 0}
            label="Alta pertinencia"
            color="#16a34a"
            size={110}
          />
          <ScoreRing
            score={totales.matches ? Math.round((totales.media / totales.matches) * 100) : 0}
            label="Pertinencia media"
            color="#d97706"
            size={110}
          />
          <ScoreRing
            score={totales.matches ? Math.round((totales.baja / totales.matches) * 100) : 0}
            label="Baja pertinencia"
            color="#ef4444"
            size={110}
          />
        </section>

        {/* ── Program cards ── */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-gray-800">Por programa</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {programas.map((p, i) => (
              <ProgramCard key={p.id} p={p} index={i} />
            ))}
          </div>
        </section>

        {/* ── Top matches table ── */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-gray-800">Top 30 matches</h2>
          <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <table className="min-w-full text-sm divide-y divide-gray-100">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  {['#', 'Programa', 'Empleo', 'Empresa', 'Score', 'Label'].map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {top_matches.map((m, i) => (
                  <tr key={i} className="hover:bg-indigo-50/30 transition-colors">
                    <td className="px-4 py-2 text-gray-400 font-mono text-xs">{i + 1}</td>
                    <td className="px-4 py-2 text-gray-700 max-w-[180px] truncate">{m.programa}</td>
                    <td className="px-4 py-2 text-gray-700 max-w-[180px] truncate">{m.empleo}</td>
                    <td className="px-4 py-2 text-gray-400 max-w-[120px] truncate">{m.empresa}</td>
                    <td className="px-4 py-2 font-mono font-bold text-gray-800">{m.score.toFixed(1)}</td>
                    <td className="px-4 py-2"><LabelBadge label={m.label} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  );
}
