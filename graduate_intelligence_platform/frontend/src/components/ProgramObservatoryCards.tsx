import { ChevronRight } from 'lucide-react';

import type { Program } from '../types/api';

interface ProgramObservatoryCardsProps {
  programs: Program[];
  selectedProgramId: number | null;
  onSelectProgram: (programId: number) => void;
  onViewFullRanking?: () => void;
}

function getProgramState(program: Program) {
  const match = Number(program.promedio_match_mercado || 0);
  const jobs = Number(program.total_empleos_relacionados || 0);

  if (match >= 70) return { label: 'Alta', tone: 'high' };
  if (match >= 50) return { label: 'Media', tone: 'medium' };
  if (jobs > 0) return { label: 'Emergente', tone: 'emerging' };
  return { label: 'Baja evidencia', tone: 'quiet' };
}

function getTrend(program: Program) {
  const match = Number(program.promedio_match_mercado || 0);
  const max = Number(program.max_match_mercado || 0);
  const jobs = Number(program.total_empleos_relacionados || 0);

  if (max > match + 8) return 'up';
  if (jobs >= 10) return 'stable';
  if (jobs > 0) return 'emerging';
  return 'quiet';
}

export function ProgramObservatoryCards({
  programs,
  selectedProgramId,
  onSelectProgram,
  onViewFullRanking,
}: ProgramObservatoryCardsProps) {
  if (!programs.length) {
    return null;
  }

  const ranked = programs.slice(0, 5);
  const maxScore = Math.max(...ranked.map((program) => Number(program.promedio_match_mercado || 0)), 1);

  return (
    <>
      <div className="program-leaderboard" role="list">
        {ranked.map((program, index) => {
          const isActive = program.especializacion_id === selectedProgramId;
          const score = Number(program.promedio_match_mercado || 0);
          const width = Math.max(4, (score / maxScore) * 100);
          const state = getProgramState(program);
          const trend = getTrend(program);

          return (
            <button
              type="button"
              className={`program-rank-row ${isActive ? 'active' : ''}`}
              key={program.especializacion_id}
              onClick={() => onSelectProgram(program.especializacion_id)}
              title="Abrir detalle contextual del programa"
            >
              <span className="program-rank-number">{String(index + 1).padStart(2, '0')}</span>
              <div className="program-rank-main">
                <div className="program-rank-title">
                  <strong>{program.nombre_especializacion}</strong>
                  <span className={`program-rank-badge ${state.tone}`}>{state.label}</span>
                </div>
                <div className="program-rank-track" aria-hidden="true">
                  <span style={{ width: `${width}%` }} />
                </div>
              </div>
              <div className="program-rank-meta">
                <strong>{score.toFixed(1)}%</strong>
                <span className={`program-trend-dot ${trend}`} aria-hidden="true" />
              </div>
              <ChevronRight className="program-rank-action" size={15} strokeWidth={1.8} />
            </button>
          );
        })}
      </div>
      <button className="ranking-full-link" type="button" onClick={onViewFullRanking}>
        Ver ranking completo
      </button>
    </>
  );
}
