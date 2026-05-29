# Curriculum Semantic Hardening

## Resumen Ejecutivo

Se agrego una capa NER curricular hibrida basada en reglas, EntityRuler opcional y patrones contextuales para recuperar tecnologias implicitas en microcurriculos.

- Baseline comparativo: `embedded_pre_hardening_baseline`.
- Gold dataset semilla: `39` entidades candidatas en `ml\datasets\curriculum_gold_dataset.csv`.
- Documentos escaneados para Gold dataset: `19`.
- Precision antes/despues: `0.8333` -> `1.0`.
- Recall antes/despues: `0.0833` -> `0.6667`.
- Contaminacion disciplinar antes/despues: `0.1667` -> `0.0`.
- Taxonomy coverage antes/despues: `0.375` -> `0.9524`.
- Contextual understanding antes/despues: `0.65` -> `0.9238`.
- Readiness piloto universitario: `medio`.

## Cambios Implementados

- Taxonomia TI ampliada con lenguajes, frameworks, bases de datos, cloud, DevOps, IDEs y herramientas de analitica.
- Dominio `transversal` creado para liderazgo, pensamiento critico y trabajo en equipo.
- NER curricular en `ml/ner/` con separacion de tipos de entidad.
- Inferencia contextual para tecnologias implicitas como desarrollo movil, nube, API, backend, IDE y CI/CD.
- Gold dataset semilla en `ml/datasets/curriculum_gold_dataset.csv` para revision humana posterior.

## Riesgos

- El Gold dataset generado sigue siendo automatico; requiere curaduria humana antes de entrenar un NER supervisado.
- Los PDFs disponibles parecen duplicados por hash, por lo que la validacion mejora recall funcional pero no prueba diversidad disciplinar real.
- La inferencia contextual aumenta recall y debe seguir monitoreandose con muestras ambientales, juridicas y gerenciales para evitar sesgo TI.

## Siguientes Pasos

1. Anotar manualmente 100-300 fragmentos por dominio en el Gold dataset.
2. Entrenar un NER supervisado con spaCy cuando exista volumen validado.
3. Calibrar confidence con falsos positivos por disciplina.
4. Agregar muestras reales no TI para medir contaminacion fuera de Ingenieria de Software.