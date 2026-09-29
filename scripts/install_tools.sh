#!/usr/bin/env bash
# ForensicX Master Tool Installer
# Installs / updates every open-source forensic tool in the registry.
# Usage: bash scripts/install_tools.sh [--category <cat>] [--list]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools"
LOG="$ROOT/tools/install.log"
mkdir -p "$TOOLS"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; echo "[OK]  $*" >> "$LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; echo "[WARN] $*" >> "$LOG"; }
err()  { echo -e "${RED}[ERR]${NC}  $*"; echo "[ERR]  $*" >> "$LOG"; }
info() { echo -e "${CYAN}[INFO]${NC} $*"; echo "[INFO] $*" >> "$LOG"; }

need() { command -v "$1" >/dev/null 2>&1 || { err "Missing required tool: $1"; exit 1; }; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)  ForensicX install started" >> "$LOG"

# ── detect python ─────────────────────────────────────────────────────────────
need git
need python3

if have python3.11; then PY=python3.11
elif have python3.12; then PY=python3.12
elif have python3.10; then PY=python3.10
else PY=python3; fi
info "Python: $($PY --version 2>&1)"

# ── helpers ───────────────────────────────────────────────────────────────────
clone() {
  local url="$1" dir="$2"
  local dest="$TOOLS/$dir"
  if [[ -d "$dest/.git" ]]; then
    info "Updating $dir…"
    git -C "$dest" pull --ff-only 2>/dev/null || warn "Could not update $dir"
  elif [[ -d "$dest" ]]; then
    warn "$dest exists but is not a git repo; skipping"
  else
    info "Cloning $dir from $url…"
    git clone --depth 1 "$url" "$dest" || { err "Clone failed: $dir"; return 1; }
  fi
  ok "$dir"
}

pip_venv() {
  local dir="$1"; shift
  local venv="$TOOLS/$dir/.venv"
  if [[ ! -x "$venv/bin/pip" ]]; then
    "$PY" -m venv "$venv" || { warn "venv failed for $dir"; return; }
  fi
  "$venv/bin/pip" install -U pip --quiet
  if [[ -f "$TOOLS/$dir/requirements.txt" ]]; then
    "$venv/bin/pip" install -r "$TOOLS/$dir/requirements.txt" --quiet || warn "Some deps failed for $dir"
  fi
  for pkg in "$@"; do
    "$venv/bin/pip" install "$pkg" --quiet || warn "pip install $pkg failed"
  done
  ok "$dir venv"
}

apt_pkgs=()
apt_install() { for pkg in "$@"; do apt_pkgs+=("$pkg"); done; }

# ──────────────────────────────────────────────────────────────────────────────
# MOBILE — Android
# ──────────────────────────────────────────────────────────────────────────────
info "=== Mobile Forensics (Android) ==="
mkdir -p "$TOOLS/mobile"

clone https://github.com/prosch88/ALEX.git              mobile/ALEX
clone https://github.com/abrignoni/ALEAPP.git            mobile/ALEAPP
clone https://github.com/RealityNet/android_triage.git   mobile/android_triage
clone https://github.com/mvt-project/mvt.git             mobile/MVT
clone https://github.com/den4uk/andriller.git            mobile/Andriller
clone https://github.com/abrignoni/VLEAPP.git            mobile/VLEAPP
clone https://github.com/jfarley248/MEAT.git             mobile/AEX

# Install Python deps for each
for d in ALEX UFADE ALEAPP MVT Andriller VLEAPP; do
  [[ -d "$TOOLS/mobile/$d" ]] && pip_venv "mobile/$d" || true
done

apt_install adb android-tools-adb

# ── Android RE tools ──────────────────────────────────────────────────────────
info "Android RE tools…"
clone https://github.com/pxb1988/dex2jar.git  mobile/dex2jar
clone https://github.com/skylot/jadx.git       mobile/jadx

# apktool binary
APKTOOL_DIR="$TOOLS/mobile/apktool"
mkdir -p "$APKTOOL_DIR"
if [[ ! -f "$APKTOOL_DIR/apktool.jar" ]]; then
  APKTOOL_VER="2.9.3"
  wget -qO "$APKTOOL_DIR/apktool.jar" \
    "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VER}/apktool_${APKTOOL_VER}.jar" \
    || warn "apktool download failed; get it manually from https://apktool.org"
