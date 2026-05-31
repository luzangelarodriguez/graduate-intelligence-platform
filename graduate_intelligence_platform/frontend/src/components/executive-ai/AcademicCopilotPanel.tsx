import { useMemo, useState } from 'react';
import {
  ArrowRight,
  Bot,
  Building2,
  Lightbulb,
  LineChart,
  SendHorizontal,
  Sparkles,
  Target,
  TriangleAlert,
} from 'lucide-react';

import type { AskObservatoryResponse } from '../../types/api';

export interface AcademicCopilotBriefingProgramContext {
  name?: string;
  alignment?: string;
  risk?: string;
  gaps?: string[];
  recommendations?: string[];
  forecast?: string[];
  simulation?: string[];
  note?: string;
}

export interface AcademicCopilotBriefing {
  diagnosis: string;
  priorityPrograms: string[];
  criticalGaps: string[];
  recommendedActions: string[];
  expectedImpact: string[];
  evidence: string[];
  programContext?: AcademicCopilotBriefingProgramContext | null;
  model?: string;
  fallbackNote?: string;
}

interface AcademicCopilotPanelProps {
  title?: string;
  subtitle?: string;
  briefing?: AcademicCopilotBriefing | null;
  briefingLoading?: boolean;
  loading?: boolean;
  error?: string | null;
  answer?: AskObservatoryResponse | null;
  onAsk: (question: string) => Promise<AskObservatoryResponse | null>;
  suggestedQuestions?: string[];
}

function SectionList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <article className="rounded-xl border border-line bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="rounded-lg bg-brand/10 p-2 text-brand">
          <Sparkles size={16} strokeWidth={2} />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-ink">{title}</h4>
          <p className="text-xs text-muted">Hallazgos generados con datos reales del observatorio.</p>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        {items.length ? (
          items.slice(0, 5).map((item) => (
            <div key={`${title}-${item}`} className="flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-ink">
              <ArrowRight size={14} className="mt-0.5 shrink-0 text-brand" strokeWidth={2} />
              <span className="leading-6">{item}</span>
            </div>
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-line bg-slate-50 px-3 py-3 text-sm text-muted">{emptyText}</div>
        )}
      </div>
    </article>
  );
}

function formatFallbackNotice(model?: string, error?: string | null, fallbackNote?: string) {
  if (fallbackNote?.trim()) return fallbackNote.trim();
  if (model === 'deterministic-fallback') {
    return 'Análisis generado con narrativa determinística. Configure OpenAI para explicación avanzada.';
  }
  if (error) {
    return 'Análisis generado con narrativa determinística. Configure OpenAI para explicación avanzada.';
  }
  return null;
}

