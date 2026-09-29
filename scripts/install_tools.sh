#!/usr/bin/env bash
# ForensicX Master Tool Installer — v2
# Installs every open-source forensic tool.  Each tool is independent;
# one failure NEVER stops the rest.
#
# Usage:
#   bash scripts/install_tools.sh               # install everything
#   bash scripts/install_tools.sh --list        # list tools
#   bash scripts/install_tools.sh --category mobile   # one category only
#   bash scripts/install_tools.sh --parallel    # clone repos in parallel
set -uo pipefail   # NOT -e  — failures are tracked, never fatal

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools"
LOG="$ROOT/tools/install.log"
mkdir -p "$TOOLS"

# ── colour / print ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC}  $*"; echo "[OK]   $*" >> "$LOG"; ((PASS++)) || true; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; echo "[WARN] $*" >> "$LOG"; }
err()  { echo -e "${RED}✗${NC}  $*"; echo "[FAIL] $*" >> "$LOG"; ((FAIL++)) || true; }
info() { echo -e "${CYAN}→${NC}  $*"; echo "[INFO] $*" >> "$LOG"; }
head() { echo; echo -e "${BOLD}${CYAN}══ $* ══${NC}"; echo "== $* ==" >> "$LOG"; }

PASS=0; FAIL=0; SKIP=0
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)  ForensicX install started" > "$LOG"

# ── argument parsing ───────────────────────────────────────────────────────────
ONLY_CAT=""; LIST_ONLY=false; PARALLEL=false; FORCE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --category) ONLY_CAT="${2:-}"; shift 2 ;;
    --list)     LIST_ONLY=true; shift ;;
    --parallel) PARALLEL=true; shift ;;
    --force)    FORCE=true; shift ;;
    *) shift ;;
  esac
done

if $LIST_ONLY; then
  echo "Available categories:  mobile  disk  memory  logs  network  artifacts  password  malware  ir  casemgmt  windows  mobile_re  netmon  osint  cloud  reporting  distros"
  exit 0
fi

# ── prerequisites ──────────────────────────────────────────────────────────────
have()  { command -v "$1" >/dev/null 2>&1; }
need()  { have "$1" || { err "Required tool missing: $1"; exit 1; }; }
need git; need python3

if have python3.12; then PY=python3.12
elif have python3.11; then PY=python3.11
elif have python3.10; then PY=python3.10
else PY=python3; fi
info "Python: $($PY --version 2>&1)"

# ── helpers ────────────────────────────────────────────────────────────────────
# clone  <url>  <rel-dir>
# Always succeeds — warns on failure but continues
clone() {
  local url="$1" dir="$2"
  local dest="$TOOLS/$dir"
  if [[ -n "$ONLY_CAT" ]] && [[ "$dir" != "${ONLY_CAT}"* ]]; then
    ((SKIP++)) || true; return 0
  fi
  if [[ -d "$dest/.git" ]]; then
    git -C "$dest" pull --ff-only -q 2>/dev/null && ok "$dir (updated)" || warn "$dir (pull failed, using cached)"
  else
    mkdir -p "$(dirname "$dest")"
    info "Cloning $dir …"
    if git clone --depth 1 "$url" "$dest" -q 2>>"$LOG"; then
      ok "$dir"
    else
      err "$dir (clone failed — check $LOG for details)"
    fi
  fi
}

# pip_venv  <rel-dir>  [extra-pip-pkgs…]
pip_venv() {
  local dir="$1"; shift
  local dest="$TOOLS/$dir"
  [[ -d "$dest" ]] || return 0
  local venv="$dest/.venv"
  if [[ ! -x "$venv/bin/pip" ]]; then
    "$PY" -m venv "$venv" 2>>"$LOG" || { warn "$dir venv creation failed"; return 0; }
  fi
  "$venv/bin/pip" install -U pip -q 2>>"$LOG" || true
  if [[ -f "$dest/requirements.txt" ]]; then
    "$venv/bin/pip" install -r "$dest/requirements.txt" -q 2>>"$LOG" || warn "$dir requirements partially failed"
  fi
  for pkg in "$@"; do
    "$venv/bin/pip" install "$pkg" -q 2>>"$LOG" || warn "$dir: pip install $pkg failed"
  done
  ok "$dir venv"
}

# pip_global  <package>
pip_global() {
  "$PY" -m pip install "$1" -q 2>>"$LOG" && ok "pip: $1" || warn "pip: $1 failed"
}

