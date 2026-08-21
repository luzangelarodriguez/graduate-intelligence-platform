-- Limpieza de datos hardcodeados insertados por register_project_management_program.py
-- que NO siguen el pipeline estándar (microcurriculos → microcurriculo_skills).
--
-- La tabla microcurriculo_asignaturas no tiene columna especializacion_id,
-- por lo que las filas huérfanas (si las hay) no afectan al matching estándar.
-- Sin embargo, las entradas en microcurriculo_skills con microcurriculo_id=NULL
-- o apuntando a rows inexistentes en microcurriculos sí pueden generar ruido.
--
-- Ejecutar con: psql $RAILWAY_DATABASE_URL -f scripts/cleanup_pm_dirty_data.sql
-- O pegar en Railway → Query.

BEGIN;

-- 1. Eliminar skills huérfanas (microcurriculo_id no existe en microcurriculos)
DELETE FROM microcurriculo_skills
WHERE microcurriculo_id NOT IN (SELECT id FROM microcurriculos);

-- 2. Eliminar asignaturas en microcurriculo_asignaturas sin microcurriculo_id válido
DELETE FROM microcurriculo_asignaturas
WHERE microcurriculo_id NOT IN (SELECT id FROM microcurriculos);

-- 3. Eliminar rows en microcurriculos para specialization_id=9
--    solo si existen (el pipeline estándar aún no ha cargado nada para este programa)
DELETE FROM microcurriculo_skills
WHERE microcurriculo_id IN (
    SELECT id FROM microcurriculos WHERE specialization_id = 9
);
DELETE FROM microcurriculos WHERE specialization_id = 9;

-- 4. Verificación
SELECT 'microcurriculos con spec_id=9' AS check, COUNT(*) FROM microcurriculos WHERE specialization_id = 9
UNION ALL
SELECT 'orphan skills', COUNT(*) FROM microcurriculo_skills
WHERE microcurriculo_id NOT IN (SELECT id FROM microcurriculos)
UNION ALL
SELECT 'orphan asignaturas', COUNT(*) FROM microcurriculo_asignaturas
WHERE microcurriculo_id NOT IN (SELECT id FROM microcurriculos);

COMMIT;