export function AcademicCopilotPanel({
  title = 'Análisis ejecutivo generado por IA',
  subtitle = 'Síntesis automática sobre pertinencia académica, brechas curriculares y señales de mercado.',
  briefing = null,
  briefingLoading = false,
  loading = false,
  error = null,
  answer = null,
  onAsk,
  suggestedQuestions = [],
}: AcademicCopilotPanelProps) {
  const [question, setQuestion] = useState(suggestedQuestions[0] || '');
  const [submitting, setSubmitting] = useState(false);
  const quickQuestions = useMemo(() => suggestedQuestions.slice(0, 4), [suggestedQuestions]);
  const fallbackNotice = formatFallbackNotice(briefing?.model, error, briefing?.fallbackNote);

  async function submitQuestion(value?: string) {
    const query = (value ?? question).trim();
    if (!query || submitting) return;
    setQuestion(query);
    setSubmitting(true);
    try {
      await onAsk(query);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <Bot size={14} strokeWidth={2} />
            Copiloto académico
          </div>
          <h3 className="mt-2 text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>
        </div>
        <span className="rounded-full border border-brand/15 bg-brand/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          Briefing automático
        </span>
      </div>

      {fallbackNotice ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-7 text-amber-900">
          {fallbackNotice}
        </div>
      ) : null}

      {briefingLoading ? (
        <div className="rounded-xl border border-line bg-slate-50 p-4 text-sm text-muted">
          Generando análisis ejecutivo con datos del observatorio...
        </div>
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <article className="rounded-xl border border-line bg-slate-50 p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
                <Building2 size={14} strokeWidth={2} />
                Diagnóstico institucional
              </div>
              <p className="mt-3 text-sm leading-7 text-ink">
                {briefing?.diagnosis?.trim() || 'No hay un briefing consolidado aún. La plataforma sigue mostrando las señales reales del observatorio y puede profundizarse con una consulta guiada.'}
              </p>
              {briefing?.programContext?.name ? (
                <div className="mt-4 rounded-xl border border-line bg-white p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-sm text-ink">{briefing.programContext.name}</strong>
                    {briefing.programContext.alignment ? (
                      <span className="rounded-full bg-brand/10 px-2.5 py-1 text-xs font-semibold text-brand">
                        Alineación {briefing.programContext.alignment}
                      </span>
                    ) : null}
                    {briefing.programContext.risk ? (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">
                        Riesgo {briefing.programContext.risk}
                      </span>
                    ) : null}
                  </div>
                  {briefing.programContext.note ? (
                    <p className="mt-2 text-sm leading-6 text-muted">{briefing.programContext.note}</p>
                  ) : null}
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg bg-slate-50 p-3">
                      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted">Brechas</div>
                      <div className="mt-2 space-y-1 text-sm text-ink">
                        {(briefing.programContext.gaps || []).slice(0, 3).map((gap) => (
                          <div key={gap} className="rounded-md bg-white px-2 py-1">
                            {gap}
                          </div>
                        ))}
                        {!(briefing.programContext.gaps || []).length ? <div className="text-muted">No hay brechas tipificadas.</div> : null}
                      </div>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted">Recomendaciones</div>
                      <div className="mt-2 space-y-1 text-sm text-ink">
                        {(briefing.programContext.recommendations || []).slice(0, 3).map((item) => (
                          <div key={item} className="rounded-md bg-white px-2 py-1">
                            {item}
                          </div>
                        ))}
                        {!(briefing.programContext.recommendations || []).length ? <div className="text-muted">Sin recomendaciones priorizadas.</div> : null}
                      </div>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted">Forecast / simulación</div>
                      <div className="mt-2 space-y-1 text-sm text-ink">
                        {(briefing.programContext.forecast || []).slice(0, 2).map((item) => (
                          <div key={item} className="rounded-md bg-white px-2 py-1">
                            {item}
                          </div>
                        ))}
                        {(briefing.programContext.simulation || []).slice(0, 2).map((item) => (
                          <div key={item} className="rounded-md bg-white px-2 py-1">
                            {item}
                          </div>
                        ))}
                        {!((briefing.programContext.forecast || []).length || (briefing.programContext.simulation || []).length) ? (
                          <div className="text-muted">Simulación pendiente de datos suficientes.</div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </article>

            <article className="rounded-xl border border-line bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
                <Target size={14} strokeWidth={2} />
                Programas prioritarios
              </div>
              <div className="mt-4 space-y-2">
                {briefing?.priorityPrograms?.length ? (
                  briefing.priorityPrograms.slice(0, 5).map((item) => (
                    <div key={item} className="rounded-lg border border-line bg-slate-50 px-3 py-2 text-sm leading-6 text-ink">
                      {item}
                    </div>
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-line bg-slate-50 px-3 py-3 text-sm text-muted">
                    No hay programas priorizados con la evidencia actual.
                  </div>
                )}
              </div>
            </article>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <SectionList
              title="Brechas críticas"
              items={briefing?.criticalGaps || []}
              emptyText="No hay brechas críticas tipificadas con la evidencia actual."
            />
            <SectionList
              title="Acciones recomendadas"
              items={briefing?.recommendedActions || []}
              emptyText="No hay acciones priorizadas con la evidencia actual."
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
            <SectionList
              title="Impacto esperado"
              items={briefing?.expectedImpact || []}
              emptyText="Simulación pendiente de cálculo predictivo."
            />
            <SectionList
              title="Evidencia utilizada"
              items={briefing?.evidence || []}
              emptyText="Sin evidencia consolidada disponible todavía."
            />
          </div>
        </>
      )}

      <div className="rounded-xl border border-line bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          <Lightbulb size={14} strokeWidth={2} />
          Preguntar al observatorio
        </div>
        <p className="mt-2 text-sm leading-6 text-muted">
          El briefing ejecutivo ya está visible. Usa estas preguntas para profundizar en un hallazgo o solicitar una explicación adicional.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {quickQuestions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => void submitQuestion(item)}
              className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-medium text-muted transition hover:border-brand/40 hover:bg-brand/5"
            >
              <Sparkles size={12} className="mr-1 inline-block" />
              {item}
            </button>
          ))}
        </div>

        <form
          className="mt-4 flex flex-col gap-3 lg:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            void submitQuestion();
          }}
        >
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            className="min-h-[96px] flex-1 rounded-lg border border-line bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
            placeholder="Pregunta al observatorio sobre el programa, brechas, skills o impacto esperado."
          />
          <button
            type="submit"
            disabled={loading || submitting}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-60 lg:self-start"
          >
            <SendHorizontal size={16} strokeWidth={2} />
            {submitting || loading ? 'Consultando...' : 'Preguntar'}
          </button>
        </form>

        {answer ? (
          <div className="mt-4 space-y-3 rounded-lg border border-line bg-slate-50 p-4">
            <p className="text-sm leading-7 text-ink">{answer.answer}</p>
            <div className="flex flex-wrap gap-2">
              {answer.evidence_sources.slice(0, 6).map((source) => (
                <span key={source} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-muted">
                  {source}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold text-muted">
              <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-3 py-1">
                <LineChart size={12} strokeWidth={2} />
                Confianza {answer.confidence.toFixed(2)}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-3 py-1">
                <TriangleAlert size={12} strokeWidth={2} />
                {answer.model === 'deterministic-fallback' ? 'Narrativa determinística' : 'OpenAI explicativo'}
              </span>
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-dashed border-line bg-slate-50 px-4 py-3 text-sm text-muted">
            Haz una pregunta para ampliar alguno de los hallazgos del briefing ejecutivo.
          </div>
        )}
      </div>
    </section>
  );
}
