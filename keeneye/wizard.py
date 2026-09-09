"""Interactive numbered terminal experience for first-time and repeat users."""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from .analyzer import analyze_image
from .config import load_config
from .doctor import run_doctor
from .errors import KeenEyeError
from .image import validate_image
from .metadata import extract_metadata
from .reports import build_report, write_html, write_json
from .scoring import calculate_score
from .ui import console, show_banner, show_report, stage


def _pause() -> None:
    Prompt.ask("\n[dim]Press Enter to return to the previous menu[/dim]", default="")


def _empty_ai(summary: str, limitation: str) -> dict:
    return {
        "summary": summary,
        "visible_text": [],
        "objects": [],
        "people_present": None,
        "location_clues": [],
        "landmarks": [],
        "signage": [],
        "logos_or_brands": [],
        "technology_clues": [],
        "security_relevant_observations": [],
        "privacy_exposure": [],
        "confidence": {"overall": "not assessed"},
        "limitations": [limitation],
    }


def _local_report(path: str, scope: str) -> dict:
    profile = validate_image(path)
    stage("File validated")
    metadata = extract_metadata(profile.path)
    stage("Local metadata extracted")
    if scope == "exif":
        summary = "Local EXIF metadata was inspected. No image was uploaded."
        limitation = "Only local EXIF/file metadata was examined."
    elif scope == "geo":
        summary = "Local GPS metadata was inspected. No image was uploaded."
        limitation = "Only local GPS metadata was examined; absence of GPS does not prove a location is unknown."
    else:
        summary = "Local EXIF and GPS metadata were inspected. No image was uploaded."
        limitation = "Only local metadata was examined; visual content was not sent to an AI provider."
    ai = _empty_ai(summary, limitation)
    report = build_report(profile.to_dict(), metadata, ai,
                          calculate_score(metadata, ai))
    report["analysis_scope"] = scope
    return report


def _export_report(report: dict) -> None:
    choice = Prompt.ask(
        "\nExport report? [1] JSON  [2] HTML  [3] Both  [00] Skip",
        choices=["1", "2", "3", "00"],
        default="00",
    )
    if choice == "00":
        return
    if choice in ("1", "3"):
        path = Prompt.ask("JSON output path", default="keeneye-report.json")
        console.print(f"[green]✓ JSON written to {write_json(report, path)}[/green]")
    if choice in ("2", "3"):
        path = Prompt.ask("HTML output path", default="keeneye-report.html")
        console.print(f"[green]✓ HTML written to {write_html(report, path)}[/green]")


def _analyze_menu() -> None:
    path = Prompt.ask("\nImage path [dim](type 00 to go back)[/dim]")
    if path.strip() == "00":
        return
    while True:
        console.print(
            "\n[bold cyan]ANALYSIS MODE[/bold cyan]\n"
            "[1] EXIF data only       Local camera, timestamp, software, and file metadata\n"
            "[2] Geo location         Local GPS metadata and location exposure\n"
            "[3] EXIF + geo           Complete local metadata review\n"
            "[4] Full AI intelligence EXIF + geo + Gemini visual analysis\n"
            "[00] Back"
        )
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "00"], default="3")
        if choice == "00":
            return
        try:
            if choice == "4":
                config = load_config()
                if not config.api_key:
                    raise KeenEyeError(
                        "AI engine is not configured.",
                        "Full AI intelligence needs your Gemini API key.",
                        "Run `keeneye setup`, then return to this menu.",
                    )
                console.print(
                    "\n[yellow]Privacy notice:[/yellow] the image will be sent to your configured "
                    "Gemini API provider for visual analysis."
                )
                if not Confirm.ask("Continue?", default=False):
                    console.print("[dim]Upload cancelled. No image was sent.[/dim]")
                    continue
                report = analyze_image(path, config, consent=True, progress=stage)
            else:
                report = _local_report(path, {"1": "exif", "2": "geo", "3": "both"}[choice])
            show_report(report)
            _export_report(report)
            _pause()
            return
        except Exception as exc:
            if isinstance(exc, KeenEyeError):
                console.print(f"\n[red][!] {exc.what}[/red]\n{exc.why}\n{exc.next_step}")
            else:
                console.print("\n[red][!] The analysis could not be completed safely.[/red]")
                console.print("Check the image path and run `keeneye doctor` for diagnostics.")
            _pause()
            return


def _config_menu() -> None:
    while True:
        config = load_config()
        console.print(
            "\n[bold cyan]CONFIGURATION[/bold cyan]\n"
            f"Gemini API: {'[green]Configured[/green]' if config.configured else '[yellow]Not configured[/yellow]'}\n"
            "[1] Run Gemini setup\n"
            "[2] Show safe configuration status\n"
            "[00] Back"
        )
        choice = Prompt.ask("Select an option", choices=["1", "2", "00"], default="2")
        if choice == "00":
            return
        if choice == "1":
            console.print("Run this command to validate and save your key securely:")
            console.print("[cyan]keeneye setup[/cyan]")
            _pause()
        else:
            console.print(f"API key: {'Configured' if config.configured else 'Not configured'}")
            console.print(f"Model: {config.model}")
            _pause()


def _doctor_menu() -> None:
    console.print("\n[bold cyan]SYSTEM DOCTOR[/bold cyan]")
    failed = 0
    for check in run_doctor():
        if check["ok"]:
            stage(f"{check['name']}: {check['detail']}")
        else:
            failed += 1
            stage(f"{check['name']}: {check['detail']} — {check['fix']}", ok=False)
    if failed:
        console.print("\n[yellow]Some checks need attention. Local EXIF/geo analysis may still work.[/yellow]")
    _pause()


def _about() -> None:
    console.print(
        "\n[bold cyan]ABOUT KEEN EYE[/bold cyan]\n"
        "AI-powered OSINT image intelligence for authorized security research.\n\n"
        "KEEN EYE separates local file intelligence from AI visual intelligence.\n"
        "It does not perform facial recognition, private-person identification,\n"
        "credential theft, exploitation, or unauthorized surveillance.\n\n"
        "Created by [bold]Devansh & Soham M[/bold]"
    )
    _pause()


def launch_wizard() -> int:
    show_banner()
    console.print(
        "[bold]Welcome to KEEN EYE.[/bold] Choose a numbered action below.\n"
        "[dim]Enter 00 at any menu to go back. Paths may contain spaces.[/dim]"
    )
    while True:
        console.print(
            "\n[bold cyan]MAIN MENU[/bold cyan]\n"
            "[1] Analyze an image\n"
            "[2] Run offline demo\n"
            "[3] Configuration\n"
            "[4] System doctor\n"
            "[5] About KEEN EYE\n"
            "[00] Exit"
        )
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "00"], default="1")
        if choice == "00":
            console.print("[cyan]Goodbye. KEEN EYE is ready when you are.[/cyan]")
            return 0
        if choice == "1":
            _analyze_menu()
        elif choice == "2":
            from .cli import command_demo
            command_demo(type("DemoArgs", (), {"output": None, "report": None})())
            _pause()
        elif choice == "3":
            _config_menu()
        elif choice == "4":
            _doctor_menu()
        elif choice == "5":
            _about()