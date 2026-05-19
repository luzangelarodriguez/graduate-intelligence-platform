import type { Program } from '../types/api';
import { EmptyState } from './EmptyState';

export function SkillsGap({ program }: { program?: Program }) {
  const skills = program?.skills ?? [];

  if (!program) {
    return <EmptyState title="Selecciona un programa" body="El mapa de skills se actualiza con la especializacion activa." />;
  }

  if (!skills.length) {
    return <EmptyState title="Sin skills normalizadas" body="El repositorio aun no tiene skills asociados para este programa." />;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {skills.slice(0, 18).map((skill) => (
        <span className="skill-chip" key={`${skill.skill_id}-${skill.nombre}`}>
          {skill.nombre}
        </span>
      ))}
    </div>
  );
}
