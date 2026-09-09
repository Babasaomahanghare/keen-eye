"""Terminal presentation kept separate from application logic."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

BANNER = r"""[bold cyan]
╭────────────────────────────────────────────────────╮
│                                                    │
│   ██╗  ██╗███████╗███████╗███╗   ██╗              │
│   ██║ ██╔╝██╔════╝██╔════╝████╗  ██║              │
│   █████╔╝ █████╗  █████╗  ██╔██╗ ██║              │
│   ██╔═██╗ ██╔══╝  ██╔══╝  ██║╚██╗██║              │
│   ██║  ██╗███████╗███████╗██║ ╚████║              │
│   ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝              │
│                                                    │
│             IMAGE INTELLIGENCE ENGINE              │
╰────────────────────────────────────────────────────╯[/bold cyan]"""


def show_banner() -> None:
    console.print(BANNER)
    console.print("[dim]Defensive OSINT analysis for images you are authorized to process.[/dim]\n")


def stage(message: str, ok: bool = True) -> None:
    icon = "[green]✓[/green]" if ok else "[yellow]![/yellow]"
    console.print(f"{icon} {message}")


def show_report(report: dict) -> None:
    profile = report["local_file_intelligence"]["profile"]
    metadata = report["local_file_intelligence"]["metadata"]
    ai = report["ai_visual_intelligence"]
    score = report["exposure_score"]
    console.print()
    console.print(Panel.fit("[bold cyan]KEEN EYE INTELLIGENCE REPORT[/bold cyan]",
                            border_style="cyan"))
    table = Table(title="TARGET", show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    for label, value in (
        ("File", profile.get("filename")),
        ("Format", profile.get("format")),
        ("Size", f"{profile.get('size_bytes', 0) / 1024:.1f} KB"),
        ("Dimensions", f"{profile.get('width')} × {profile.get('height')}"),
        ("SHA-256", profile.get("sha256")),
    ):
        table.add_row(label, str(value))
    console.print(table)
    band_style = "green" if score["score"] < 30 else "yellow" if score["score"] < 65 else "red"
    console.print(Panel(f"[bold {band_style}]{score['score']} / 100 · {score['band']}[/bold {band_style}]\n"
                        + ("\n".join(f"• {r}" for r in score["reasons"]) or "No exposure indicators detected."),
                        title="KEEN EYE EXPOSURE SCORE", border_style=band_style))
    meta = Table(title="LOCAL FILE INTELLIGENCE · METADATA", box=None)
    meta.add_column("Field", style="dim")
    meta.add_column("Value")
    for label, value in (
        ("GPS", "Detected" if metadata.get("gps") else "Not present"),
        ("Camera", " ".join(filter(None, [metadata.get("camera_make"), metadata.get("camera_model")])) or "Not present"),
        ("Timestamp", metadata.get("datetime") or "Not present"),
        ("Software", metadata.get("software") or "Not present"),
    ):
        meta.add_row(label, str(value))
    console.print(meta)
    console.print(Panel(ai.get("summary", "Unable to determine from the image."),
                        title="AI VISUAL INTELLIGENCE", border_style="blue"))
    for title, key in (
        ("VISIBLE TEXT", "visible_text"), ("LOCATION CLUES", "location_clues"),
        ("TECHNOLOGY CLUES", "technology_clues"), ("PRIVACY EXPOSURE", "privacy_exposure"),
        ("SECURITY OBSERVATIONS", "security_relevant_observations"),
    ):
        values = ai.get(key) or []
        if not values:
            continue
        body = "\n".join(
            f"• {item.get('text') or item.get('observation') or item.get('clue') or item}"
            f" [dim]({str(item.get('confidence', '')).upper()})[/dim]"
            if isinstance(item, dict) else f"• {item}" for item in values
        )
        console.print(Panel(body, title=title, border_style="cyan"))
    limitations = ai.get("limitations") or []
    console.print(Panel("\n".join(f"• {item}" for item in limitations),
                        title="LIMITATIONS", border_style="dim"))