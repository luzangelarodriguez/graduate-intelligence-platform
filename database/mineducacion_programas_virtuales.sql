CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS public.mineducacion_programas_virtuales (
    id SERIAL PRIMARY KEY,
    nombre_ies TEXT,
    codigo_ies TEXT,
    ies_padre TEXT,
    registro_unico TEXT,
    codigo_snies_programa TEXT NOT NULL,
    nombre_programa TEXT NOT NULL,
    estado_programa TEXT,
    nivel_academico TEXT,
    modalidad TEXT,
    reconocimiento_ministerio TEXT,
    municipio TEXT,
    departamento TEXT,
    metodologia TEXT,
    area_conocimiento TEXT,
    nucleo_basico_conocimiento TEXT,
    creditos INTEGER,
    duracion TEXT,
    periodicidad_admision TEXT,
    fecha_registro DATE,
    fecha_vencimiento DATE,
    url_detalle TEXT,
    raw_html TEXT,
    timestamp_extraccion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fuente TEXT NOT NULL DEFAULT 'HECAA - Ministerio de Educación Nacional',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mineducacion_programas_virtuales_snies UNIQUE (codigo_snies_programa)
);

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_modalidad
    ON public.mineducacion_programas_virtuales (modalidad);

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_estado
    ON public.mineducacion_programas_virtuales (estado_programa);

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_ies
    ON public.mineducacion_programas_virtuales (codigo_ies);

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_departamento
    ON public.mineducacion_programas_virtuales (departamento);

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_nombre_programa
    ON public.mineducacion_programas_virtuales (lower(nombre_programa));

CREATE INDEX IF NOT EXISTS idx_mineducacion_programas_virtuales_nombre_programa_trgm
    ON public.mineducacion_programas_virtuales
    USING gin (lower(nombre_programa) gin_trgm_ops);
