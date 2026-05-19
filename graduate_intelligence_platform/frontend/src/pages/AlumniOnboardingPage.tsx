import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { getProgramRecommendations, getProgramas, registerAlumni } from '../services/api';
import type { AlumniRegistrationPayload, Program, RecommendationProgram } from '../types/api';

const initialForm: AlumniRegistrationPayload = {
  nombre_completo: '',
  email: '',
  especializacion_id: 0,
  anio_graduacion: '',
  cargo_actual: '',
  area_actual: 'Datos',
  nivel_experiencia: '2-3',
  anios_experiencia: '',
  skills_actuales: '',
  herramientas_dia_dia: '',
  roles_interes: '',
  areas_interes: '',
  objetivo_laboral: 'Cambiar de rol',
  disponibilidad: 'Abierto a oportunidades',
};

const steps = ['Perfil', 'Experiencia', 'Skills', 'Objetivos', 'Recomendaciones'];

export function AlumniOnboardingPage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [form, setForm] = useState<AlumniRegistrationPayload>(initialForm);
  const [step, setStep] = useState(0);
  const [recommendations, setRecommendations] = useState<RecommendationProgram[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const page = await getProgramas(100);
        setPrograms(page.items);
        setForm((current) => ({ ...current, especializacion_id: page.items[0]?.especializacion_id ?? 0 }));
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'No fue posible cargar programas.');
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (!form.especializacion_id) return;
    getProgramRecommendations(form.especializacion_id, 3)
      .then((page) => setRecommendations(page.items))
      .catch(() => setRecommendations([]));
  }, [form.especializacion_id]);

  const canSubmit = useMemo(
    () => Boolean(form.nombre_completo.trim() && form.email.trim() && form.especializacion_id),
    [form],
  );

  function update(field: keyof AlumniRegistrationPayload, value: string | number) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setIsSubmitting(true);
    setStatus(null);
    setError(null);
    try {
      const result = await registerAlumni(form);
      setStatus(`Perfil creado correctamente. ID #${result.id}`);
      setStep(4);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo registrar el perfil.');
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <LoadingState label="Preparando onboarding alumni..." />;
  if (error && !programs.length) return <EmptyState title="No se pudo abrir registro" body={error} />;

  return (
    <form className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]" onSubmit={onSubmit}>
      <aside className="panel h-fit">
        <h2 className="text-xl font900">Onboarding alumni</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Registro moderno multi-step conectado a `POST /api/alumni/register`.
        </p>
        <div className="mt-6 space-y-2">
          {steps.map((item, index) => (
            <button
              className={index === step ? 'step-button active' : 'step-button'}
              key={item}
              type="button"
              onClick={() => setStep(index)}
            >
              <span>{index + 1}</span>
              {item}
            </button>
          ))}
        </div>
      </aside>

      <section className="panel">
        {status && <div className="notice success">{status}</div>}
        {error && <div className="notice error">{error}</div>}

        {step === 0 && (
          <div className="form-grid">
            <Field label="Nombre completo">
              <input value={form.nombre_completo} onChange={(event) => update('nombre_completo', event.target.value)} />
            </Field>
            <Field label="Email">
              <input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} />
            </Field>
            <Field label="Programa de egreso">
              <select value={form.especializacion_id} onChange={(event) => update('especializacion_id', Number(event.target.value))}>
                {programs.map((program) => (
                  <option key={program.especializacion_id} value={program.especializacion_id}>
                    {program.nombre_especializacion}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Año graduacion">
              <input value={form.anio_graduacion} onChange={(event) => update('anio_graduacion', event.target.value)} />
            </Field>
          </div>
        )}

        {step === 1 && (
          <div className="form-grid">
            <Field label="Cargo actual">
              <input value={form.cargo_actual} onChange={(event) => update('cargo_actual', event.target.value)} />
            </Field>
            <Field label="Area actual">
              <select value={form.area_actual} onChange={(event) => update('area_actual', event.target.value)}>
                <option>Datos</option>
                <option>Tecnologia</option>
                <option>Negocios</option>
                <option>Operaciones</option>
              </select>
            </Field>
            <Field label="Nivel experiencia">
              <select value={form.nivel_experiencia} onChange={(event) => update('nivel_experiencia', event.target.value)}>
                <option>0-1</option>
                <option>2-3</option>
                <option>4-5</option>
                <option>6-8</option>
                <option>9-12</option>
                <option>13+</option>
              </select>
            </Field>
            <Field label="Años experiencia">
              <input value={form.anios_experiencia} onChange={(event) => update('anios_experiencia', event.target.value)} />
            </Field>
          </div>
        )}

        {step === 2 && (
          <div className="form-grid">
            <Field label="Skills actuales">
              <textarea value={form.skills_actuales} onChange={(event) => update('skills_actuales', event.target.value)} />
            </Field>
            <Field label="Herramientas dia a dia">
              <textarea value={form.herramientas_dia_dia} onChange={(event) => update('herramientas_dia_dia', event.target.value)} />
            </Field>
          </div>
        )}

        {step === 3 && (
          <div className="form-grid">
            <Field label="Roles de interes">
              <textarea value={form.roles_interes} onChange={(event) => update('roles_interes', event.target.value)} />
            </Field>
            <Field label="Areas de interes">
              <textarea value={form.areas_interes} onChange={(event) => update('areas_interes', event.target.value)} />
            </Field>
            <Field label="Objetivo laboral">
              <select value={form.objetivo_laboral} onChange={(event) => update('objetivo_laboral', event.target.value)}>
                <option>Encontrar empleo</option>
                <option>Cambiar de rol</option>
                <option>Crecer en mi empresa</option>
                <option>Explorar posgrado</option>
              </select>
            </Field>
            <Field label="Disponibilidad">
              <select value={form.disponibilidad} onChange={(event) => update('disponibilidad', event.target.value)}>
                <option>Activamente buscando empleo</option>
                <option>Abierto a oportunidades</option>
                <option>Solo explorando</option>
              </select>
            </Field>
          </div>
        )}

        {step === 4 && (
          <div>
            <h3 className="text-lg font900">Recomendaciones iniciales</h3>
            <div className="mt-4 grid gap-3">
              {recommendations.map((item) => (
                <article className="recommendation-card" key={item.nombre}>
                  <span>{item.match.toFixed(1)}% match mercado</span>
                  <strong>{item.nombre}</strong>
                  <p>{item.reason}</p>
                </article>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 flex flex-wrap justify-between gap-3">
          <button className="btn-secondary" type="button" disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))}>
            Anterior
          </button>
          {step < 4 ? (
            <button className="btn-primary" type="button" onClick={() => setStep((current) => Math.min(4, current + 1))}>
              Siguiente
            </button>
          ) : (
            <button className="btn-primary" type="submit" disabled={!canSubmit || isSubmitting}>
              {isSubmitting ? 'Registrando...' : 'Crear perfil'}
            </button>
          )}
        </div>
      </section>
    </form>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
