# Roadmap

## v0.1 — Foundation (current)
- [x] SQLite persistence with FTS5 full-text search
- [x] SHA-256 + MD5 chain-of-custody hashing
- [x] Generic text parser
- [x] Click CLI (`case`, `evidence`, `search`, `report`)
- [x] Tkinter GUI
- [x] JSON report export
- [x] GitHub Actions CI

## v0.2 — Android Core Parsers
- [ ] `android_sms` — `mmssms.db` WAL-aware parser
- [ ] `android_calls` — call log parser
- [ ] `android_contacts` — contacts parser
- [ ] `android_location` — GPS/Wi-Fi/cell cache parser
- [ ] `android_browser` — browser history (AOSP + Chrome)
- [ ] SQLite WAL + SHM stitching utility

## v0.3 — Timeline & Correlation
- [ ] Cross-source timeline view (GUI + CLI)
- [ ] Event correlation engine
- [ ] Interactive timeline chart in GUI

## v0.4 — Acquisition
- [ ] ADB pull integration (with hash verification)
- [ ] Android backup (`.ab`) extraction
- [ ] Filesystem image (ext4 / F2FS) mount helper

## v0.5 — Reporting
- [ ] HTML report with embedded timeline
- [ ] PDF export
- [ ] DFXML output

## v1.0 — Production
- [ ] Plugin packaging (install parsers as pip packages)
- [ ] Multi-user case management
- [ ] Encrypted case storage
- [ ] Automated regression test suite for each parser
