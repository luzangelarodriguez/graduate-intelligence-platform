import type { RecommendationProgram } from '../types/api';
import { EmptyState } from './EmptyState';

export function RecommendationCards({ items }: { items: RecommendationProgram[] }) {
  if (!items.length) {
    return <EmptyState title="Sin recomendaciones suficientes" body="La API no encontro programas complementarios con evidencia fuerte." />;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <article className="recommendation-card" key={`${item.nombre}-${item.reason}`}>
          <span>{Number(item.match).toFixed(1)}% match mercado</span>
          <strong>{item.nombre}</strong>
          <p>{item.reason}</p>
        </article>
      ))}
    </div>
  );
}
