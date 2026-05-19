from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2.extras import Json

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")


def load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. Install requirements/ml.txt before generating embeddings."
        ) from exc
    return SentenceTransformer(model_name)


def embed_texts(texts: list[str], *, model_name: str = DEFAULT_MODEL) -> list[list[float]]:
    model = load_model(model_name)
    prepared = [f"passage: {text}" for text in texts]
    vectors = model.encode(prepared, normalize_embeddings=True, show_progress_bar=True)
    return [vector.astype(float).tolist() for vector in vectors]


def iter_empleos_without_embeddings(limit: int) -> Iterable[tuple[str, str]]:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, concat_ws(' ', titulo, empresa, ciudad, modalidad, descripcion) AS text
                FROM public.empleos
                WHERE embedding IS NULL
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            yield from cur.fetchall()
    finally:
        conn.close()


def update_empleo_embeddings(rows: list[tuple[str, list[float]]]) -> None:
    if not rows:
        return
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )
    try:
        with conn, conn.cursor() as cur:
            for empleo_id, vector in rows:
                cur.execute("UPDATE public.empleos SET embedding = %s WHERE id = %s", (Json(vector), empleo_id))
    finally:
        conn.close()


def embed_file(input_path: Path, output_path: Path, model_name: str) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("rows", [])
    texts = [str(row.get("text") or row.get("descripcion") or row.get("nombre") or "") for row in rows]
    vectors = embed_texts(texts, model_name=model_name)
    for row, vector in zip(rows, vectors):
        row["embedding"] = vector
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate semantic embeddings for jobs, skills or curriculum text.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="SentenceTransformers model name.")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--output-json", default="outputs/embeddings.json")
    args = parser.parse_args()

    if args.input_json:
        embed_file(Path(args.input_json), Path(args.output_json), args.model)
        print(json.dumps({"output": args.output_json}, ensure_ascii=False))
        return 0

    rows = list(iter_empleos_without_embeddings(args.limit))
    vectors = embed_texts([text for _, text in rows], model_name=args.model) if rows else []
    update_empleo_embeddings([(empleo_id, vector) for (empleo_id, _), vector in zip(rows, vectors)])
    print(json.dumps({"updated": len(rows), "model": args.model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
