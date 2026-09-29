# ForensicX

A comprehensive open-source forensic workstation — tool hub, case management, artifact parsing, and timeline analysis for digital forensics investigations.

> **Use only on devices and evidence you are authorized to examine.**

## What's inside

ForensicX has two layers:

### 1. ForensicX Hub — multi-tool launcher
A GUI that discovers, installs, and launches **60+ open-source forensic tools** organized by category:

| Category | Tools |
|---|---|
| Mobile (Android) | ALEX, ALEAPP, android_triage, MVT, Andriller, VLEAPP, apktool, jadx |
| Mobile (iOS/Apple) | UFADE, iLEAPP, RLEAPP, libimobiledevice |
| Disk & Imaging | Autopsy, Sleuth Kit, bulk_extractor, Scalpel, foremost, PhotoRec, dc3dd, ewf-tools, guymager |
| Memory | Volatility 3/2, LiME, AVML, MemProcFS |
| Logs & Timeline | Plaso, Timesketch, Chainsaw, Hayabusa, Sigma, LogonTracer, UAC |
| Network | Wireshark, tshark, NetworkMiner, Zeek, tcpdump, tcpflow |
| Artifact Analysis | ExifTool, RegRipper, Hindsight, pdfid, oletools, binwalk, FLOSS, steghide, zsteg |
| Password & Hash | Hashcat, John the Ripper, hashID, fcrackzip |
| Malware & RE | Ghidra, Radare2, YARA, ClamAV, capa, speakeasy, Detect-It-Easy |
| Incident Response | Velociraptor, osquery, GRR, FastIR, KAPE |
| OSINT | SpiderFoot, theHarvester, Sherlock, Recon-ng, Photon |
| Cloud & Container | docker-explorer, aws-ir, pacu, TruffleHog |
| Reporting | dfimagetools, dfvfs, Timeline Lab |

### 2. ForensicX Core — case management
SQLite-backed case database with chain-of-custody hashing, artifact parsers, full-text search, and JSON reports.

## Installation

```bash
git clone https://github.com/ammadahmed9001/forensicx
cd forensicx

# Install ForensicX itself
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Install all forensic tools
chmod +x scripts/install_tools.sh
bash scripts/install_tools.sh
```

## Launch

```bash
# Hub (all forensic tools)
forensicx hub
# or:
python3 -m forensicx_hub
# or:
bash scripts/start_forensicx.sh

# Case management GUI only
forensicx gui
```

## CLI

```bash
forensicx case create "Android Investigation" --investigator "Examiner Name"
forensicx case list
forensicx evidence import 1 sample_evidence/sample.txt
forensicx search 1 "location"
forensicx report 1 reports/case.json
```

## Workflow

```
Authorized device / evidence
          │
          ▼
    ALEX / android_triage / UFADE   ← acquisition
          │
          ▼
    ALEAPP / iLEAPP / Volatility    ← parsing
          │
          ▼
    Plaso + Timesketch / Chainsaw   ← timeline & log analysis
          │
          ▼
    ForensicX case workspace        ← unified case DB, hashes, reports
          │
          ├── timeline view
          ├── full-text search
          ├── hash manifest
          └── JSON / HTML report
```

## Individual tool launchers

```bash
bash scripts/launchers/launch_aleapp.sh
bash scripts/launchers/launch_alex.sh
bash scripts/launchers/launch_ufade.sh
bash scripts/launchers/launch_ileapp.sh
bash scripts/launchers/launch_mvt.sh
bash scripts/launchers/launch_volatility3.sh
bash scripts/launchers/launch_hindsight.sh
bash scripts/launchers/launch_spiderfoot.sh
bash scripts/launchers/launch_android_triage.sh
```

## Check Android device

```bash
bash scripts/check_android.sh
# or:
adb devices -l
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tool list & attribution

See [docs/UPSTREAM.md](docs/UPSTREAM.md) for the full list of 60+ tools with authors, licenses, and upstream repository links.

## Adding a parser

See [docs/PARSER_SDK.md](docs/PARSER_SDK.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

ForensicX hub/core code: Apache-2.0 / MIT — see [LICENSE](LICENSE).
Each upstream tool retains its own license.
