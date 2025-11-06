from __future__ import annotations
import math
from typing import List, Dict, Tuple
from collections import Counter
import numpy as np


class SimpleTfidfVectorizer:
    """
    Minimal TF-IDF (pure Python + NumPy) to avoid scikit-learn/scipy.
    - Tokenizes on basic whitespace & lowercases.
    - Supports max_features cap.
    - Methods: fit_transform(corpus) -> np.ndarray, transform(texts) -> np.ndarray
    """

    def __init__(self, max_features: int = 20000):
        self.max_features = max_features
        self.vocab_: Dict[str, int] = {}
        self.idf_: np.ndarray | None = None

    def _tokenize(self, s: str) -> List[str]:
        return [t for t in s.lower().split() if t]

    def fit_transform(self, corpus: List[str]) -> np.ndarray:
        # build DF
        df: Counter[str] = Counter()
        tokenized = [self._tokenize(doc) for doc in corpus]
        for toks in tokenized:
            df.update(set(toks))

        # select top features
        most_common = df.most_common(self.max_features)
        self.vocab_ = {tok: i for i, (tok, _) in enumerate(most_common)}

        N = len(corpus)
        idf = np.zeros(len(self.vocab_), dtype=np.float32)
        for tok, idx in self.vocab_.items():
            idf[idx] = math.log((1 + N) / (1 + df[tok])) + 1.0  # smoothed IDF
        self.idf_ = idf

        # build TF-IDF matrix
        X = np.zeros((N, len(self.vocab_)), dtype=np.float32)
        for row, toks in enumerate(tokenized):
            cnt = Counter(toks)
            total = sum(cnt.values()) or 1
            for tok, c in cnt.items():
                idx = self.vocab_.get(tok)
                if idx is None:
                    continue
                tf = c / total
                X[row, idx] = tf * idf[idx]
        return X

    def transform(self, texts: List[str]) -> np.ndarray:
        assert self.vocab_ and self.idf_ is not None, "Call fit_transform first."
        X = np.zeros((len(texts), len(self.vocab_)), dtype=np.float32)
        for row, s in enumerate(texts):
            toks = self._tokenize(s)
            cnt = Counter(toks)
            total = sum(cnt.values()) or 1
            for tok, c in cnt.items():
                idx = self.vocab_.get(tok)
                if idx is None:
                    continue
                tf = c / total
                X[row, idx] = tf * self.idf_[idx]
        return X
