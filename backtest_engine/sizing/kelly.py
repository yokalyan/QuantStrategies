from __future__ import annotations


def bounded_kelly_weights(
    scores: dict[str, float],
    fraction: float,
    max_position_weight: float,
    max_gross_exposure: float,
) -> dict[str, float]:
    positive = {k: v for k, v in scores.items() if v > 0}
    total = sum(positive.values())
    if total <= 0:
        return {}
    raw = {k: (v / total) * fraction for k, v in positive.items()}
    capped = {k: min(v, max_position_weight) for k, v in raw.items()}
    gross = sum(abs(v) for v in capped.values())
    if gross > max_gross_exposure and gross > 0:
        scale = max_gross_exposure / gross
        capped = {k: v * scale for k, v in capped.items()}
    return capped

