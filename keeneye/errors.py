"""User-facing error types and safe error formatting."""


class KeenEyeError(Exception):
    """An expected, actionable application error."""

    def __init__(self, what: str, why: str, next_step: str):
        super().__init__(what)
        self.what = what
        self.why = why
        self.next_step = next_step


class ConfigurationError(KeenEyeError):
    pass


class ImageValidationError(KeenEyeError):
    pass


class GeminiError(KeenEyeError):
    pass


def as_user_error(exc: Exception) -> KeenEyeError:
    """Convert an unexpected provider/filesystem exception without secrets."""
    if isinstance(exc, KeenEyeError):
        return exc
    return KeenEyeError(
        "KEEN EYE encountered an unexpected error.",
        "The operation could not be completed safely.",
        "Retry with --debug for local diagnostics, and check `keeneye doctor`.",
    )