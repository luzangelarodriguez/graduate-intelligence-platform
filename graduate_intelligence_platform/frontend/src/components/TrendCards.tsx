import type { Program } from '../types/api';

export function TrendCards({ programs }: { programs: Program[] }) {
  const highAlignment = programs.filter((program) => Number(program.promedio_match_mercado) >= 60).length;
  const activePrograms = programs.filter((program) => Number(program.total_empleos_relacionados) > 0).length;
  const best = [...programs].sort((a, b) => b.max_match_mercado - a.max_match_mercado)[0];

  return (
    <section className="grid gap-4 md:grid-cols-3">
      <article className="metric-strip">
        <span>Alineacion fuerte</span>
        <strong>{highAlignment}</strong>
        <p>programas con senal superior al 60%</p>
      </article>
      <article className="metric-strip">
        <span>Cobertura laboral</span>
        <strong>{activePrograms}</strong>
        <p>programas con matches laborales activos</p>
      </article>
      <article className="metric-strip">
        <span>Mejor senal</span>
        <strong>{best ? `${best.max_match_mercado.toFixed(1)}%` : '0%'}</strong>
        <p>{best?.nombre_especializacion ?? 'Sin datos suficientes'}</p>
      </article>
    </section>
  );
}
