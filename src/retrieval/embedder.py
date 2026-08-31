from __future__ import annotations

import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[a-zA-Z0-9_/-]+")


class HashingEmbedder:
    def embed(self, text: str) -> dict[str, float]:
        tokens = tokenize(text)
        counts = Counter(tokens)
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {key: value / norm for key, value in counts.items()}

    def embed_dense(self, text: str, dimensions: int = 512) -> list[float]:
        sparse = self.embed(text)
        vector = [0.0] * dimensions
        for token, value in sparse.items():
            vector[hash(token) % dimensions] += value
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]
