"""Gemini provider boundary with strict, defensive response handling."""

from __future__ import annotations

import json
import re
from typing import Any

from .errors import GeminiError

FINDING_KEYS = (
    "summary", "visible_text", "objects", "people_present", "location_clues",
    "landmarks", "signage", "logos_or_brands", "technology_clues",
    "security_relevant_observations", "privacy_exposure", "confidence",
    "limitations",
)

ANALYSIS_PROMPT = """You are KEEN EYE, a defensive image-intelligence assistant.
Analyze only what is visually supported by the supplied image. This is
authorized security research and privacy review, not identification.

Return ONLY valid JSON with exactly these fields:
{
  "summary": "short cautious summary",
  "visible_text": [{"text": "...", "confidence": "high|medium|low"}],
  "objects": [{"observation": "...", "confidence": "high|medium|low"}],
  "people_present": true,
  "location_clues": [{"clue": "...", "confidence": "high|medium|low"}],
  "landmarks": [{"observation": "...", "confidence": "high|medium|low"}],
  "signage": [{"observation": "...", "confidence": "high|medium|low"}],
  "logos_or_brands": [{"observation": "...", "confidence": "high|medium|low"}],
  "technology_clues": [{"observation": "...", "confidence": "high|medium|low"}],
  "security_relevant_observations": [{"observation": "...", "confidence": "high|medium|low"}],
  "privacy_exposure": [{"observation": "...", "confidence": "high|medium|low"}],
  "confidence": {"overall": "high|medium|low"},
  "limitations": ["state uncertainty and what cannot be determined"]
}

Do not identify or guess private people. Do not provide exact GPS coordinates,
addresses, usernames, organizations, or identities unless they are plainly
visible text in the image; even then report the visible text, not an inferred
identity. Use "Unable to determine from the image." when appropriate.
"""


def _json_text(text: str) -> str:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else cleaned


def normalize_response(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise GeminiError(
            "Gemini returned an unusable response.",
            "The provider response was not a JSON object.",
            "Retry the analysis or choose another supported model.",
        )
    result: dict[str, Any] = {key: payload.get(key) for key in FINDING_KEYS}
    result["summary"] = result["summary"] if isinstance(result["summary"], str) else "Unable to determine from the image."
    result["people_present"] = result["people_present"] if isinstance(result["people_present"], bool) else None
    for key in FINDING_KEYS:
        if key in {"summary", "people_present", "confidence"}:
            continue
        if not isinstance(result[key], list):
            result[key] = []
    if not isinstance(result["confidence"], dict):
        result["confidence"] = {"overall": "low"}
    result["limitations"] = result["limitations"] or ["AI-generated observations may be incomplete or incorrect."]
    return result


def parse_response_text(text: str) -> dict:
    try:
        return normalize_response(json.loads(_json_text(text)))
    except (json.JSONDecodeError, TypeError) as exc:
        raise GeminiError(
            "Gemini returned malformed JSON.",
            "The vision response could not be parsed as the required structured report.",
            "Retry the analysis. If it persists, try another model or report the provider response format.",
        ) from exc


class GeminiClient:
    """Small adapter around the official google-genai SDK."""

    def __init__(self, api_key: str, model: str):
        self.model = model
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiError(
                "The Gemini SDK is not installed.",
                "The google-genai package is unavailable in this Python environment.",
                "Run `pip install -r requirements.txt` and retry.",
            ) from exc
        self._types = types
        self._client = genai.Client(api_key=api_key)

    def analyze(self, image_bytes: bytes, mime_type: str) -> dict:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    ANALYSIS_PROMPT,
                    self._types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            text = getattr(response, "text", None)
            if not text:
                raise ValueError("empty response")
            return parse_response_text(text)
        except GeminiError:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "429" in message or "rate" in message or "quota" in message:
                why = "The provider reported a quota or rate-limit condition."
                next_step = "Wait before retrying or review your Gemini usage limits."
            elif "401" in message or "403" in message or "api key" in message or "permission" in message:
                why = "The provider rejected the configured credential or permission."
                next_step = "Check the key, its restrictions, and the selected model, then run `keeneye setup`."
            else:
                why = "The provider request failed or the network was unavailable."
                next_step = "Check connectivity, run `keeneye doctor`, and retry."
            raise GeminiError("Gemini image analysis failed.", why, next_step) from exc