# download_binary  <url>  <dest-file>
download_bin() {
  local url="$1" dest="$2"
  if [[ -f "$dest" ]]; then ok "$dest (cached)"; return 0; fi
  mkdir -p "$(dirname "$dest")"
  if have wget; then
    wget -qO "$dest" "$url" 2>>"$LOG" && chmod +x "$dest" && ok "$(basename "$dest")" || err "download failed: $url"
  elif have curl; then
    curl -fsSL "$url" -o "$dest" 2>>"$LOG" && chmod +x "$dest" && ok "$(basename "$dest")" || err "download failed: $url"
  else
    err "wget/curl not found — cannot download $(basename "$dest")"
  fi
}

# download_zip  <url>  <dest-dir>  [strip-components]
download_zip() {
  local url="$1" dest="$2" strip="${3:-0}"
  mkdir -p "$dest"
  local tmp
  tmp=$(mktemp /tmp/fxinst_XXXXXX.zip)
  if have wget; then wget -qO "$tmp" "$url" 2>>"$LOG"
  elif have curl; then curl -fsSL "$url" -o "$tmp" 2>>"$LOG"
  else err "wget/curl required for $(basename "$dest")"; return 1; fi
  unzip -q "$tmp" -d "$dest" 2>>"$LOG" && ok "$(basename "$dest")" || err "unzip failed: $url"
  rm -f "$tmp"
}

# download_tgz  <url>  <dest-dir>  [strip-components]
download_tgz() {
  local url="$1" dest="$2" strip="${3:-1}"
  mkdir -p "$dest"
  local tmp
  tmp=$(mktemp /tmp/fxinst_XXXXXX.tar.gz)
  if have wget; then wget -qO "$tmp" "$url" 2>>"$LOG"
  elif have curl; then curl -fsSL "$url" -o "$tmp" 2>>"$LOG"
  else err "wget/curl required for $(basename "$dest")"; return 1; fi
  tar -xzf "$tmp" -C "$dest" --strip-components="$strip" 2>>"$LOG" && ok "$(basename "$dest")" || err "tar failed: $url"
  rm -f "$tmp"
}

apt_pkgs=()
apt_install() { for pkg in "$@"; do apt_pkgs+=("$pkg"); done; }

BGPIDS=()
maybe_bg() {
  if $PARALLEL; then "$@" & BGPIDS+=($!); else "$@"; fi
}

# ──────────────────────────────────────────────────────────────────────────────
head "MOBILE — Android"
mkdir -p "$TOOLS/mobile"

maybe_bg clone https://github.com/prosch88/ALEX.git               mobile/ALEX
maybe_bg clone https://github.com/abrignoni/ALEAPP.git             mobile/ALEAPP
maybe_bg clone https://github.com/RealityNet/android_triage.git    mobile/android_triage
maybe_bg clone https://github.com/mvt-project/mvt.git              mobile/MVT
maybe_bg clone https://github.com/den4uk/andriller.git             mobile/Andriller
maybe_bg clone https://github.com/abrignoni/VLEAPP.git             mobile/VLEAPP
maybe_bg clone https://github.com/jfarley248/MEAT.git              mobile/MEAT
maybe_bg clone https://github.com/google/android-forensics.git     mobile/android-forensics 2>/dev/null || true
maybe_bg clone https://github.com/AndroidForensics/AFLogical-OSE.git mobile/AFLogical 2>/dev/null || true
$PARALLEL && { wait "${BGPIDS[@]}" 2>/dev/null; BGPIDS=(); }

for d in ALEX ALEAPP MVT Andriller VLEAPP; do
  [[ -d "$TOOLS/mobile/$d" ]] && pip_venv "mobile/$d" || true
done

# apktool
APKTOOL="$TOOLS/mobile/apktool/apktool.jar"
if [[ ! -f "$APKTOOL" ]]; then
  mkdir -p "$TOOLS/mobile/apktool"
  download_bin "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar" "$APKTOOL"
fi

clone https://github.com/pxb1988/dex2jar.git  mobile/dex2jar
clone https://github.com/skylot/jadx.git       mobile/jadx

apt_install adb android-tools-adb

# ──────────────────────────────────────────────────────────────────────────────
head "MOBILE — iOS"

maybe_bg clone https://github.com/prosch88/UFADE.git                   mobile/UFADE
maybe_bg clone https://github.com/abrignoni/iLEAPP.git                 mobile/iLEAPP
maybe_bg clone https://github.com/abrignoni/RLEAPP.git                 mobile/RLEAPP
maybe_bg clone https://github.com/jsharkey13/iphone_backup_decrypt.git mobile/idevice-backup
$PARALLEL && { wait "${BGPIDS[@]}" 2>/dev/null; BGPIDS=(); }

