import hashlib
import math
from typing import Protocol

import httpx

from research_agent.config import Settings


class Embedder(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(text, self.dim) for text in texts]


class GeminiEmbedder:
    def __init__(self, settings: Settings) -> None:
        self.dim = settings.embedding_dim
        self._key = settings.resolved_google_api_key() or ""
        self._model = "gemini-embedding-001"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._key:
            return await HashEmbedder(self.dim).embed(texts)
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for text in texts:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent",
                    params={"key": self._key},
                    json={"content": {"parts": [{"text": text}]}},
                )
                response.raise_for_status()
                values = response.json()["embedding"]["values"]
                vectors.append(_fit(values, self.dim))
        return vectors


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "gemini":
        return GeminiEmbedder(settings)
    return HashEmbedder(settings.embedding_dim)


def _hash_vector(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    raw = [(digest[i % len(digest)] / 255.0) * 2 - 1 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]


def _fit(values: list[float], dim: int) -> list[float]:
    sliced = values[:dim] if len(values) >= dim else values + [0.0] * (dim - len(values))
    norm = math.sqrt(sum(v * v for v in sliced)) or 1.0
    return [v / norm for v in sliced]
