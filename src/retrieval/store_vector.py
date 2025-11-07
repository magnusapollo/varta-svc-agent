from __future__ import annotations

import numpy as np


class InMemoryVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.ids: list[str] = []
        self.vecs: np.ndarray | None = None

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        assert vectors.shape[1] == self.dim
        self.ids.extend(ids)
        if self.vecs is None:
            self.vecs = vectors.astype(np.float32)
        else:
            self.vecs = np.vstack([self.vecs, vectors.astype(np.float32)])

    def search(self, q: np.ndarray, k: int) -> list[tuple[str, float]]:
        if self.vecs is None or len(self.ids) == 0:
            return []
        q = q.astype(np.float32)
        sims = (self.vecs @ q) / (
            np.linalg.norm(self.vecs, axis=1) * (np.linalg.norm(q) + 1e-8) + 1e-8
        )
        idx = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in idx]
