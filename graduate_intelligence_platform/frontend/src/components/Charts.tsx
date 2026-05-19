import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { Match, Program } from '../types/api';

export function AlignmentChart({ programs }: { programs: Program[] }) {
  const data = programs.slice(0, 8).map((program) => ({
    name: program.nombre_especializacion.replace('Especialización en ', ''),
    match: Number(program.promedio_match_mercado || 0),
    jobs: Number(program.total_empleos_relacionados || 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
        <CartesianGrid stroke="#e7edf3" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#5d6b7a' }} tickLine={false} axisLine={false} interval={0} height={70} />
        <YAxis tick={{ fontSize: 10, fill: '#5d6b7a' }} tickLine={false} axisLine={false} />
        <Tooltip cursor={{ fill: '#f4f7fa' }} />
        <Bar dataKey="match" fill="#005da8" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MatchTrendChart({ matches }: { matches: Match[] }) {
  const data = matches.slice(0, 12).map((match, index) => ({
    index: index + 1,
    match: Number(match.porcentaje_match || 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={205}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
        <CartesianGrid stroke="#e7edf3" vertical={false} />
        <XAxis dataKey="index" tick={{ fontSize: 10, fill: '#5d6b7a' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#5d6b7a' }} tickLine={false} axisLine={false} />
        <Tooltip />
        <Line type="monotone" dataKey="match" stroke="#005da8" strokeWidth={2.2} dot={{ r: 2, fill: '#0b2438' }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