fi

# ──────────────────────────────────────────────────────────────────────────────
# MOBILE — iOS / Apple
# ──────────────────────────────────────────────────────────────────────────────
info "=== Mobile Forensics (iOS/Apple) ==="

clone https://github.com/prosch88/UFADE.git                  mobile/UFADE
clone https://github.com/abrignoni/iLEAPP.git                mobile/iLEAPP
clone https://github.com/abrignoni/RLEAPP.git                mobile/RLEAPP
clone https://github.com/jsharkey13/iphone_backup_decrypt.git mobile/idevice-backup

pip_venv mobile/iLEAPP
pip_venv mobile/RLEAPP
apt_install libimobiledevice-utils ifuse usbmuxd

# ──────────────────────────────────────────────────────────────────────────────
# DISK & IMAGE FORENSICS
# ──────────────────────────────────────────────────────────────────────────────
info "=== Disk & Image Forensics ==="
mkdir -p "$TOOLS/disk"

clone https://github.com/simsong/bulk_extractor.git  disk/bulk_extractor
clone https://github.com/sleuthkit/scalpel.git        disk/scalpel

apt_install sleuthkit autopsy foremost testdisk photorec dc3dd ewf-tools \
            xmount afflib-tools ddrescue guymager hashdeep ssdeep fdupes \
            gddrescue dcfldd

# ──────────────────────────────────────────────────────────────────────────────
# MEMORY FORENSICS
# ──────────────────────────────────────────────────────────────────────────────
info "=== Memory Forensics ==="
mkdir -p "$TOOLS/memory"

clone https://github.com/volatilityfoundation/volatility3.git  memory/volatility3
clone https://github.com/volatilityfoundation/volatility.git   memory/volatility2
clone https://github.com/504ensicsLabs/LiME.git                memory/LiME
clone https://github.com/microsoft/avml.git                    memory/avml
clone https://github.com/ufrisk/MemProcFS.git                  memory/MemProcFS

pip_venv memory/volatility3
pip_venv memory/volatility2

# ──────────────────────────────────────────────────────────────────────────────
# LOG / TIMELINE ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────
info "=== Log & Timeline Analysis ==="
mkdir -p "$TOOLS/logs"

clone https://github.com/log2timeline/plaso.git       logs/plaso
clone https://github.com/google/timesketch.git        logs/timesketch
clone https://github.com/SigmaHQ/sigma.git            logs/sigma
clone https://github.com/JPCERTCC/LogonTracer.git     logs/LogonTracer
clone https://github.com/tclahr/uac.git               logs/UAC
clone https://github.com/omerbenamram/evtx.git        logs/evtx

pip_venv logs/plaso
pip_venv logs/LogonTracer

# Chainsaw binary (Linux AMD64)
CHAINSAW_DIR="$TOOLS/logs/chainsaw"
mkdir -p "$CHAINSAW_DIR"
if [[ ! -f "$CHAINSAW_DIR/chainsaw" ]]; then
  CHAINSAW_VER="2.9.0"
  wget -qO "/tmp/chainsaw.tar.gz" \
    "https://github.com/WithSecureLabs/chainsaw/releases/download/v${CHAINSAW_VER}/chainsaw_x86_64-unknown-linux-musl.tar.gz" \
    && tar -xzf /tmp/chainsaw.tar.gz -C "$CHAINSAW_DIR" --strip-components=1 \
    || warn "Chainsaw download failed; get from https://github.com/WithSecureLabs/chainsaw/releases"
fi

# Hayabusa binary
HAYABUSA_DIR="$TOOLS/logs/hayabusa"
mkdir -p "$HAYABUSA_DIR"
if [[ ! -f "$HAYABUSA_DIR/hayabusa" ]]; then
  HAYABUSA_VER="2.17.0"
  wget -qO "/tmp/hayabusa.zip" \
    "https://github.com/Yamato-Security/hayabusa/releases/download/v${HAYABUSA_VER}/hayabusa-${HAYABUSA_VER}-linux-x64-musl.zip" \
    && unzip -q /tmp/hayabusa.zip -d "$HAYABUSA_DIR" \
    || warn "Hayabusa download failed; get from https://github.com/Yamato-Security/hayabusa/releases"
