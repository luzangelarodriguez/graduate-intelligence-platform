from __future__ import annotations

import importlib.util
from functools import lru_cache
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def sentence_transformers_available() -> bool:
    return importlib.util.find_spec("sentence_transformers") is not None


@lru_cache(maxsize=2)
def load_sentence_transformer(model_name: str = DEFAULT_EMBEDDING_MODEL):
    if not sentence_transformers_available():
        return None
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception:
        return None


def encode_texts(texts: Iterable[str], *, model_name: str = DEFAULT_EMBEDDING_MODEL) -> list[list[float]]:
    items = [str(text or "") for text in texts]
    model = load_sentence_transformer(model_name)
    if model is not None:
        vectors = model.encode(items, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(items).toarray()
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (matrix / norms).tolist()


def semantic_similarity_matrix(left: list[str], right: list[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform([*left, *right])
    return cosine_similarity(matrix[: len(left)], matrix[len(left) :])