pip_venv mobile/UFADE
pip_venv mobile/iLEAPP
pip_venv mobile/RLEAPP
apt_install libimobiledevice-utils ifuse usbmuxd

# ──────────────────────────────────────────────────────────────────────────────
head "SPYWARE & STALKERWARE DETECTION"
mkdir -p "$TOOLS/spyware"

clone https://github.com/mvt-project/mvt.git              spyware/mvt
clone https://github.com/AssoEchap/stalkerware-indicators.git spyware/stalkerware-indicators
clone https://github.com/Te-k/stalkerware-indicators.git  spyware/stalkerware-indicators-tek 2>/dev/null || true
clone https://github.com/AmnestyTech/investigations.git   spyware/amnesty-investigations

pip_venv spyware/mvt

# Download latest MVT IOC feeds
MVT_IOCS="$TOOLS/spyware/iocs"
mkdir -p "$MVT_IOCS"
download_bin "https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-07-18_nso/pegasus.stix2" \
             "$MVT_IOCS/pegasus.stix2" 2>/dev/null || warn "Pegasus IOC download failed (non-fatal)"

# ──────────────────────────────────────────────────────────────────────────────
head "DISK & IMAGE FORENSICS"
mkdir -p "$TOOLS/disk"

clone https://github.com/simsong/bulk_extractor.git  disk/bulk_extractor
clone https://github.com/sleuthkit/scalpel.git        disk/scalpel

apt_install sleuthkit autopsy foremost testdisk photorec dc3dd ewf-tools \
            xmount afflib-tools ddrescue guymager hashdeep ssdeep \
            gddrescue dcfldd

pip_global dissect 2>/dev/null || true
clone https://github.com/fox-it/dissect.git  disk/dissect 2>/dev/null || true

# ──────────────────────────────────────────────────────────────────────────────
head "MEMORY FORENSICS"
mkdir -p "$TOOLS/memory"

clone https://github.com/volatilityfoundation/volatility3.git  memory/volatility3
clone https://github.com/volatilityfoundation/volatility.git   memory/volatility2
clone https://github.com/504ensicsLabs/LiME.git                memory/LiME
clone https://github.com/microsoft/avml.git                    memory/avml

pip_venv memory/volatility3
pip_venv memory/volatility2

# ──────────────────────────────────────────────────────────────────────────────
head "LOG & TIMELINE ANALYSIS"
mkdir -p "$TOOLS/logs"

clone https://github.com/log2timeline/plaso.git    logs/plaso
clone https://github.com/google/timesketch.git     logs/timesketch
clone https://github.com/SigmaHQ/sigma.git         logs/sigma
clone https://github.com/JPCERTCC/LogonTracer.git  logs/LogonTracer
clone https://github.com/tclahr/uac.git            logs/UAC
clone https://github.com/omerbenamram/evtx.git     logs/evtx

pip_venv logs/plaso
pip_venv logs/LogonTracer

# Chainsaw
CHAINSAW="$TOOLS/logs/chainsaw/chainsaw"
if [[ ! -f "$CHAINSAW" ]]; then
  download_tgz \
    "https://github.com/WithSecureLabs/chainsaw/releases/download/v2.9.0/chainsaw_x86_64-unknown-linux-musl.tar.gz" \
    "$TOOLS/logs/chainsaw" 1 || warn "Chainsaw download failed"
fi

# Hayabusa
HAYABUSA="$TOOLS/logs/hayabusa/hayabusa"
if [[ ! -f "$HAYABUSA" ]]; then
  download_zip \
    "https://github.com/Yamato-Security/hayabusa/releases/download/v2.17.0/hayabusa-2.17.0-linux-x64-musl.zip" \
    "$TOOLS/logs/hayabusa" || warn "Hayabusa download failed"
fi

# ──────────────────────────────────────────────────────────────────────────────
head "NETWORK FORENSICS"
mkdir -p "$TOOLS/network"

clone https://github.com/iagox86/dnscat2.git  network/dnscat2
apt_install wireshark tshark ngrep tcpdump tcpflow zeek nfdump xplico

# ──────────────────────────────────────────────────────────────────────────────
head "ARTIFACT & FILE ANALYSIS"
mkdir -p "$TOOLS/artifacts"

clone https://github.com/keydet89/RegRipper3.0.git              artifacts/regripper
clone https://github.com/obsidianforensics/hindsight.git        artifacts/hindsight
clone https://github.com/DidierStevens/DidierStevensSuite.git   artifacts/didier-tools
clone https://github.com/decalage2/oletools.git                 artifacts/oletools
clone https://github.com/jesparza/peepdf.git                    artifacts/peepdf
clone https://github.com/ReFirmLabs/binwalk.git                 artifacts/binwalk
clone https://github.com/mandiant/flare-floss.git               artifacts/FLOSS
clone https://github.com/dfir-orc/dfir-orc.git                  artifacts/orc

