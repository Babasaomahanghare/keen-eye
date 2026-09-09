"""Command-line interface for KEEN EYE."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.prompt import Confirm

from . import __version__
from .analyzer import analyze_image
from .config import DEFAULT_MODEL, clear_config, load_config, mask_key, prompt_for_key, save_config
from .doctor import run_doctor
from .errors import KeenEyeError, as_user_error
from .gemini import GeminiClient
from .reports import build_report, write_html, write_json
from .scoring import calculate_score
from .ui import console, show_banner, show_report, stage


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="keeneye",
        description="Privacy-first AI-powered OSINT image intelligence.",
    )
    root.add_argument("--debug", action="store_true", help="show a traceback for unexpected errors")
    subs = root.add_subparsers(dest="command")
    setup = subs.add_parser("setup", help="save and validate a Gemini API key")
    setup.add_argument("--model", default=DEFAULT_MODEL)
    config = subs.add_parser("config", help="show or clear local configuration")
    config.add_argument("--clear", action="store_true")
    for name in ("image", "analyze"):
        command = subs.add_parser(name, help="analyze an image")
        command.add_argument("path")
        command.add_argument("--json", action="store_true", help="print the machine-readable report")
        command.add_argument("--output", help="write JSON report to this path")
        command.add_argument("--report", help="write a self-contained HTML report to this path")
        command.add_argument("--yes", action="store_true", help="approve sending the image to Gemini")
        command.add_argument("--model", default=None)
    demo = subs.add_parser("demo", help="run the offline demo with clearly labeled demo data")
    demo.add_argument("--output")
    demo.add_argument("--report")
    subs.add_parser("doctor", help="diagnose the local environment")
    subs.add_parser("version", help="print the version")
    subs.add_parser("help", help="show help")
    return root


def _demo_report() -> dict:
    profile = {
        "path": "demo://keen-eye-sample",
        "filename": "keen-eye-demo-image.jpg",
        "format": "JPEG",
        "mime_type": "image/jpeg",
        "size_bytes": 184320,
        "width": 1280,
        "height": 853,
        "sha256": "demo-data-not-a-real-file",
        "md5": "demo-data-not-a-real-file",
    }
    metadata = {"exif_present": True, "camera_make": "Demo Camera",
                "camera_model": "KEEN EYE Sample", "datetime": "DEMO ONLY",
                "software": None, "orientation": 1, "copyright": None,
                "gps": None, "other": {}}
    ai = {
        "summary": "DEMO DATA: a sample street scene contains visible signage and a laptop.",
        "visible_text": [{"text": "DEMO CAFE", "confidence": "high"}],
        "objects": [{"observation": "Laptop computer", "confidence": "high"}],
        "people_present": False,
        "location_clues": [{"clue": "Street signage is visible; exact location is not determined.", "confidence": "low"}],
        "landmarks": [], "signage": [{"observation": "Sample business sign", "confidence": "high"}],
        "logos_or_brands": [], "technology_clues": [{"observation": "Laptop screen is visible.", "confidence": "medium"}],
        "security_relevant_observations": [{"observation": "Screen content should be reviewed before sharing.", "confidence": "medium"}],
        "privacy_exposure": [{"observation": "Visible signage may reveal context.", "confidence": "medium"}],
        "confidence": {"overall": "medium"},
        "limitations": ["DEMO DATA only. This is not an analysis of a real user image."],
    }
    return build_report(profile, metadata, ai, calculate_score(metadata, ai), demo=True)


def _privacy_consent() -> bool:
    console.print("[yellow]Privacy notice:[/yellow] This image will be sent to the configured Gemini API provider for analysis.")
    console.print("KEEN EYE does not receive or store your image.")
    try:
        return Confirm.ask("Continue?", default=False)
    except (EOFError, KeyboardInterrupt):
        return False


def command_setup(args) -> int:
    key = prompt_for_key()
    try:
        client = GeminiClient(key, args.model)
        client._client.models.list(config={"page_size": 1})
    except Exception as exc:
        error = as_user_error(exc)
        if isinstance(error, KeenEyeError) and error.what.startswith("Gemini"):
            console.print(f"[red][!] API key validation failed.[/red]\n{error.why}\n{error.next_step}")
            return 2
        console.print("[yellow][!] Could not validate the key due to a provider or network problem.[/yellow]")
        console.print("The key was not saved. Check connectivity and try again.")
        return 2
    path = save_config(key, args.model)
    console.print("[green]✓ Gemini connection successful.[/green]")
    console.print(f"[green]✓[/green] Key saved securely at {path}")
    return 0


def command_config(args) -> int:
    if args.clear:
        console.print("[green]✓ Local KEEN EYE configuration removed.[/green]" if clear_config()
                      else "[dim]No local configuration found.[/dim]")
        return 0
    cfg = load_config()
    console.print("[bold cyan]Configuration[/bold cyan]")
    console.print("─────────────")
    console.print(f"Gemini API: {'Configured' if cfg.configured else 'Not configured'}")
    console.print(f"API Key: {mask_key(cfg.api_key)}")
    console.print(f"Model: {cfg.model}")
    return 0


def command_doctor() -> int:
    show_banner()
    checks = run_doctor()
    failed = 0
    for check in checks:
        if check["ok"]:
            stage(f"{check['name']}: {check['detail']}")
        else:
            failed += 1
            stage(f"{check['name']}: {check['detail']} — {check['fix']}", ok=False)
    return 1 if failed else 0


def command_demo(args) -> int:
    show_banner()
    console.print("[yellow]DEMO DATA[/yellow] · No image upload and no API key required.")
    report = _demo_report()
    show_report(report)
    if args.output:
        console.print(f"[green]✓ JSON written to {write_json(report, args.output)}[/green]")
    if args.report:
        console.print(f"[green]✓ HTML written to {write_html(report, args.report)}[/green]")
    return 0


def command_image(args) -> int:
    cfg = load_config()
    if args.model:
        cfg = type(cfg)(api_key=cfg.api_key, model=args.model)
    if args.json and not args.yes:
        raise KeenEyeError(
            "Machine-readable JSON mode requires explicit upload approval.",
            "A JSON stream cannot safely contain an interactive privacy prompt.",
            "Review the upload notice and rerun with `--json --yes`.",
        )
    if not args.json:
        show_banner()
    consent = args.yes or _privacy_consent()
    report = analyze_image(args.path, cfg, consent=consent,
                           progress=None if args.json else stage)
    if args.output:
        write_json(report, args.output)
    if args.report:
        write_html(report, args.report)
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    else:
        if args.output:
            console.print(f"[green]✓ JSON written to {args.output}[/green]")
        if args.report:
            console.print(f"[green]✓ HTML written to {args.report}[/green]")
        show_report(report)
    return 0


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    try:
        if args.command is None:
            from .wizard import launch_wizard
            code = launch_wizard()
        elif args.command == "help":
            parser().print_help()
            code = 0
        elif args.command == "version":
            console.print(f"KEEN EYE {__version__}")
            code = 0
        elif args.command == "setup":
            code = command_setup(args)
        elif args.command == "config":
            code = command_config(args)
        elif args.command == "doctor":
            code = command_doctor()
        elif args.command == "demo":
            code = command_demo(args)
        elif args.command in ("image", "analyze"):
            code = command_image(args)
        else:
            parser().print_help()
            code = 0
    except Exception as exc:
        if args.debug:
            raise
        error = as_user_error(exc)
        console.print(f"[red][!] WHAT HAPPENED[/red]\n{error.what}")
        console.print(f"[yellow]WHY[/yellow]\n{error.why}")
        console.print(f"[cyan]WHAT TO DO NEXT[/cyan]\n{error.next_step}")
        code = 2
    raise SystemExit(code)