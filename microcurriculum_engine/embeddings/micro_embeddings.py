from __future__ import annotations

from typing import Any

from ml.embeddings.embedding_service import DEFAULT_EMBEDDING_MODEL, encode_texts


def generate_microcurriculum_embeddings(items: dict[str, str], *, model_name: str = DEFAULT_EMBEDDING_MODEL) -> dict[str, Any]:
    keys = list(items)
    texts = [items[key] for key in keys]
    vectors = encode_texts(texts, model_name=model_name) if texts else []
    return {
        key: {
            "embedding": vectors[index],
            "model_name": model_name,
            "dimensions": len(vectors[index]) if vectors else 0,
        }
        for index, key in enumerate(keys)
    }
