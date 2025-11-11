from __future__ import annotations

import threading

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

from app.config import settings


class EmbeddingService:
    _instance: EmbeddingService | None = None
    _lock = threading.Lock()

    def __init__(self):
        self.dim = settings.embedding_dim
        self._model = (
            SentenceTransformer(settings.embedding_model)
            if SentenceTransformer
            else None
        )

    @classmethod
    def get(cls) -> EmbeddingService:
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = EmbeddingService()
        return cls._instance

    def embed(self, text: str) -> list[float]:
        if not self._model:
            return [0.0] * self.dim
        vec = self._model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vec.tolist()] if hasattr(vec, "tolist") else list(vec)