pip_venv artifacts/hindsight
pip_venv artifacts/oletools
pip_venv artifacts/binwalk
pip_venv artifacts/FLOSS
apt_install exiftool libimage-exiftool-perl steghide binutils file

# ──────────────────────────────────────────────────────────────────────────────
head "PASSWORD & HASH ANALYSIS"
apt_install hashcat john fcrackzip pdfcrack
clone https://github.com/psypanda/hashID.git  password/hashid

# ──────────────────────────────────────────────────────────────────────────────
head "MALWARE & REVERSE ENGINEERING"
mkdir -p "$TOOLS/malware"

clone https://github.com/radareorg/radare2.git      malware/radare2
clone https://github.com/mandiant/capa.git          malware/capa
clone https://github.com/mandiant/speakeasy.git     malware/speakeasy
clone https://github.com/horsicq/Detect-It-Easy.git malware/die

pip_venv malware/capa
pip_venv malware/speakeasy
apt_install yara clamav radare2

GHIDRA="$TOOLS/malware/ghidra"
mkdir -p "$GHIDRA"
[[ -f "$GHIDRA/ghidraRun" ]] || warn "Ghidra: download from https://ghidra-sre.org and extract to $GHIDRA"

# ──────────────────────────────────────────────────────────────────────────────
head "MOBILE RE (MobSF / androguard / frida)"
mkdir -p "$TOOLS/mobile_re"

clone https://github.com/MobSF/Mobile-Security-Framework-MobSF.git  mobile_re/MobSF
clone https://github.com/androguard/androguard.git                   mobile_re/androguard
clone https://github.com/sensepost/objection.git                     mobile_re/objection

pip_venv mobile_re/androguard
pip_venv mobile_re/objection
pip_global frida-tools 2>/dev/null || warn "frida-tools failed (try: pip install frida-tools)"

# ──────────────────────────────────────────────────────────────────────────────
head "INCIDENT RESPONSE"
mkdir -p "$TOOLS/ir"

clone https://github.com/google/grr.git                    ir/GRR
clone https://github.com/SekoiaLab/Fastir_Collector.git    ir/fastir
clone https://github.com/diogo-fernan/ir-rescue.git        ir/ir-rescue
clone https://github.com/CrowdStrike/forensics.git         ir/crowdstrike-forensics
clone https://github.com/Velocidex/velociraptor.git        ir/velociraptor
clone https://github.com/Neo23x0/Loki.git                  ir/loki
clone https://github.com/Invoke-IR/PowerForensics.git      ir/powerforensics

pip_venv ir/loki
apt_install osquery

# Velociraptor binary
VR="$TOOLS/ir/velociraptor-bin/velociraptor"
download_bin \
  "https://github.com/Velocidex/velociraptor/releases/download/v0.72.4/velociraptor-v0.72.4-linux-amd64" \
  "$VR" || warn "Velociraptor download failed"

# ──────────────────────────────────────────────────────────────────────────────
head "CASE MANAGEMENT (Docker-based)"
mkdir -p "$TOOLS/case_mgmt"

clone https://github.com/dfir-iris/iris-web.git       case_mgmt/dfir-iris
clone https://github.com/TheHive-Project/TheHive.git  case_mgmt/TheHive
clone https://github.com/TheHive-Project/Cortex.git   case_mgmt/Cortex

if have docker; then
  info "Docker found — DFIR-IRIS and TheHive can be started with 'docker compose up -d'"
else
  warn "Docker not found — install Docker to use DFIR-IRIS/TheHive: https://docs.docker.com/get-docker/"
fi

# ──────────────────────────────────────────────────────────────────────────────
head "WINDOWS ARTIFACTS (EZ Tools)"
mkdir -p "$TOOLS/windows/EZTools"
EZ="$TOOLS/windows/EZTools"
EZ_BASE="https://f001.backblazeb2.com/file/EricZimmermanTools/net6"

for tool in LECmd PECmd JLECmd MFTCmd RBCmd AppCompatCacheParser AmcacheParser EvtxECmd SrumECmd WxTCmd; do
  if [[ ! -d "$EZ/$tool" ]]; then
    mkdir -p "$EZ/$tool"
    tmp=$(mktemp /tmp/ez_XXXXXX.zip)
    if have wget; then wget -qO "$tmp" "${EZ_BASE}/${tool}.zip" 2>>"$LOG"
    elif have curl; then curl -fsSL "${EZ_BASE}/${tool}.zip" -o "$tmp" 2>>"$LOG"; fi
    unzip -q "$tmp" -d "$EZ/$tool" 2>>"$LOG" && ok "EZTool: $tool" || warn "EZTool: $tool download failed"
    rm -f "$tmp"
  else ok "EZTool: $tool (cached)"; fi
