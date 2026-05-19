import type { Match } from '../types/api';
import { EmptyState } from './EmptyState';

export function MatchCards({ matches }: { matches: Match[] }) {
  if (!matches.length) {
    return <EmptyState title="Sin matches para este programa" body="Selecciona otro programa o espera a que el pipeline ML genere nuevos resultados." />;
  }

  return (
    <div className="space-y-3">
      {matches.slice(0, 5).map((match) => (
        <article className="match-card" key={`${match.empleo_id}-${match.titulo_empleo}`}>
          <div>
            <strong>{match.titulo_empleo}</strong>
            <span>{match.skills_en_comun} skills en comun de {match.total_skills_especializacion}</span>
          </div>
          <div className="match-score">{Number(match.porcentaje_match).toFixed(1)}%</div>
        </article>
      ))}
    </div>
  );
}
