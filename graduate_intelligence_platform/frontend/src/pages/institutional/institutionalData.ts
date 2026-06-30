import type { ProgramIntelligenceItem } from '../../types/api';

export function pct(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : '0.0%';
}

export function numberLabel(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? new Intl.NumberFormat('es-CO').format(parsed) : '0';
}

export function average(values: number[]) {
  const valid = values.filter((value) => Number.isFinite(value));
  return valid.length ? valid.reduce((total, value) => total + value, 0) / valid.length : 0;
}

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function recordList(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    : [];
}

export function text(value: unknown, fallback = 'No disponible') {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

export function programEvidence(program: ProgramIntelligenceItem) {
  const evidence = asRecord(program.supporting_evidence);
  const microcurriculum = asRecord(evidence.microcurriculum_context);
  const benchmark = asRecord(evidence.domain_benchmark);
  const gaps = recordList(evidence.gaps).length ? recordList(evidence.gaps) : program.top_gaps;
  return { evidence, microcurriculum, benchmark, gaps };
}

export function skillName(row: Record<string, unknown>) {
  return text(row.missing_skill ?? row.skill ?? row.skill_normalized ?? row.canonical_skill ?? row.name, 'Skill no identificada');
}

export function priorityLabel(value: unknown) {
  const score = Number(value);
  if (!Number.isFinite(score)) return 'Media';
  if (score >= 0.7) return 'Alta';
  if (score >= 0.35) return 'Media';
  return 'Baja';
}

export function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes('error') || normalized.includes('ausente') || normalized.includes('missing')) return 'danger';
  if (normalized.includes('parcial') || normalized.includes('partial') || normalized.includes('sin')) return 'warning';
  return 'success';
}
