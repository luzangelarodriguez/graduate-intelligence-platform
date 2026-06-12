import { useEffect, useMemo, useState } from 'react';

import {
  getProgramMarketAlignment,
  getProgramMatches,
  getProgramRecommendedJobs,
  getProgramSkillGaps,
  getProgramas,
  getPrograma,
} from '../services/api';
import type {
  Program,
} from '../types/api';

type GenericRecord = Record<string, unknown>;

interface ProgramSelectorItem {
  especializacion_id: number;
  nombre_especializacion: string;
  rol: string;
  total_empleos_relacionados?: number;
  promedio_match_mercado?: number;
}

interface CanonicalProgramPayload {
  program: Program | null;
  alignment: GenericRecord | null;
  recommended_jobs: GenericRecord[];
  skill_gaps: GenericRecord[];
  matches: GenericRecord[];
}

function firstText(item: GenericRecord, keys: string[], fallback = '') {
  for (const key of keys) {
    const value = item[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return String(value);
    }
  }
  return fallback;
}

function firstNumber(item: GenericRecord | null, keys: string[], fallback = 0) {
  if (!item) return fallback;
  for (const key of keys) {
    const value = item[key];
    const parsed = Number(value);
    if (value !== undefined && value !== null && Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function metricCard(label: string, value: number | string, hint?: string) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
      {hint ? <p className="mt-1 text-sm text-slate-500">{hint}</p> : null}
    </article>
  );
}

function listBlock(
  title: string,
  items: GenericRecord[],
  primaryKeys: string[],
  secondaryKeys: string[] = [],
) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <span className="text-xs text-slate-500">{items.length} items</span>
      </div>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">Sin datos para este programa.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.slice(0, 12).map((item, index) => {
            const primary = firstText(item, primaryKeys, `item-${index + 1}`);
            const secondary = firstText(item, secondaryKeys);
            return (
              <li key={`${primary}-${index}`} className="rounded-md bg-slate-50 px-3 py-2">
                <p className="text-sm font-medium text-slate-900">{primary}</p>
                {secondary ? <p className="text-xs text-slate-500">{secondary}</p> : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function DashboardV1SimplePage() {
  const [programs, setPrograms] = useState<ProgramSelectorItem[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [selectedPayload, setSelectedPayload] = useState<CanonicalProgramPayload>({
    program: null,
    alignment: null,
    recommended_jobs: [],
    skill_gaps: [],
    matches: [],
  });
  const [loadingPrograms, setLoadingPrograms] = useState(true);
  const [loadingProgram, setLoadingProgram] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let mounted = true;
    setLoadingPrograms(true);
    setError('');
    getProgramas(100)
      .then((page) => {
        if (!mounted) return;
        const rows = (page.items ?? []).map((program) => ({
          especializacion_id: program.especializacion_id,
          nombre_especializacion: program.nombre_especializacion,
          rol: program.rol,
          total_empleos_relacionados: program.total_empleos_relacionados,
          promedio_match_mercado: program.promedio_match_mercado,
        }));
        setPrograms(rows);
        setSelectedProgramId((current) => current ?? (rows[0]?.especializacion_id ?? null));
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'No se pudieron cargar los programas.');
      })
      .finally(() => {
        if (!mounted) return;
        setLoadingPrograms(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedProgramId) {
      setSelectedPayload({
        program: null,
        alignment: null,
        recommended_jobs: [],
        skill_gaps: [],
        matches: [],
      });
      return;
    }

    let mounted = true;
    setLoadingProgram(true);
    setError('');

    console.log('SELECTED PROGRAM ID', selectedProgramId);

    Promise.allSettled([
      getPrograma(selectedProgramId),
      getProgramMarketAlignment(selectedProgramId),
      getProgramRecommendedJobs(selectedProgramId),
      getProgramSkillGaps(selectedProgramId),
      getProgramMatches(selectedProgramId, 25),
    ])
      .then(([programResult, alignmentResult, recommendationsResult, gapsResult, matchesResult]) => {
        if (!mounted) return;

        const program = programResult.status === 'fulfilled' ? programResult.value : null;
        const alignment = alignmentResult.status === 'fulfilled' ? (alignmentResult.value as unknown as GenericRecord) : null;
        const recommendationsPayload = recommendationsResult.status === 'fulfilled' ? recommendationsResult.value : null;
        const gapsPayload = gapsResult.status === 'fulfilled' ? gapsResult.value : null;
        const matchesPayload = matchesResult.status === 'fulfilled' ? matchesResult.value : null;

        console.log('FETCH /api/programas/{id}', {
          url: `/api/programas/${selectedProgramId}`,
          status: programResult.status === 'fulfilled' ? 200 : 'error',
          payload: program,
        });
        console.log('FETCH /api/programas/{id}/market-alignment', {
          url: `/api/programas/${selectedProgramId}/market-alignment`,
          status: alignmentResult.status === 'fulfilled' ? 200 : 'error',
          payload: alignment,
        });
        console.log('FETCH /api/programas/{id}/recommended-jobs', {
          url: `/api/programas/${selectedProgramId}/recommended-jobs`,
          status: recommendationsResult.status === 'fulfilled' ? 200 : 'error',
          payload: recommendationsPayload,
        });
        console.log('FETCH /api/programas/{id}/skill-gaps', {
          url: `/api/programas/${selectedProgramId}/skill-gaps`,
          status: gapsResult.status === 'fulfilled' ? 200 : 'error',
          payload: gapsPayload,
        });
        console.log('FETCH /api/matches/programa/{id}', {
          url: `/api/matches/programa/${selectedProgramId}`,
          status: matchesResult.status === 'fulfilled' ? 200 : 'error',
          payload: matchesPayload,
        });

        const recommendedJobs = Array.isArray(recommendationsPayload?.recommended_jobs)
          ? (recommendationsPayload?.recommended_jobs as unknown[]).map((item) => item as GenericRecord)
          : [];

        const missingSkills = Array.isArray(gapsPayload?.missing_skills)
          ? (gapsPayload?.missing_skills as string[]).map((skill) => ({ skill, source: 'missing_skills' }))
          : [];

        const taughtNotDemanded = Array.isArray(gapsPayload?.taught_not_demanded)
          ? (gapsPayload?.taught_not_demanded as string[]).map((skill) => ({ skill, source: 'taught_not_demanded' }))
          : [];

        const skillGaps = [...missingSkills, ...taughtNotDemanded];
        const matches = Array.isArray(matchesPayload?.items)
          ? (matchesPayload.items as unknown[]).map((item) => item as GenericRecord)
          : [];

        console.log('REACT ASSIGNED', {
          alignment,
          coverage: selectedCoverageScore,
          gap: selectedGapScore,
          matches,
          recommendedJobs,
          skillGaps,
        });

        setSelectedPayload({
          program,
          alignment,
          recommended_jobs: recommendedJobs,
          skill_gaps: skillGaps,
          matches,
        });
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'No se pudo cargar el programa seleccionado.');
      })
      .finally(() => {
        if (!mounted) return;
        setLoadingProgram(false);
      });

    return () => {
      mounted = false;
    };
  }, [selectedProgramId]);

  const selectedProgram = selectedPayload.program;
  const selectedAlignment = selectedPayload.alignment;
  const recommendedJobs = useMemo(() => selectedPayload.recommended_jobs ?? [], [selectedPayload.recommended_jobs]);
  const skillGaps = useMemo(() => selectedPayload.skill_gaps ?? [], [selectedPayload.skill_gaps]);
  const matches = useMemo(() => selectedPayload.matches ?? [], [selectedPayload.matches]);

  const selectedAlignmentScore = firstNumber(selectedAlignment, ['market_alignment_score', 'alignment_score']);
  const selectedCoverageScore = firstNumber(selectedAlignment, ['coverage_score', 'current_alignment', 'coverage']);
  const selectedGapScore = firstNumber(selectedAlignment, ['gap_score']);
  const selectedMatchedJobs = firstNumber(selectedAlignment, ['matched_jobs'], matches.length);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 p-6">
      <header className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Dashboard V1 Simple</p>
        <h1 className="text-3xl font-semibold text-slate-900">Pertinencia académica con datos canónicos</h1>
        <p className="text-sm text-slate-600">
          Esta vista consume directamente los endpoints reales del programa y evita la lógica heredada del dashboard anterior.
        </p>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Selector de programas</h2>
            <p className="text-sm text-slate-500">
              {loadingPrograms ? 'Cargando programas...' : `${programs.length} programas disponibles`}
            </p>
          </div>
          <select
            className="min-w-[320px] rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm"
            value={selectedProgramId ?? ''}
            onChange={(event) => setSelectedProgramId(Number(event.target.value))}
            disabled={loadingPrograms || programs.length === 0}
          >
            <option value="" disabled>
              Selecciona un programa
            </option>
            {programs.map((program) => (
              <option key={program.especializacion_id} value={program.especializacion_id}>
                {program.nombre_especializacion} - {program.rol}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error ? (
        <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</section>
      ) : null}

      <section className="grid gap-4 md:grid-cols-4">
        {metricCard('Programas', programs.length, 'Selector real de programa')}
        {metricCard('Alignment', selectedAlignmentScore.toFixed(2), 'Score de pertinencia')}
        {metricCard('Coverage', selectedCoverageScore.toFixed(2), 'Cobertura curricular')}
        {metricCard('Matches', selectedMatchedJobs, 'Empleos relacionados')}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Programa seleccionado</h2>
          {!selectedProgram ? (
            <p className="mt-3 text-sm text-slate-500">{loadingProgram ? 'Cargando programa...' : 'Sin programa seleccionado.'}</p>
          ) : (
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p><span className="font-medium text-slate-900">ID:</span> {selectedProgram.especializacion_id}</p>
              <p><span className="font-medium text-slate-900">Nombre:</span> {selectedProgram.nombre_especializacion}</p>
              <p><span className="font-medium text-slate-900">Rol:</span> {selectedProgram.rol}</p>
              <p><span className="font-medium text-slate-900">Gap score:</span> {selectedGapScore.toFixed(2)}</p>
              <p><span className="font-medium text-slate-900">Total skills:</span> {selectedProgram.total_skills_programa}</p>
              <p>
                <span className="font-medium text-slate-900">Fuente:</span>{' '}
                {selectedProgram.microcurriculum_context ? 'canonical program detail' : 'program list'}
              </p>
            </div>
          )}
        </article>

        <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Resumen canónico</h2>
          {!selectedProgram ? (
            <p className="mt-3 text-sm text-slate-500">Seleccione un programa para ver el detalle.</p>
          ) : (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {metricCard('Alignment', selectedAlignmentScore.toFixed(2))}
              {metricCard('Coverage', selectedCoverageScore.toFixed(2))}
              {metricCard('Gap', selectedGapScore.toFixed(2))}
              {metricCard('Matches', selectedMatchedJobs)}
            </div>
          )}
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {listBlock('Recomendaciones', recommendedJobs, ['job_title', 'titulo_empleo', 'title', 'nombre'], ['company', 'empresa', 'match_score', 'similarity_score'])}
        {listBlock('Skill gaps', skillGaps, ['skill', 'missing_skill', 'skill_name'], ['gap_frequency', 'source'])}
        {listBlock('Matches', matches, ['titulo_empleo', 'job_title', 'title', 'nombre'], ['porcentaje_match', 'match_score', 'skills_en_comun'])}
      </section>
    </div>
  );
}
