"""Ollama embedding wrapper, shared by ingest and query.

Both corpus.py and vector.py import embed() from here. That sharing is the point:
it is what structurally prevents building the index with one model and querying it
with another, which produces no error -- just silently wrong rankings.
"""

import httpx
import numpy as np

from . import config


class EmbeddingError(RuntimeError):
    pass


def embed(texts: list[str], *, batch_size: int = config.EMBED_BATCH) -> list[list[float]]:
    """Embed texts with the configured model, returning L2-normalized vectors.

    Normalization is done here rather than trusted from the model: BGE-M3's
    reference implementation returns unit vectors, but nothing guarantees Ollama's
    quantized serving preserves that. Normalizing explicitly is what keeps cosine
    distances -- and therefore the relevance floor -- stable across re-indexes.

    No instruction prefix is added. BGE-M3 is trained without one, unlike E5
    ("query: " / "passage: ") and bge-*-en-v1.5. Queries and passages are encoded
    identically.
    """
    if not texts:
        return []

    out: list[list[float]] = []
    with httpx.Client(timeout=600.0) as client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            try:
                resp = client.post(
                    f"{config.OLLAMA_HOST}/api/embed",
                    json={"model": config.EMBED_MODEL, "input": batch},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise EmbeddingError(
                    f"Ollama embed call failed against {config.OLLAMA_HOST}. "
                    f"Is the daemon running and '{config.EMBED_MODEL}' pulled? ({exc})"
                ) from exc

            vectors = resp.json().get("embeddings")
            if not vectors or len(vectors) != len(batch):
                raise EmbeddingError(
                    f"Expected {len(batch)} embeddings, got "
                    f"{0 if not vectors else len(vectors)}"
                )

            arr = np.asarray(vectors, dtype=np.float32)
            if arr.shape[1] != config.EMBED_DIM:
                raise EmbeddingError(
                    f"Model returned dim {arr.shape[1]}, config expects "
                    f"{config.EMBED_DIM}. Update EMBED_DIM or the model."
                )
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            out.extend((arr / norms).tolist())

    return out


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
