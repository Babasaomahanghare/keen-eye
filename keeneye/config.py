"""Local configuration with environment-first API key resolution."""

from __future__ import annotations

import getpass
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError

ENV_KEY = "GEMINI_API_KEY"
DEFAULT_MODEL = "gemini-2.5-flash"


def config_dir() -> Path:
    override = os.environ.get("KEEN_EYE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg).expanduser() if xdg else Path.home() / ".config") / "keeneye"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass(frozen=True)
class KeenEyeConfig:
    api_key: str | None = None
    model: str = DEFAULT_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def read_local_config() -> KeenEyeConfig:
    path = config_path()
    if not path.exists():
        return KeenEyeConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            "The local KEEN EYE configuration could not be read.",
            "The configuration file is missing, unreadable, or invalid JSON.",
            f"Review or remove {path}, then run `keeneye setup` again.",
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigurationError(
            "The local KEEN EYE configuration is invalid.",
            "The configuration root must be a JSON object.",
            f"Run `keeneye setup` to recreate {path}.",
        )
    key = raw.get("api_key")
    model = raw.get("model") or DEFAULT_MODEL
    return KeenEyeConfig(api_key=key if isinstance(key, str) and key else None,
                         model=model if isinstance(model, str) else DEFAULT_MODEL)


def load_config() -> KeenEyeConfig:
    """Resolve environment first, then the local config file."""
    env_key = os.environ.get(ENV_KEY, "").strip()
    local = read_local_config()
    return KeenEyeConfig(api_key=env_key or local.api_key, model=local.model)


def mask_key(key: str | None) -> str:
    if not key:
        return "Not configured"
    if len(key) <= 4:
        return "*" * len(key)
    return "*" * max(8, len(key) - 4) + key[-4:]


def save_config(api_key: str, model: str = DEFAULT_MODEL) -> Path:
    key = api_key.strip()
    if not key:
        raise ConfigurationError(
            "No API key was provided.",
            "The Gemini API key cannot be empty.",
            "Paste a valid key or press Ctrl-C to cancel.",
        )
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, stat.S_IRWXU)
    except OSError:
        pass
    path = config_path()
    path.write_text(json.dumps({"api_key": key, "model": model}, indent=2) + "\n",
                    encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path


def clear_config() -> bool:
    path = config_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def prompt_for_key() -> str:
    try:
        return getpass.getpass("Gemini API key (input hidden): ")
    except (EOFError, KeyboardInterrupt) as exc:
        raise ConfigurationError(
            "API key setup was cancelled.",
            "No key was entered.",
            "Run `keeneye setup` when you are ready.",
        ) from exc