fi

# ──────────────────────────────────────────────────────────────────────────────
# NETWORK FORENSICS
# ──────────────────────────────────────────────────────────────────────────────
info "=== Network Forensics ==="
mkdir -p "$TOOLS/network"

clone https://github.com/iagox86/dnscat2.git  network/dnscat2

apt_install wireshark tshark ngrep tcpdump tcpflow zeek nfdump xplico

# ──────────────────────────────────────────────────────────────────────────────
# FILE / ARTIFACT ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────
info "=== Artifact & File Analysis ==="
mkdir -p "$TOOLS/artifacts"

clone https://github.com/keydet89/RegRipper3.0.git        artifacts/regripper
clone https://github.com/obsidianforensics/hindsight.git  artifacts/hindsight
clone https://github.com/DidierStevens/DidierStevensSuite.git  artifacts/didier-tools
clone https://github.com/decalage2/oletools.git           artifacts/oletools
clone https://github.com/jesparza/peepdf.git              artifacts/peepdf
clone https://github.com/ReFirmLabs/binwalk.git           artifacts/binwalk
clone https://github.com/mandiant/flare-floss.git         artifacts/FLOSS
clone https://github.com/zed-0xff/zsteg.git               artifacts/zsteg
clone https://github.com/b3dk7/StegExpose.git             artifacts/StegExpose
clone https://github.com/dfir-orc/dfir-orc.git            artifacts/orc

pip_venv artifacts/hindsight
pip_venv artifacts/oletools
pip_venv artifacts/binwalk
pip_venv artifacts/FLOSS

apt_install exiftool libimage-exiftool-perl steghide binutils \
            libfile-type-perl file

# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD & HASH
# ──────────────────────────────────────────────────────────────────────────────
info "=== Password & Hash Analysis ==="
apt_install hashcat john fcrackzip pdfcrack

clone https://github.com/psypanda/hashID.git  password/hashid
"$PY" -m pip install hashid --quiet || true

# ──────────────────────────────────────────────────────────────────────────────
# MALWARE / REVERSE ENGINEERING
# ──────────────────────────────────────────────────────────────────────────────
info "=== Malware Analysis & Reverse Engineering ==="
mkdir -p "$TOOLS/malware"

clone https://github.com/radareorg/radare2.git     malware/radare2
clone https://github.com/mandiant/capa.git         malware/capa
clone https://github.com/mandiant/speakeasy.git    malware/speakeasy
clone https://github.com/horsicq/Detect-It-Easy.git malware/die

pip_venv malware/capa
pip_venv malware/speakeasy

apt_install yara clamav radare2

# Ghidra — point user to download page (large binary)
GHIDRA_DIR="$TOOLS/malware/ghidra"
mkdir -p "$GHIDRA_DIR"
if [[ ! -f "$GHIDRA_DIR/ghidraRun" ]]; then
  warn "Ghidra not found at $GHIDRA_DIR."
  warn "Download from https://ghidra-sre.org and extract to $GHIDRA_DIR"
fi

# ──────────────────────────────────────────────────────────────────────────────
# INCIDENT RESPONSE
# ──────────────────────────────────────────────────────────────────────────────
info "=== Incident Response ==="
mkdir -p "$TOOLS/ir"

clone https://github.com/google/grr.git                       ir/GRR
clone https://github.com/SekoiaLab/Fastir_Collector.git       ir/fastir
clone https://github.com/diogo-fernan/ir-rescue.git           ir/ir-rescue
clone https://github.com/CrowdStrike/forensics.git            ir/crowdstrike-forensics
clone https://github.com/Velocidex/velociraptor.git           ir/velociraptor

apt_install osquery

