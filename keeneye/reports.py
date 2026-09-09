"""Machine-readable JSON and self-contained HTML report generation."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path


def build_report(profile: dict, metadata: dict, ai: dict, score: dict,
                 *, demo: bool = False) -> dict:
    return {
        "product": "KEEN EYE",
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_data": demo,
        "local_file_intelligence": {
            "profile": profile,
            "metadata": metadata,
        },
        "ai_visual_intelligence": ai,
        "exposure_score": score,
        "disclaimer": (
            "AI-generated observations may be incomplete or incorrect. "
            "Verify important findings independently."
        ),
    }


def write_json(report: dict, path: str | Path) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def _list(items: list) -> str:
    if not items:
        return "<p class='muted'>None reported.</p>"
    rows = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("observation") or item.get("clue") or json.dumps(item)
            confidence = item.get("confidence", "")
            suffix = f" <span class='confidence'>{html.escape(str(confidence).upper())}</span>" if confidence else ""
            rows.append(f"<li>{html.escape(str(text))}{suffix}</li>")
        else:
            rows.append(f"<li>{html.escape(str(item))}</li>")
    return "<ul>" + "".join(rows) + "</ul>"


def render_html(report: dict) -> str:
    profile = report["local_file_intelligence"]["profile"]
    metadata = report["local_file_intelligence"]["metadata"]
    ai = report["ai_visual_intelligence"]
    score = report["exposure_score"]
    demo = " · DEMO DATA" if report.get("demo_data") else ""
    gps = metadata.get("gps")
    meta_rows = [
        ("Format", profile.get("format")),
        ("MIME", profile.get("mime_type")),
        ("Dimensions", f"{profile.get('width')} × {profile.get('height')}"),
        ("Size", f"{profile.get('size_bytes', 0) / 1024:.1f} KB"),
        ("SHA-256", profile.get("sha256")),
        ("Camera", " ".join(filter(None, [metadata.get("camera_make"), metadata.get("camera_model")])) or "Not present"),
        ("Timestamp", metadata.get("datetime") or "Not present"),
        ("GPS", "Detected" if gps else "Not present"),
    ]
    rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in meta_rows)
    sections = [
        ("Visible text", _list(ai.get("visible_text", []))),
        ("Objects", _list(ai.get("objects", []))),
        ("Location clues", _list(ai.get("location_clues", []))),
        ("Technology clues", _list(ai.get("technology_clues", []))),
        ("Privacy exposure", _list(ai.get("privacy_exposure", []))),
        ("Security observations", _list(ai.get("security_relevant_observations", []))),
        ("Limitations", _list(ai.get("limitations", []))),
    ]
    cards = "".join(f"<section><h2>{html.escape(title)}</h2>{body}</section>" for title, body in sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KEEN EYE · {html.escape(profile.get('filename', 'report'))}</title>
<style>
:root {{ color-scheme: dark; --bg:#071018; --panel:#0e1b26; --line:#203849; --text:#e7f1f5; --muted:#8ba5b2; --cyan:#62d9dc; --amber:#f4bf6b; --red:#ff7f7f; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:radial-gradient(circle at 80% 0,#123848 0,#071018 42%); color:var(--text); font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:42px 22px 70px }} .eyebrow {{ color:var(--cyan); letter-spacing:.16em; font-size:12px; font-weight:700 }}
h1 {{ margin:8px 0 4px; font-size:clamp(30px,5vw,54px); letter-spacing:-.04em }} h2 {{ font-size:18px; margin-top:0 }}
.subtitle,.muted {{ color:var(--muted) }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; margin-top:24px }}
section,.hero,.score {{ background:rgba(14,27,38,.88); border:1px solid var(--line); border-radius:16px; padding:22px; box-shadow:0 12px 40px #0002 }}
.score {{ display:flex; align-items:center; gap:24px; margin:22px 0; border-color:#315c6a }} .number {{ font-size:48px; font-weight:800; color:var(--cyan); line-height:1 }} .band {{ color:var(--amber); font-weight:700; letter-spacing:.08em }}
table {{ width:100%; border-collapse:collapse }} th,td {{ border-bottom:1px solid var(--line); padding:9px 0; text-align:left; vertical-align:top }} th {{ color:var(--muted); font-weight:500; width:30% }} td {{ overflow-wrap:anywhere }}
ul {{ padding-left:20px }} li {{ margin:7px 0 }} .confidence {{ color:var(--cyan); font-size:11px; font-weight:700; margin-left:5px }} footer {{ color:var(--muted); margin-top:32px; font-size:13px }}
</style></head><body><main>
<div class="hero"><div class="eyebrow">KEEN EYE · IMAGE INTELLIGENCE{html.escape(demo)}</div>
<h1>Intelligence report</h1><div class="subtitle">{html.escape(profile.get('filename', 'Unknown image'))}</div>
<p>{html.escape(ai.get('summary', 'No summary available.'))}</p></div>
<div class="score"><div class="number">{score.get('score', 0)}<small>/100</small></div><div><div class="band">{html.escape(score.get('band', 'UNKNOWN'))}</div><div class="muted">Explainable exposure heuristic</div><div>{_list(score.get('reasons', []))}</div></div></div>
<section><h2>Local file intelligence</h2><table>{rows}</table></section>
<div class="grid">{cards}</div>
<footer>{html.escape(report.get('disclaimer', ''))}<br><br>Created by Devansh &amp; Soham M · KEEN EYE</footer>
</main></body></html>"""


def write_html(report: dict, path: str | Path) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(report), encoding="utf-8")
    return target