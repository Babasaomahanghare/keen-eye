"""Actionable environment diagnostics."""

from __future__ import annotations

import importlib.util
import os
import platform
import socket
import sys
import urllib.request
from pathlib import Path

from .config import config_dir, load_config


def run_doctor() -> list[dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str, fix: str = ""):
        checks.append({"name": name, "ok": ok, "detail": detail, "fix": fix})

    add("Python version", sys.version_info >= (3, 10),
        platform.python_version(), "Install Python 3.10 or newer.")
    add("Image processing library", importlib.util.find_spec("PIL") is not None,
        "Pillow available" if importlib.util.find_spec("PIL") else "Pillow missing",
        "Run `pip install -r requirements.txt`.")
    sdk_ok = importlib.util.find_spec("google.genai") is not None
    add("Gemini SDK", sdk_ok, "google-genai available" if sdk_ok else "google-genai missing",
        "Run `pip install -r requirements.txt`.")
    directory = config_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        writable = os.access(directory, os.W_OK)
    except OSError:
        writable = False
    add("Configuration directory", writable, str(directory),
        "Choose a writable home/config directory.")
    cfg = load_config()
    add("API configuration", cfg.configured, "Configured" if cfg.configured else "Not configured",
        "Run `keeneye setup` or export GEMINI_API_KEY.")
    try:
        socket.getaddrinfo("generativelanguage.googleapis.com", 443)
        network_ok = True
    except OSError:
        network_ok = False
    add("Internet connectivity", network_ok, "DNS resolved" if network_ok else "DNS/network unavailable",
        "Check network access and DNS settings.")
    if cfg.configured and sdk_ok and network_ok:
        try:
            from google import genai
            genai.Client(api_key=cfg.api_key).models.list(config={"page_size": 1})
            add("Gemini connectivity", True, "Provider accepted a connectivity check")
        except Exception:
            add("Gemini connectivity", False, "Provider check failed",
                "Check the key, model access, quotas, and network.")
    else:
        add("Gemini connectivity", False, "Skipped until SDK, network, and key are ready",
            "Resolve the earlier checks, then rerun doctor.")
    return checks