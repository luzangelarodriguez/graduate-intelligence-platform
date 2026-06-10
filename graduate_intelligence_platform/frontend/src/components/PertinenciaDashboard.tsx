import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts';

const API_URL = import.meta.env.VITE_API_URL ?? '';

const LABEL_COLORS = {
  high: '#16a34a',
  medium: '#d97706',
  low: '#dc2626',
};

const INITIAL_DATA = {
  run_id: null,
  fecha: '—',
  programas: [],
  top_matches: [],
  totales: { matches: 0, alta: 0, media: 0, baja: 0 },
};

export default function PertinenciaDashboard() {
  const [data, setData] = useState(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/dashboard/summary`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <p className="p-6 text-gray-500">Cargando datos…</p>;
  if (error)   return <p className="p-6 text-red-600">Error: {error}</p>;

  const pieData = [
    { name: 'Alta', value: data.totales.alta,  color: LABEL_COLORS.high },
    { name: 'Media', value: data.totales.media, color: LABEL_COLORS.medium },
    { name: 'Baja',  value: data.totales.baja,  color: LABEL_COLORS.low },
  ].filter((d) => d.value > 0);

  const barData = data.programas.map((p) => ({
    nombre: p.nombre.length > 28 ? p.nombre.slice(0, 26) + '…' : p.nombre,
    Alta:   p.labels.high   ?? 0,
    Media:  p.labels.medium ?? 0,
    Baja:   p.labels.low    ?? 0,
    score:  p.score_promedio,
  }));

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-gray-800">
          Pertinencia Académica — Motor de Matching
        </h2>
        <span className="text-sm text-gray-400">
          Run #{data.run_id} · {data.fecha}
        </span>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Matches totales', value: data.totales.matches, color: 'text-gray-700' },
          { label: 'Alta pertinencia', value: data.totales.alta,   color: 'text-green-600' },
          { label: 'Media',           value: data.totales.media,   color: 'text-yellow-600' },
          { label: 'Baja',            value: data.totales.baja,    color: 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border bg-white p-4 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Distribution pie */}
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-medium text-gray-600">Distribución de labels</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name"
                   cx="50%" cy="50%" outerRadius={75} label={({ name, percent }) =>
                     `${name} ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Matches per program bar */}
        <div className="col-span-1 rounded-xl border bg-white p-4 shadow-sm lg:col-span-2">
          <h3 className="mb-2 text-sm font-medium text-gray-600">Matches por programa</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} margin={{ top: 4, right: 8, left: -16, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="nombre" angle={-35} textAnchor="end" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend verticalAlign="top" />
              <Bar dataKey="Alta"  stackId="a" fill={LABEL_COLORS.high} />
              <Bar dataKey="Media" stackId="a" fill={LABEL_COLORS.medium} />
              <Bar dataKey="Baja"  stackId="a" fill={LABEL_COLORS.low} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top matches table */}
      <div className="rounded-xl border bg-white shadow-sm">
        <h3 className="px-4 pt-4 text-sm font-medium text-gray-600">Top matches</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100 text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {['Programa', 'Empleo', 'Empresa', 'Score', 'Label'].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.top_matches.map((m, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-700">{m.programa}</td>
                  <td className="px-4 py-2 text-gray-700">{m.empleo}</td>
                  <td className="px-4 py-2 text-gray-500">{m.empresa}</td>
                  <td className="px-4 py-2 font-mono font-semibold text-gray-800">
                    {m.score.toFixed(1)}
                  </td>
                  <td className="px-4 py-2">
                    <span className="rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{ background: LABEL_COLORS[m.label] + '22',
                                   color: LABEL_COLORS[m.label] }}>
                      {m.label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