# Velociraptor binary
VR_DIR="$TOOLS/ir/velociraptor-bin"
mkdir -p "$VR_DIR"
if [[ ! -f "$VR_DIR/velociraptor" ]]; then
  VR_VER="0.72.4"
  wget -qO "$VR_DIR/velociraptor" \
    "https://github.com/Velocidex/velociraptor/releases/download/v${VR_VER}/velociraptor-v${VR_VER}-linux-amd64" \
    && chmod +x "$VR_DIR/velociraptor" \
    || warn "Velociraptor download failed; get from https://github.com/Velocidex/velociraptor/releases"
fi

# ──────────────────────────────────────────────────────────────────────────────
# OSINT
# ──────────────────────────────────────────────────────────────────────────────
info "=== OSINT ==="
mkdir -p "$TOOLS/osint"

clone https://github.com/smicallef/spiderfoot.git        osint/spiderfoot
clone https://github.com/laramies/theHarvester.git       osint/theHarvester
clone https://github.com/sherlock-project/sherlock.git   osint/sherlock
clone https://github.com/lanmaster53/recon-ng.git        osint/recon-ng
clone https://github.com/lockfale/osint-framework.git    osint/osint-framework
clone https://github.com/s0md3v/Photon.git               osint/Photon

for d in spiderfoot theHarvester sherlock recon-ng Photon; do
  pip_venv "osint/$d"
done

# ──────────────────────────────────────────────────────────────────────────────
# CLOUD & CONTAINER
# ──────────────────────────────────────────────────────────────────────────────
info "=== Cloud & Container Forensics ==="
mkdir -p "$TOOLS/cloud"

clone https://github.com/google/docker-explorer.git   cloud/docker-explorer
clone https://github.com/ThreatResponse/aws_ir.git    cloud/aws-ir
clone https://github.com/RhinoSecurityLabs/pacu.git   cloud/pacu

pip_venv cloud/docker-explorer
pip_venv cloud/aws-ir
pip_venv cloud/pacu

# Trufflehog binary
TH_DIR="$TOOLS/cloud/trufflehog"
mkdir -p "$TH_DIR"
if [[ ! -f "$TH_DIR/trufflehog" ]]; then
  TH_VER="3.82.6"
  wget -qO "/tmp/trufflehog.tar.gz" \
    "https://github.com/trufflesecurity/trufflehog/releases/download/v${TH_VER}/trufflehog_${TH_VER}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/trufflehog.tar.gz -C "$TH_DIR" trufflehog \
    && chmod +x "$TH_DIR/trufflehog" \
    || warn "Trufflehog download failed"
fi

# ──────────────────────────────────────────────────────────────────────────────
# REPORTING
# ──────────────────────────────────────────────────────────────────────────────
info "=== Reporting & Utilities ==="
mkdir -p "$TOOLS/reporting"

clone https://github.com/libyal/dfimagetools.git        reporting/dfimagetools
clone https://github.com/log2timeline/dfvfs.git         reporting/dfvfs
clone https://github.com/certsocietegenerale/timeline-lab.git  reporting/timeline_lab

pip_venv reporting/dfvfs

# ──────────────────────────────────────────────────────────────────────────────
# APT BATCH INSTALL
# ──────────────────────────────────────────────────────────────────────────────
if [[ ${#apt_pkgs[@]} -gt 0 ]]; then
  info "=== Installing apt packages ==="
  # De-duplicate
  mapfile -t apt_pkgs < <(printf '%s\n' "${apt_pkgs[@]}" | sort -u)
  info "Packages: ${apt_pkgs[*]}"
  if have apt-get; then
    sudo apt-get update -qq 2>/dev/null || warn "apt-get update failed"
    sudo apt-get install -y "${apt_pkgs[@]}" 2>/dev/null || warn "Some apt packages failed; install manually"
    ok "apt packages"
  else
    warn "apt-get not available; install manually: ${apt_pkgs[*]}"
  fi
fi

# ──────────────────────────────────────────────────────────────────────────────
info "=== Install complete ==="
info "Tools directory: $TOOLS"
info "Log: $LOG"
echo
echo "  Start the hub:  python3 -m forensicx_hub"
echo "  Or via CLI:     forensicx hub"
echo
