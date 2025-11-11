from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime


def centroid(vectors: Sequence[Sequence[float]]) -> list[float] | None:
    frames = [vec for vec in vectors if vec]
    if not frames:
        return None
    length = len(frames[0])
    acc = [0.0] * length
    count = 0
    for vec in frames:
        if len(vec) != length:
            continue
        for idx, value in enumerate(vec):
            acc[idx] += value
        count += 1
    if count == 0:
        return None
    return [value / count for value in acc]


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    if not first or not second or len(first) != len(second):
        return 0.0
    dot = sum(a * b for a, b in zip(first, second, strict=False))
    norm_a = math.sqrt(sum(a * a for a in first))
    norm_b = math.sqrt(sum(b * b for b in second))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    raw = dot / (norm_a * norm_b)
    return max(-1.0, min(1.0, raw))


def momentum_score(published_at: datetime | None, now: datetime | None = None) -> float:
    now = now or datetime.utcnow()
    if not published_at:
        return 0.1
    age = (now - published_at).days
    if age < 0:
        age = 0
    score = 1 - min(1.0, age / 365)
    return max(0.0, min(1.0, score))
