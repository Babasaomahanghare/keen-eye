"""End-to-end analysis orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .config import KeenEyeConfig
from .errors import ConfigurationError, GeminiError
from .gemini import GeminiClient
from .image import validate_image
from .metadata import extract_metadata
from .reports import build_report
from .scoring import calculate_score


def analyze_image(path: str, config: KeenEyeConfig, *, consent: bool,
                  progress: Callable[[str], None] | None = None,
                  client=None) -> dict:
    def say(message: str) -> None:
        if progress:
            progress(message)

    profile = validate_image(path)
    say("File validated")
    metadata = extract_metadata(profile.path)
    say("Metadata extracted")
    if not config.api_key:
        raise ConfigurationError(
            "AI engine is not configured.",
            "No GEMINI_API_KEY or local KEEN EYE key was found.",
            "Run `keeneye setup` or export GEMINI_API_KEY, then retry.",
        )
    if not consent:
        raise ConfigurationError(
            "Image upload was not approved.",
            "This image would be sent to the configured Gemini API provider.",
            "Review the privacy notice and rerun with approval or `--yes`.",
        )
    say("Image prepared")
    if client is None:
        client = GeminiClient(config.api_key, config.model)
    try:
        image_bytes = Path(profile.path).read_bytes()
        say("Sending image to AI engine")
        ai = client.analyze(image_bytes, profile.mime_type)
    except GeminiError:
        raise
    except OSError as exc:
        raise GeminiError(
            "The image could not be read for analysis.",
            "The file became unavailable after validation.",
            "Check permissions and that the file was not moved, then retry.",
        ) from exc
    say("AI visual analysis complete")
    score = calculate_score(metadata, ai)
    say("Exposure evaluated")
    return build_report(profile.to_dict(), metadata, ai, score)