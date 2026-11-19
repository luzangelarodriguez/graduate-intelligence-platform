-- Migration 033: occupational profiles — familias de Marketing y Publicidad
--
-- Adds 10 profiles in 6 families:
--   · Marketing Digital                        (Especialista en Marketing Digital,
--                                               Community Manager,
--                                               Especialista en SEO/SEM)
--   · Marketing Estratégico                    (Brand Manager)
--   · Publicidad y Creatividad                 (Ejecutivo de Cuenta Publicidad,
--                                               Diseñador / Creativo Publicitario)
--   · Investigación y Analítica de Consumidor  (Analista de Investigación de Mercados)
--   · Trade Marketing y Ventas                 (Especialista en Trade Marketing)
--   · Growth y E-commerce                      (Especialista en Growth,
--                                               Especialista en E-commerce)
--
-- Idempotent: ON CONFLICT DO NOTHING on both tables.
-- Does NOT touch existing profiles or patterns from earlier migrations.

-- ── 1. Profiles ───────────────────────────────────────────────────────────────

INSERT INTO public.occupational_profiles (nombre, familia, descripcion) VALUES

    ('Especialista en Marketing Digital',
     'Marketing Digital',
     'Gestiona canales digitales, SEO/SEM, pauta digital y analítica web'),

    ('Community Manager',
     'Marketing Digital',
     'Administra redes sociales, genera contenido y gestiona la comunidad de marca'),

    ('Especialista en SEO/SEM',
     'Marketing Digital',
     'Optimiza posicionamiento orgánico (SEO técnico, on-page) y gestiona campañas de pago (Google Ads, Meta Ads)'),

    ('Brand Manager',
     'Marketing Estratégico',
     'Define y gestiona la identidad de marca, posicionamiento y arquitectura de marca'),

    ('Ejecutivo de Cuenta Publicidad',
     'Publicidad y Creatividad',
     'Gestiona cuentas de clientes en agencias de publicidad y coordina campañas'),

    ('Diseñador / Creativo Publicitario',
     'Publicidad y Creatividad',
     'Desarrolla piezas creativas y conceptos de campaña para medios ATL y BTL'),

    ('Analista de Investigación de Mercados',
     'Investigación y Analítica de Consumidor',
     'Diseña y ejecuta estudios cualitativos y cuantitativos de mercado y consumidor'),

    ('Especialista en Trade Marketing',
     'Trade Marketing y Ventas',
     'Diseña estrategias de visibilidad en punto de venta y gestión de categorías'),

    ('Especialista en Growth',
     'Growth y E-commerce',
     'Diseña experimentos de crecimiento y optimiza funnels de adquisición y retención'),

    ('Especialista en E-commerce',
     'Growth y E-commerce',
     'Gestiona tiendas en línea, UX/CRO, integraciones de pago y logística digital')

ON CONFLICT (nombre) DO NOTHING;

-- ── 2. Patterns — Especialista en Marketing Digital ───────────────────────────
-- Covers Spanish ("marketing", "mercadeo"), English order, and common seniority prefixes.

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%marketing digital%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%mercadeo%digital%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%digital marketing%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%especialista%marketing%', 0.900
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%coordinador%marketing%', 0.890
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%coordinador%mercadeo%', 0.890
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista%marketing%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista%mercadeo%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%marketing analyst%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%campa%as digitales%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%director%marketing%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%director%mercadeo%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%jefe%marketing%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%jefe%mercadeo%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%gerente%marketing%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%gerente%mercadeo%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%aprendiz%mercadeo%', 0.850
FROM public.occupational_profiles WHERE nombre = 'Especialista en Marketing Digital'
ON CONFLICT (patron) DO NOTHING;

-- ── 3. Patterns — Community Manager ──────────────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%community manager%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Community Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%social media%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Community Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%gestor%redes sociales%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Community Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%content creator%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Community Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%creador%contenido%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Community Manager'
ON CONFLICT (patron) DO NOTHING;

-- ── 4. Patterns — Especialista en SEO/SEM ────────────────────────────────────
-- '%seo%' excluded: matches "Aseo". Two boundary patterns used instead.

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '% seo%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, 'seo %', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%pauta digital%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%performance%marketing%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%google ads%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%meta ads%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%paid media%', 0.910
FROM public.occupational_profiles WHERE nombre = 'Especialista en SEO/SEM'
ON CONFLICT (patron) DO NOTHING;

-- ── 5. Patterns — Brand Manager ───────────────────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%brand manager%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Brand Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%gerente%marca%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Brand Manager'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%director%marca%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Brand Manager'
ON CONFLICT (patron) DO NOTHING;

-- ── 6. Patterns — Publicidad ──────────────────────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%ejecutivo%cuenta%publicidad%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Ejecutivo de Cuenta Publicidad'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%ejecutivo%cuenta%agencia%', 0.900
FROM public.occupational_profiles WHERE nombre = 'Ejecutivo de Cuenta Publicidad'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%director creativo%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Diseñador / Creativo Publicitario'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%diseñador%publicidad%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Diseñador / Creativo Publicitario'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%copywriter%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Diseñador / Creativo Publicitario'
ON CONFLICT (patron) DO NOTHING;

-- ── 7. Patterns — Investigación de mercados ───────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%investigaci%n%mercado%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Analista de Investigación de Mercados'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%market research%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Analista de Investigación de Mercados'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista%consumidor%', 0.900
FROM public.occupational_profiles WHERE nombre = 'Analista de Investigación de Mercados'
ON CONFLICT (patron) DO NOTHING;

-- ── 8. Patterns — Trade Marketing ─────────────────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%trade marketing%', 0.970
FROM public.occupational_profiles WHERE nombre = 'Especialista en Trade Marketing'
ON CONFLICT (patron) DO NOTHING;

-- ── 9. Patterns — Growth ──────────────────────────────────────────────────────
-- Space before "growth" avoids theoretical English compound words (outgrowth, etc.)

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '% growth%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Especialista en Growth'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%growth hac%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Especialista en Growth'
ON CONFLICT (patron) DO NOTHING;

-- ── 10. Patterns — E-commerce ─────────────────────────────────────────────────

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%e-commerce%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Especialista en E-commerce'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%ecommerce%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Especialista en E-commerce'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%comercio electr%nico%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Especialista en E-commerce'
ON CONFLICT (patron) DO NOTHING;
