# ForensicX

A modular, open-source Android digital forensics platform for evidence acquisition, artifact parsing, timeline correlation, and report generation.

## Features

- **Evidence Management** — import, hash-verify, and chain-of-custody tracking
- **Android Artifact Parsers** — SQLite/WAL/SHM, SMS, call logs, contacts, location data
- **Timeline Correlation** — cross-source event reconstruction
- **Full-Text Search** — indexed search across all acquired artifacts
- **GUI + CLI** — Tkinter-based desktop interface and `forensicx` command-line tool
- **Plugin SDK** — drop-in parser modules for new artifact types

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"

pytest
```

### Launch GUI

```bash
forensicx gui
```

### CLI Usage

```bash
# Create a case
forensicx case create "Android Investigation" --investigator "Examiner Name"

# List cases
forensicx case list

# Import evidence
forensicx evidence import 1 sample_evidence/sample.txt

# Search evidence
forensicx search 1 "location"

# Export report
mkdir -p reports
forensicx report 1 reports/case.json
```

## Project Structure

```
forensicx/
├── .github/
│   ├── workflows/ci.yml
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PARSER_SDK.md
│   └── ROADMAP.md
├── sample_evidence/
├── src/
│   └── forensicx/
│       ├── core/          # DB, hashing, data models
│       ├── gui/           # Tkinter application
│       ├── parsers/       # Artifact parsers (generic + Android)
│       ├── services/      # Business logic
│       ├── cli.py         # CLI entry point
│       └── __main__.py
├── tests/
├── scripts/
├── pyproject.toml
└── requirements.txt
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a full description of the pipeline:

```
Evidence → Acquisition → Parsers → Normalization → Correlation → Timeline/Graph → Search → Reports
```

## Adding a Parser

See [docs/PARSER_SDK.md](docs/PARSER_SDK.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).
