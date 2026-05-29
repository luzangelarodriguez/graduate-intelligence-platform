# ML Disciplinary Engine Phase 1

## Arquitectura

Se crea una primera capa ML hibrida:

- taxonomia disciplinar existente;
- clasificador supervisado `LogisticRegression`;
- baseline compatible LightGBM con fallback `GradientBoostingClassifier`;
- similitud semantica tipo SentenceTransformer con fallback TF-IDF cosine;
- bloqueo de inferencias con `confidence < 0.65`.

Estructura:

```text
ml/
  training/
  models/
  inference/
  evaluation/
  embeddings/
  datasets/
```

## Dataset inicial

El dataset semilla se genera automaticamente desde:

- `DOMAIN_DEFINITIONS`
- `SKILL_DEFINITIONS`
- terminos y aliases de taxonomia

Salida:

- `ml/datasets/domain_training_seed.csv`

## Modelos

Baselines implementados:

- `logistic_regression`
- `lightgbm_baseline_fallback`
- `tfidf_semantic_similarity`

El entorno actual no tiene `sentence-transformers` ni `lightgbm`; por eso la fase deja compatibilidad y fallback estable. Cuando se instalen, el servicio de embeddings puede usar `all-MiniLM-L6-v2`.

## Persistencia preparada

Tablas agregadas:

- `ml_model_registry`
- `ml_predictions`
- `ml_evaluation_runs`

Tambien se prepara compatibilidad futura con pgvector manteniendo embeddings como lista numerica serializable.

## Pipelines

Entrenar:

```powershell
python ml/train_domain_classifier.py
```

Evaluar:

```powershell
python ml/evaluate_models.py
```

Inferencia:

```powershell
python ml/run_inference.py --title "Analista BI" --description "SQL Power BI Python Big Data" --skills "sql,power bi,python"
```

## API FastAPI

Endpoints nuevos:

- `GET /api/ml/domain-classification`
- `POST /api/ml/inference`

Ambos devuelven:

```json
{
  "domain": "analitica",
  "confidence": 0.82,
  "confidence_level": "high",
  "blocked": false,
  "scores": {}
}
```

Regla de publicacion:

- `confidence < 0.65` => `blocked = true`

## Tests

Se agregaron pruebas en `tests/ml/`:

- ambiental vs TI;
- analitica vs gerencia;
- bloqueo de inferencias invalidas;
- niveles de confianza.

## Riesgos

- Dataset inicial es semilla taxonomica; requiere Gold humano para precision institucional real.
- `sentence-transformers` no esta instalado localmente.
- `lightgbm` no esta instalado localmente.
- Falta persistir predicciones API en DB de forma transaccional cuando se defina politica de auditoria.

## Proximos pasos

1. Instalar `sentence-transformers` y generar embeddings reales `all-MiniLM-L6-v2`.
2. Agregar `pgvector` y columnas vectoriales.
3. Curar dataset Gold con ejemplos reales por dominio.
4. Registrar modelos entrenados en `ml_model_registry`.
5. Promover endpoint ML a pipeline de matching solo despues de pasar QA y release gates.
