"""Explainable exposure heuristic based only on actual findings."""

from __future__ import annotations


def _items(value) -> list:
    return value if isinstance(value, list) else []


def calculate_score(metadata: dict, ai: dict) -> dict:
    score = 0
    reasons: list[str] = []

    if metadata.get("gps"):
        score += 35
        reasons.append("GPS metadata detected")
    if metadata.get("camera_make") or metadata.get("camera_model"):
        score += 10
        reasons.append("Camera/device metadata detected")
    if metadata.get("datetime"):
        score += 5
        reasons.append("Capture timestamp metadata detected")
    if metadata.get("software"):
        score += 5
        reasons.append("Editing/software metadata detected")

    for key, label, points in (
        ("privacy_exposure", "AI-identified privacy exposure", 8),
        ("visible_text", "Visible text may reveal context", 4),
        ("signage", "Identifiable signage observed", 4),
        ("location_clues", "Location clues observed", 4),
        ("security_relevant_observations", "Security-relevant visual observation", 3),
    ):
        count = len(_items(ai.get(key)))
        if count:
            added = min(points * count, 20 if key == "privacy_exposure" else 12)
            score += added
            reasons.append(f"{label} ({count})")

    score = min(score, 100)
    band = "LOW EXPOSURE" if score < 30 else "MEDIUM EXPOSURE" if score < 65 else "HIGH EXPOSURE"
    return {"score": score, "band": band, "reasons": reasons}