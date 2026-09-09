# KEEN EYE

## AI-powered OSINT image intelligence for security research

KEEN EYE is a privacy-first Python CLI for analyzing images that you are
authorized to process. It combines local file intelligence (hashes, image
properties, and EXIF metadata) with optional Gemini vision analysis, then
produces an explainable exposure score and exportable JSON or HTML reports.

It is designed to run as an ordinary user on Kali Linux, Termux, and standard
Python installations. It does not run shell commands, collect telemetry, or
send images anywhere except the Gemini API that you explicitly configure and
approve.

> **Responsible use:** Use KEEN EYE only for authorized security research,
> defensive analysis, investigations involving publicly available information,
> and images you are authorized to process. It does not perform facial
> recognition, private-person identification, credential theft, exploitation,
> or unauthorized surveillance.

## Features

- `keeneye image` and `keeneye analyze` commands with paths containing spaces
- Local validation before any network request
- SHA-256/MD5 hashes, MIME type, dimensions, file size, and EXIF extraction
- Optional Gemini vision analysis with strict JSON normalization
- Clear separation between **local file intelligence** and **AI visual intelligence**
- Explainable **KEEN EYE Exposure Score** (a heuristic, not a validated standard)
- Privacy confirmation before an image is sent to Gemini
- JSON output for automation and self-contained HTML reports for demos
- `keeneye demo` for a harmless, offline presentation
- `keeneye doctor` for troubleshooting
- No server, account, telemetry, or hidden tracking
- Tests that mock the AI layer and never need a real API key

## Requirements

- Python 3.10 or newer
- Pillow
- Rich
- Google Gen AI SDK only when AI analysis is needed

The exact installable dependencies are in [`requirements.txt`](requirements.txt).

## Installation

### Kali Linux / Linux

```bash
git clone https://github.com/YOUR-USERNAME/keen-eye.git
cd keen-eye
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
keeneye doctor
```

KEEN EYE does not require root privileges.

### Termux

```bash
pkg update
pkg install python
git clone https://github.com/YOUR-USERNAME/keen-eye.git
cd keen-eye
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
keeneye doctor
```

If you are working with shared Android storage, grant access once with
`termux-setup-storage`, then use paths such as
`~/storage/shared/DCIM/photo.jpg`.

## Gemini configuration

KEEN EYE uses your own Gemini API key directly from your machine. The key is
never sent to a KEEN EYE server, printed in full, or committed to Git.

Option 1, environment variable:

```bash
export GEMINI_API_KEY="your-key"
```

Option 2, secure local setup:

```bash
keeneye setup
```

The setup command stores the key at `~/.config/keeneye/config.json` (or the
platform's equivalent XDG config directory) with restrictive permissions.
`GEMINI_API_KEY` takes precedence over the local file.

KEEN EYE does not embed a provider URL. Obtain a key from the official Google
AI Studio interface or your organization's approved Gemini provider
documentation, then provide it locally.

Useful configuration commands:

```bash
keeneye config
keeneye config --clear
```

The `config` command shows only a masked suffix of the key.

## Usage

Show the first-run banner and analyze an image:

```bash
keeneye image ./photo.jpg
```

The command validates the file, extracts local metadata, asks for privacy
approval, sends the image to the configured Gemini API, and renders the
report. Use `--yes` only when you have already reviewed the upload notice.

```bash
keeneye image "/home/user/My Photos/evidence.jpg" --yes
keeneye analyze ./evidence.webp --model gemini-2.5-flash --yes
```

Export machine-readable JSON or a polished HTML report:

```bash
keeneye image ./photo.jpg --json --yes
keeneye image ./photo.jpg --output report.json --yes
keeneye image ./photo.jpg --report report.html --yes
keeneye image ./photo.jpg --output report.json --report report.html --yes
```

The JSON report contains the local profile, metadata, AI findings, limitations,
and score. HTML output is self-contained and contains no remote assets.

Run the offline demonstration without an API key:

```bash
keeneye demo
keeneye demo --report demo-report.html
keeneye demo --output demo-report.json
```

Demo findings are clearly labeled **DEMO DATA** and must not be treated as
real intelligence.

## Commands

| Command | Purpose |
| --- | --- |
| `keeneye setup` | Securely save and validate a Gemini API key |
| `keeneye image PATH` | Analyze a user-provided image |
| `keeneye analyze PATH` | Alias for `image` |
| `keeneye config` | Show safe configuration status |
| `keeneye doctor` | Check Python, dependencies, permissions, and connectivity |
| `keeneye demo` | Run an offline, clearly labeled demo |
| `keeneye version` | Print version |
| `keeneye help` | Show command help |

## Architecture

```text
CLI
 ├── config.py       local key/config management
 ├── image.py        validation, hashing, dimensions
 ├── metadata.py     EXIF and GPS extraction
 ├── gemini.py       provider boundary and response validation
 ├── analyzer.py     orchestration and privacy gate
 ├── scoring.py      explainable heuristic score
 ├── reports.py      JSON and self-contained HTML
 ├── ui.py           terminal presentation
 └── doctor.py       diagnostics
```

The provider boundary is deliberately small. Tests can replace the Gemini
client with a fake implementation, and future providers can be added without
changing local processing or report generation.

## Privacy and security model

- An image is never uploaded silently. Interactive analysis asks for approval.
- `--yes` is explicit and intended for scripted or already-reviewed runs.
- Local metadata is extracted before the provider call.
- No image, key, telemetry, or analytics is sent to a KEEN EYE server.
- Temporary files are not created by the core workflow.
- User paths are handled as filesystem paths; they are never passed to a shell.
- Keys are read from the environment or a mode-restricted config file.
- AI observations are labeled as observations and accompanied by confidence or
  limitations. KEEN EYE does not claim identities, exact locations, or facts
  that are not visible or present in metadata.

The exposure score is an explainable triage heuristic based only on findings
that are actually present. It is not a compliance rating or scientific
cybersecurity standard.

## Troubleshooting

Start with:

```bash
keeneye doctor
```

Common causes:

- **No API key:** run `keeneye setup` or export `GEMINI_API_KEY`.
- **API key rejected:** check that the key is active and permitted to use the
  selected Gemini model.
- **Network failure:** verify DNS, connectivity, firewall rules, and provider
  availability.
- **Unsupported/corrupt image:** convert it to JPEG or PNG and retry.
- **Rate limit:** wait, review provider quotas, or use an approved model.
- **Permission denied:** confirm the image is readable by your user.

Normal errors are rendered with what happened, why it may have happened, and
what to do next. Tracebacks are reserved for `--debug`.

## Development

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
pytest -q
python -m keeneye demo
```

Tests cover configuration precedence, key masking, image validation, metadata
handling, malformed AI responses, scoring, JSON/HTML reports, and CLI error
paths. No test calls a real Gemini API.

## Roadmap

- Pluggable local OCR with an explicit opt-in
- Additional provider adapters behind the same safe interface
- Optional signed report manifests
- More image formats where Termux support remains lightweight

## Creators

**KEEN EYE**  
Created by **Devansh** & **Soham M**

## License

MIT. See [LICENSE](LICENSE).