done

# ──────────────────────────────────────────────────────────────────────────────
head "NETWORK DETECTION (Suricata / Arkime / Kismet)"
mkdir -p "$TOOLS/netmon"

clone https://github.com/OISF/suricata.git         netmon/suricata
clone https://github.com/arkime/arkime.git          netmon/arkime
clone https://github.com/kismetwireless/kismet.git  netmon/kismet

apt_install suricata snort tshark

# ──────────────────────────────────────────────────────────────────────────────
head "OSINT"
mkdir -p "$TOOLS/osint"

clone https://github.com/smicallef/spiderfoot.git      osint/spiderfoot
clone https://github.com/laramies/theHarvester.git     osint/theHarvester
clone https://github.com/sherlock-project/sherlock.git osint/sherlock
clone https://github.com/lanmaster53/recon-ng.git      osint/recon-ng
clone https://github.com/s0md3v/Photon.git             osint/Photon

for d in spiderfoot theHarvester sherlock recon-ng Photon; do
  pip_venv "osint/$d"
done

# ──────────────────────────────────────────────────────────────────────────────
head "CLOUD & CONTAINER"
mkdir -p "$TOOLS/cloud"

clone https://github.com/google/docker-explorer.git  cloud/docker-explorer
clone https://github.com/ThreatResponse/aws_ir.git   cloud/aws-ir
clone https://github.com/RhinoSecurityLabs/pacu.git  cloud/pacu

pip_venv cloud/docker-explorer
pip_venv cloud/aws-ir
pip_venv cloud/pacu

TH="$TOOLS/cloud/trufflehog/trufflehog"
download_tgz \
  "https://github.com/trufflesecurity/trufflehog/releases/download/v3.82.6/trufflehog_3.82.6_linux_amd64.tar.gz" \
  "$TOOLS/cloud/trufflehog" 0 || warn "Trufflehog download failed"
[[ -f "$TOOLS/cloud/trufflehog/trufflehog" ]] && chmod +x "$TOOLS/cloud/trufflehog/trufflehog"

# ──────────────────────────────────────────────────────────────────────────────
head "REPORTING"
mkdir -p "$TOOLS/reporting"

clone https://github.com/libyal/dfimagetools.git              reporting/dfimagetools
clone https://github.com/log2timeline/dfvfs.git               reporting/dfvfs
clone https://github.com/certsocietegenerale/timeline-lab.git reporting/timeline_lab

pip_venv reporting/dfvfs

# ──────────────────────────────────────────────────────────────────────────────
head "APT BATCH INSTALL"
if [[ ${#apt_pkgs[@]} -gt 0 ]]; then
  mapfile -t apt_pkgs < <(printf '%s\n' "${apt_pkgs[@]}" | sort -u)
  info "Installing ${#apt_pkgs[@]} apt packages…"
  if have apt-get; then
    sudo apt-get update -qq 2>/dev/null || warn "apt-get update failed"
    # Install each package individually so one failure doesn't block others
    for pkg in "${apt_pkgs[@]}"; do
      sudo apt-get install -y "$pkg" -qq 2>>"$LOG" && ok "apt: $pkg" || warn "apt: $pkg failed (may need manual install)"
    done
  else
    warn "apt-get not found — install manually: ${apt_pkgs[*]}"
  fi
fi

# ──────────────────────────────────────────────────────────────────────────────
head "SUMMARY"
TOTAL=$((PASS + FAIL + SKIP))
echo
echo -e "  ${GREEN}✓ Passed:${NC}  $PASS"
echo -e "  ${RED}✗ Failed:${NC}  $FAIL"
echo -e "  ${YELLOW}⊘ Skipped:${NC} $SKIP"
echo -e "  Total:      $TOTAL"
echo
echo -e "  Full log:   ${CYAN}$LOG${NC}"
echo -e "  Tools dir:  ${CYAN}$TOOLS${NC}"
echo
echo "  Start hub:  ${BOLD}forensicx web${NC}   or   ${BOLD}python3 -m forensicx_hub${NC}"
echo

if [[ $FAIL -gt 0 ]]; then
  echo -e "  ${YELLOW}Some tools failed to install. This is normal — network issues, missing"
  echo -e "  system libraries, or platform restrictions. Re-run to retry failed tools."
  echo -e "  The hub works fully with whichever tools succeeded.${NC}"
fi
