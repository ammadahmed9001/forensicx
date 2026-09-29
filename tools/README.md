# ForensicX Tool Directory

This directory is populated by `scripts/install_tools.sh`.
Tools are organized by category and cloned/installed from their upstream repositories.

## Structure

```
tools/
├── mobile/          Android & iOS forensic tools
│   ├── ALEX/        Android Logical Extractor (Christian Peter)
│   ├── ALEAPP/      Android Logs Events And Protobuf Parser
│   ├── UFADE/       Universal Forensic Apple Device Extractor
│   ├── iLEAPP/      iOS Logs Events And Protobuf Parser
│   ├── RLEAPP/      Roku Logs Events And Protobuf Parser
│   ├── VLEAPP/      Vehicle Logs Events And Protobuf Parser
│   ├── MVT/         Mobile Verification Toolkit (spyware detection)
│   ├── Andriller/   Android data extraction without root
│   ├── android_triage/  ADB-based triage script
│   ├── apktool/     APK reverse engineering
│   ├── jadx/        DEX to Java decompiler
│   └── dex2jar/     DEX to JAR converter
│
├── disk/            Disk & image forensics
│   ├── bulk_extractor/  Feature extraction from disk images
│   ├── scalpel/     File carver
│   └── (apt tools: sleuthkit, autopsy, foremost, testdisk, dc3dd…)
│
├── memory/          Memory forensics
│   ├── volatility3/ Volatility 3 framework
│   ├── volatility2/ Volatility 2 (legacy)
│   ├── LiME/        Linux Memory Extractor (kernel module)
│   ├── avml/        Microsoft AVML
│   └── MemProcFS/   Memory Process Filesystem
│
├── logs/            Log & timeline analysis
│   ├── plaso/       log2timeline super timeline
│   ├── timesketch/  Collaborative timeline analysis
│   ├── chainsaw/    Windows Event Log hunting
│   ├── hayabusa/    Windows Event Log threat hunting
│   ├── sigma/       Generic SIEM rule format
│   ├── LogonTracer/ Logon event investigation
│   ├── UAC/         Unix-like Artifacts Collector
│   └── evtx/        EVTX parser
│
├── network/         Network forensics
│   └── (apt: wireshark, tshark, tcpdump, zeek, ngrep, tcpflow)
│
├── artifacts/       File & artifact analysis
│   ├── regripper/   Windows Registry parser
│   ├── hindsight/   Chrome forensics
│   ├── didier-tools/ pdfid, pdf-parser (Didier Stevens)
│   ├── oletools/    MS Office analysis
│   ├── peepdf/      PDF analysis
│   ├── binwalk/     Firmware analysis
│   ├── FLOSS/       String de-obfuscation
│   ├── zsteg/       PNG/BMP steganography detection
│   └── StegExpose/  LSB steganography detection
│
├── password/        Password & hash analysis
│   └── (apt: hashcat, john, fcrackzip, pdfcrack)
│
├── malware/         Malware analysis & RE
│   ├── radare2/     Reverse engineering framework
│   ├── capa/        Malware capability detection
│   ├── speakeasy/   Windows emulator
│   ├── die/         Detect It Easy (packer ID)
│   └── ghidra/      NSA Ghidra (manual download required)
│
├── ir/              Incident response
│   ├── velociraptor/ Endpoint visibility
│   ├── GRR/          Google Rapid Response
│   ├── fastir/       FastIR Collector
│   ├── ir-rescue/    Windows IR triage
│   └── (apt: osquery)
│
├── osint/           OSINT tools
│   ├── spiderfoot/  Automated OSINT framework
│   ├── theHarvester/ Email/domain harvesting
│   ├── sherlock/    Username search
│   ├── recon-ng/    Recon framework
│   └── Photon/      Web crawler
│
├── cloud/           Cloud & container forensics
│   ├── docker-explorer/ Container forensics
│   ├── aws-ir/      AWS incident response
│   ├── pacu/        AWS forensics framework
│   └── trufflehog/  Credential leak detection
│
└── reporting/       Reporting utilities
    ├── dfimagetools/ Disk image utilities
    ├── dfvfs/        Digital Forensics VFS
    └── timeline_lab/ Timeline analysis

```

## Quick Install

```bash
bash scripts/install_tools.sh
```

## License notice

Each tool retains its own upstream license.
See each tool's directory for `LICENSE` or `COPYING`.
ForensicX hub code is Apache-2.0 / MIT.
All tools are open-source. Use only on authorized evidence.
