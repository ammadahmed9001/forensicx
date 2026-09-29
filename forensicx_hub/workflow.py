"""
Automated forensic triage workflows.
Each workflow is a generator yielding (step_name, log_line) tuples
so the GUI can stream progress in real time.
"""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

Step = tuple[str, str]  # (step_name, message)


def _run(cmd: list[str], cwd: Path | None = None,
         env: dict | None = None, timeout: int = 300) -> tuple[int, str]:
    import os
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=cwd, env=full_env, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "Timed out"
    except Exception as exc:
        return -1, str(exc)


def _adb(serial: str, *args: str, timeout: int = 30) -> tuple[int, str]:
    return _run(["adb", "-s", serial, *args], timeout=timeout)


def _py(tool_dir: Path) -> str:
    venv = tool_dir / ".venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


# ─────────────────────────────────────────────────────────────────────────────
# COMPREHENSIVE ANDROID SCAN  (authority-grade)
# ─────────────────────────────────────────────────────────────────────────────

def comprehensive_android_scan(
    serial: str,
    case_dir: Path,
    investigator: str = "ForensicX",
    run_alex: bool = True,
    run_triage: bool = True,
    run_aleapp: bool = True,
    run_mvt: bool = True,
    run_spyware: bool = True,
) -> Iterator[Step]:
    """
    Full authority-grade Android forensic pipeline:
      1.  Device fingerprint (all getprop, IMEI, build)
      2.  ADB bugreport
      3.  Installed apps inventory
      4.  Running processes snapshot
      5.  Network connections
      6.  Call logs
      7.  SMS messages
      8.  Browser history
      9.  Account list
      10. APK pull (3rd-party apps)
      11. ALEX logical extraction
      12. android_triage system artifacts
      13. ALEAPP artifact parser
      14. MVT spyware / stalkerware scan
      15. Stalkerware indicator check
      16. HTML report generation with file navigator
      17. ForensicX case DB import
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"android_{serial}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    findings: list[dict] = []
    device_info: dict = {}

    yield "init", f"═══ ForensicX Comprehensive Android Scan ═══"
    yield "init", f"Device  : {serial}"
    yield "init", f"Output  : {out_dir}"
    yield "init", f"Started : {ts} UTC"
    yield "init", f"────────────────────────────────────────────"

    # ── 1. Device fingerprint ─────────────────────────────────────────────────
    yield "device", "📱 [1/17] Collecting device fingerprint…"
    props = {
        "model": "ro.product.model", "mfr": "ro.product.manufacturer",
        "android": "ro.build.version.release", "sdk": "ro.build.version.sdk",
        "build": "ro.build.display.id", "serial": "ro.serialno",
        "imei": "persist.radio.imei", "brand": "ro.product.brand",
        "device": "ro.product.device", "product": "ro.product.name",
        "bootloader": "ro.bootloader", "radio": "gsm.version.baseband",
        "fingerprint": "ro.build.fingerprint", "security_patch": "ro.build.version.security_patch",
        "kernel": "os.version",
    }
    for key, prop in props.items():
        rc, out = _adb(serial, "shell", "getprop", prop)
        device_info[key] = out.strip()
        yield "device", f"  {key:20s}: {device_info[key]}"

    (out_dir / "device_info.json").write_text(json.dumps(device_info, indent=2))
    yield "device", "  ✓ device_info.json saved"

    # ── 2. ADB bugreport ──────────────────────────────────────────────────────
    yield "bugreport", "📋 [2/17] Capturing ADB bugreport…"
    rc, out = _run(["adb", "-s", serial, "bugreport",
                    str(out_dir / "bugreport.zip")], timeout=180)
    if rc == 0:
        yield "bugreport", "  ✓ bugreport.zip saved"
    else:
        yield "bugreport", f"  ⚠ bugreport failed (non-fatal): {out[:120]}"

    # ── 3. Installed apps ─────────────────────────────────────────────────────
    yield "apps", "📦 [3/17] Enumerating installed applications…"
    rc, apps_out = _adb(serial, "shell", "pm", "list", "packages", "-f", "-3")
    (out_dir / "installed_apps.txt").write_text(apps_out)
    app_count = apps_out.count("\n") + 1 if apps_out.strip() else 0
    yield "apps", f"  ✓ {app_count} third-party apps listed → installed_apps.txt"

    # Known spyware package names (partial list)
    SPYWARE_PKGS = {
        "com.android.callrecorder", "com.spy", "com.mspy", "com.spyera",
        "com.flexispy", "org.monitor", "com.hoverwatch", "net.spyzie",
        "com.phonetracker", "com.stalkerware", "com.trackview",
        "com.checkin", "com.cerberus.app", "com.thetruthspy",
    }
    for line in apps_out.splitlines():
        pkg = line.split("=")[-1].strip() if "=" in line else line.strip()
        if any(s in pkg.lower() for s in ("spy", "track", "monitor", "keylog", "surv", "stalker")):
            findings.append({
                "severity": "high",
                "title": f"Suspicious app package: {pkg}",
                "description": f"Package name matches known spyware/stalkerware patterns: {pkg}",
                "path": str(out_dir / "installed_apps.txt"),
            })
            yield "apps", f"  ⚠ SUSPICIOUS package: {pkg}"

    # ── 4. Running processes ──────────────────────────────────────────────────
    yield "procs", "⚙️  [4/17] Capturing running processes…"
    rc, ps_out = _adb(serial, "shell", "ps", "-A")
    (out_dir / "processes.txt").write_text(ps_out)
    proc_count = ps_out.count("\n")
    yield "procs", f"  ✓ {proc_count} processes → processes.txt"

    # ── 5. Network connections ─────────────────────────────────────────────────
    yield "network", "🌐 [5/17] Dumping active network connections…"
    rc, net_out = _adb(serial, "shell", "cat", "/proc/net/tcp", "/proc/net/tcp6",
                       "/proc/net/udp", "/proc/net/udp6")
    (out_dir / "network_connections.txt").write_text(net_out)
    yield "network", f"  ✓ network_connections.txt"
    rc2, ss_out = _adb(serial, "shell", "ss", "-tuln")
    (out_dir / "open_ports.txt").write_text(ss_out)
    yield "network", f"  ✓ open_ports.txt"

    # ── 6. Call logs ──────────────────────────────────────────────────────────
    yield "calls", "📞 [6/17] Extracting call log…"
    rc, calls = _adb(serial, "shell", "content", "query",
                     "--uri", "content://call_log/calls",
                     "--projection", "number,type,date,duration,name")
    (out_dir / "call_log.txt").write_text(calls)
    call_count = calls.count("Row:")
    yield "calls", f"  ✓ {call_count} call records → call_log.txt"

    # ── 7. SMS messages ───────────────────────────────────────────────────────
    yield "sms", "💬 [7/17] Extracting SMS messages…"
    rc, sms = _adb(serial, "shell", "content", "query",
                   "--uri", "content://sms",
                   "--projection", "address,date,body,type")
    (out_dir / "sms_messages.txt").write_text(sms)
    sms_count = sms.count("Row:")
    yield "sms", f"  ✓ {sms_count} SMS records → sms_messages.txt"

    # ── 8. Browser history ────────────────────────────────────────────────────
    yield "browser", "🌍 [8/17] Collecting browser history…"
    rc, hist = _adb(serial, "shell", "content", "query",
                    "--uri", "content://browser/bookmarks",
                    "--projection", "url,title,visits,date")
    (out_dir / "browser_history.txt").write_text(hist)
    yield "browser", f"  ✓ browser_history.txt"

    # ── 9. Accounts ───────────────────────────────────────────────────────────
    yield "accounts", "👤 [9/17] Listing device accounts…"
    rc, accts = _adb(serial, "shell", "content", "query",
                     "--uri", "content://com.android.contacts/accounts")
    (out_dir / "accounts.txt").write_text(accts)
    yield "accounts", f"  ✓ accounts.txt"

    # ── 10. APK pull ──────────────────────────────────────────────────────────
    yield "apks", "📲 [10/17] Pulling third-party APKs…"
    apk_dir = out_dir / "apks"
    apk_dir.mkdir(exist_ok=True)
    pulled = 0
    for line in apps_out.splitlines()[:20]:  # limit to 20 to avoid timeouts
        if "=" in line:
            path = line.split("=")[0].replace("package:", "").strip()
            pkg  = line.split("=")[1].strip()
            rc, _ = _run(["adb", "-s", serial, "pull", path,
                          str(apk_dir / f"{pkg}.apk")], timeout=60)
            if rc == 0:
                pulled += 1
    yield "apks", f"  ✓ {pulled} APKs pulled → apks/"

    # ── 11. ALEX logical extraction ───────────────────────────────────────────
    if run_alex:
        yield "alex", "🔍 [11/17] ALEX logical extraction…"
        alex_dir = TOOLS_DIR / "mobile" / "ALEX"
        if (alex_dir / "alex.py").exists():
            alex_out = out_dir / "ALEX_output"
            alex_out.mkdir(exist_ok=True)
            rc, out = _run([_py(alex_dir), "alex.py", "--device", serial,
                            "--output", str(alex_out)],
                           cwd=alex_dir, timeout=900)
            for line in out.splitlines()[-30:]:
                yield "alex", f"  {line}"
            yield "alex", f"  {'✓' if rc == 0 else '⚠'} ALEX {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "alex", "  ⊘ ALEX not installed (run install_tools.sh)"
    else:
        yield "alex", "  [11/17] ALEX — skipped"

    # ── 12. android_triage ────────────────────────────────────────────────────
    if run_triage:
        yield "triage", "🔧 [12/17] android_triage system artifacts…"
        triage_dir = TOOLS_DIR / "mobile" / "android_triage"
        if (triage_dir / "android_triage.sh").exists():
            triage_out = out_dir / "triage_output"
            triage_out.mkdir(exist_ok=True)
            rc, out = _run(["bash", str(triage_dir / "android_triage.sh"),
                            "-s", serial, "-o", str(triage_out)],
                           cwd=triage_dir, timeout=900)
            for line in out.splitlines()[-30:]:
                yield "triage", f"  {line}"
            yield "triage", f"  {'✓' if rc == 0 else '⚠'} android_triage {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "triage", "  ⊘ android_triage not installed"
    else:
        yield "triage", "  [12/17] android_triage — skipped"

    # ── 13. ALEAPP ────────────────────────────────────────────────────────────
    if run_aleapp:
        yield "aleapp", "📊 [13/17] ALEAPP artifact parsing…"
        aleapp_dir = TOOLS_DIR / "mobile" / "ALEAPP"
        if (aleapp_dir / "aleapp.py").exists():
            input_path = (
                out_dir / "ALEX_output" if (out_dir / "ALEX_output").exists() else
                out_dir / "triage_output" if (out_dir / "triage_output").exists() else
                out_dir
            )
            aleapp_out = out_dir / "ALEAPP_report"
            aleapp_out.mkdir(exist_ok=True)
            rc, out = _run([_py(aleapp_dir), "aleapp.py", "-t", "fs",
                            "-i", str(input_path), "-o", str(aleapp_out)],
                           cwd=aleapp_dir, timeout=600)
            for line in out.splitlines()[-30:]:
                yield "aleapp", f"  {line}"
            yield "aleapp", f"  {'✓' if rc == 0 else '⚠'} ALEAPP {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "aleapp", "  ⊘ ALEAPP not installed"
    else:
        yield "aleapp", "  [13/17] ALEAPP — skipped"

    # ── 14. MVT spyware scan ──────────────────────────────────────────────────
    if run_mvt:
        yield "mvt", "🔎 [14/17] MVT (Mobile Verification Toolkit) spyware scan…"
        mvt_dir = TOOLS_DIR / "mobile" / "MVT"
        ioc_file = TOOLS_DIR / "spyware" / "iocs" / "pegasus.stix2"
        if (mvt_dir / "setup.py").exists() or (mvt_dir / "pyproject.toml").exists():
            mvt_out = out_dir / "MVT_output"
            mvt_out.mkdir(exist_ok=True)
            cmd = [_py(mvt_dir), "-m", "mvt", "android", "check-adb",
                   "--serial", serial, "--output", str(mvt_out)]
            if ioc_file.exists():
                cmd += ["--iocs", str(ioc_file)]
            rc, out = _run(cmd, cwd=mvt_dir, timeout=600)
            for line in out.splitlines()[-40:]:
                yield "mvt", f"  {line}"
                if "detected" in line.lower() or "found" in line.lower():
                    findings.append({"severity": "critical",
                                     "title": "MVT: Potential spyware indicator detected",
                                     "description": line, "path": str(mvt_out)})
            yield "mvt", f"  {'✓' if rc == 0 else '⚠'} MVT {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "mvt", "  ⊘ MVT not installed (run install_tools.sh)"

    # ── 15. Stalkerware indicators ────────────────────────────────────────────
    if run_spyware:
        yield "spyware", "🕵️  [15/17] Checking stalkerware indicators…"
        sw_indicators = TOOLS_DIR / "spyware" / "stalkerware-indicators"
        if sw_indicators.exists():
            # Check installed apps against known stalkerware packages
            ioc_files = list(sw_indicators.rglob("*.txt")) + list(sw_indicators.rglob("*.csv"))
            known_stalkerware: set[str] = set()
            for f in ioc_files[:10]:
                try:
                    for line in f.read_text(errors="replace").splitlines():
                        line = line.strip().lower()
                        if line and not line.startswith("#"):
                            known_stalkerware.add(line)
                except Exception:
                    pass
            matches = 0
            for line in apps_out.lower().splitlines():
                for sw in known_stalkerware:
                    if sw in line:
                        matches += 1
                        findings.append({"severity": "critical",
                                         "title": f"Stalkerware package match: {sw}",
                                         "description": f"Installed app matches known stalkerware indicator: {line.strip()}",
                                         "path": str(out_dir / "installed_apps.txt")})
                        yield "spyware", f"  ⚠ STALKERWARE MATCH: {line.strip()}"
            if matches == 0:
                yield "spyware", "  ✓ No known stalkerware packages detected"
            yield "spyware", f"  Checked {len(known_stalkerware)} known indicators"
        else:
            yield "spyware", "  ⊘ Stalkerware indicators not installed (run install_tools.sh)"

    # ── 16. HTML report ───────────────────────────────────────────────────────
    yield "report", "📝 [16/17] Generating HTML forensic report…"
    try:
        from forensicx_hub.report_gen import generate_html_report
        report_path = generate_html_report(
            out_dir=out_dir,
            device_info=device_info,
            findings=findings,
            case_name=f"Android_{device_info.get('model','device')}_{ts}",
            investigator=investigator,
        )
        yield "report", f"  ✓ Report: {report_path}"
        yield "report", f"  ⭢ Open in browser: file://{report_path}"
    except Exception as exc:
        yield "report", f"  ⚠ Report generation failed: {exc}"

    # ── 17. ForensicX case import ─────────────────────────────────────────────
    yield "import", "💾 [17/17] Importing into ForensicX case database…"
    try:
        from forensicx.core import database as db
        case_name = f"Android_{device_info.get('model', serial)}_{ts}"
        case = db.create_case(name=case_name, investigator=investigator,
                              notes=json.dumps(device_info))
        yield "import", f"  ✓ Case #{case.id}: {case.name}"

        from forensicx.services.evidence import import_evidence
        for f in (out_dir / "device_info.json", out_dir / "installed_apps.txt",
                  out_dir / "call_log.txt", out_dir / "sms_messages.txt",
                  out_dir / "processes.txt", out_dir / "network_connections.txt"):
            if f.exists():
                try:
                    ev = import_evidence(case_id=case.id, file_path=f)
                    yield "import", f"  ✓ Evidence #{ev.id}: {f.name}"
                except Exception:
                    pass
    except Exception as exc:
        yield "import", f"  ⚠ DB import error: {exc}"

    yield "done", "═══════════════════════════════════════════════"
    yield "done", f"✅ SCAN COMPLETE"
    yield "done", f"  Output  : {out_dir}"
    yield "done", f"  Findings: {len(findings)}"
    yield "done", f"  Report  : {out_dir}/forensicx_report.html"
    yield "done", "═══════════════════════════════════════════════"


# ─────────────────────────────────────────────────────────────────────────────
# iOS COMPREHENSIVE SCAN
# ─────────────────────────────────────────────────────────────────────────────

def comprehensive_ios_scan(
    case_dir: Path,
    investigator: str = "ForensicX",
    run_ufade: bool = True,
    run_ileapp: bool = True,
    run_mvt: bool = True,
) -> Iterator[Step]:
    """Full authority-grade iOS forensic pipeline."""
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"ios_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    device_info: dict = {}
    findings: list[dict] = []

    yield "init", "═══ ForensicX Comprehensive iOS Scan ═══"
    yield "init", f"Output  : {out_dir}"
    yield "init", f"Started : {ts} UTC"

    # ── 1. ideviceinfo ────────────────────────────────────────────────────────
    yield "device", "📱 [1/6] Collecting iOS device info via libimobiledevice…"
    rc, info_out = _run(["ideviceinfo"], timeout=15)
    if rc == 0:
        (out_dir / "ideviceinfo.txt").write_text(info_out)
        for line in info_out.splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2:
                device_info[parts[0].strip()] = parts[1].strip()
        yield "device", f"  ✓ ideviceinfo.txt ({len(device_info)} properties)"
    else:
        yield "device", f"  ⚠ ideviceinfo failed: {info_out[:80]}"
        yield "device", "    Ensure iTunes/libimobiledevice installed and device trusted"

    # ── 2. App list ───────────────────────────────────────────────────────────
    yield "apps", "📦 [2/6] Enumerating installed apps…"
    rc, apps = _run(["ideviceinstaller", "-l"], timeout=20)
    if rc == 0:
        (out_dir / "installed_apps.txt").write_text(apps)
        yield "apps", f"  ✓ {apps.count(chr(10))} apps → installed_apps.txt"
    else:
        yield "apps", "  ⊘ ideviceinstaller not available"

    # ── 3. UFADE extraction ───────────────────────────────────────────────────
    if run_ufade:
        yield "ufade", "🔍 [3/6] UFADE logical extraction…"
        ufade_dir = TOOLS_DIR / "mobile" / "UFADE"
        if (ufade_dir / "ufade.py").exists():
            ufade_out = out_dir / "UFADE_output"
            ufade_out.mkdir(exist_ok=True)
            rc, out = _run([_py(ufade_dir), "ufade.py", "--output", str(ufade_out)],
                           cwd=ufade_dir, timeout=900)
            for line in out.splitlines()[-30:]:
                yield "ufade", f"  {line}"
            yield "ufade", f"  {'✓' if rc == 0 else '⚠'} UFADE {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "ufade", "  ⊘ UFADE not installed (run install_tools.sh)"

    # ── 4. iLEAPP ─────────────────────────────────────────────────────────────
    if run_ileapp:
        yield "ileapp", "📊 [4/6] iLEAPP artifact parsing…"
        ileapp_dir = TOOLS_DIR / "mobile" / "iLEAPP"
        if (ileapp_dir / "ileapp.py").exists():
            input_path = (out_dir / "UFADE_output" if (out_dir / "UFADE_output").exists()
                          else out_dir)
            ileapp_out = out_dir / "iLEAPP_report"
            ileapp_out.mkdir(exist_ok=True)
            rc, out = _run([_py(ileapp_dir), "ileapp.py", "-t", "fs",
                            "-i", str(input_path), "-o", str(ileapp_out)],
                           cwd=ileapp_dir, timeout=600)
            for line in out.splitlines()[-30:]:
                yield "ileapp", f"  {line}"
            yield "ileapp", f"  {'✓' if rc == 0 else '⚠'} iLEAPP {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "ileapp", "  ⊘ iLEAPP not installed"

    # ── 5. MVT iOS ────────────────────────────────────────────────────────────
    if run_mvt:
        yield "mvt", "🔎 [5/6] MVT iOS spyware scan (Pegasus indicators)…"
        mvt_dir = TOOLS_DIR / "mobile" / "MVT"
        ioc_file = TOOLS_DIR / "spyware" / "iocs" / "pegasus.stix2"
        if (mvt_dir / "setup.py").exists() or (mvt_dir / "pyproject.toml").exists():
            mvt_out = out_dir / "MVT_output"
            mvt_out.mkdir(exist_ok=True)
            cmd = [_py(mvt_dir), "-m", "mvt", "ios", "check-backup",
                   "--output", str(mvt_out)]
            if ioc_file.exists():
                cmd += ["--iocs", str(ioc_file)]
            # Look for iTunes backup
            import os
            home = Path.home()
            backup_paths = [
                home / "Library" / "Application Support" / "MobileSync" / "Backup",
                Path("/var/lib/lockdown"),
            ]
            for bp in backup_paths:
                if bp.exists():
                    cmd += [str(bp)]
                    break
            rc, out = _run(cmd, cwd=mvt_dir, timeout=600)
            for line in out.splitlines()[-40:]:
                yield "mvt", f"  {line}"
                if "detected" in line.lower():
                    findings.append({"severity": "critical",
                                     "title": "MVT iOS: Spyware indicator detected",
                                     "description": line, "path": str(mvt_out)})
            yield "mvt", f"  {'✓' if rc == 0 else '⚠'} MVT iOS {'complete' if rc==0 else f'exited {rc}'}"
        else:
            yield "mvt", "  ⊘ MVT not installed"

    # ── 6. HTML report ────────────────────────────────────────────────────────
    yield "report", "📝 [6/6] Generating forensic report…"
    try:
        from forensicx_hub.report_gen import generate_html_report
        report_path = generate_html_report(
            out_dir=out_dir, device_info=device_info, findings=findings,
            case_name=f"iOS_{ts}", investigator=investigator)
        yield "report", f"  ✓ Report: {report_path}"
        yield "report", f"  ⭢ file://{report_path}"
    except Exception as exc:
        yield "report", f"  ⚠ {exc}"

    yield "done", f"✅ iOS SCAN COMPLETE — {out_dir}"


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY TRIAGE WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────

def memory_triage_workflow(dump_path: Path, case_dir: Path,
                           profile: str = "") -> Iterator[Step]:
    """Run Volatility 3 on a memory dump."""
    vol3_dir = TOOLS_DIR / "memory" / "volatility3"
    if not (vol3_dir / "vol.py").exists():
        yield "error", "Volatility 3 not installed — run scripts/install_tools.sh"
        return

    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"memory_{dump_path.stem}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    yield "init", f"═══ ForensicX Memory Analysis ═══"
    yield "init", f"Dump : {dump_path}"
    yield "init", f"Out  : {out_dir}"

    plugins = [
        "windows.pslist", "windows.pstree", "windows.cmdline",
        "windows.netscan", "windows.malfind", "windows.dlllist",
        "windows.handles", "windows.filescan", "windows.hashdump",
        "windows.svcscan", "windows.registry.hivelist",
    ]

    py = _py(vol3_dir)
    total = len(plugins)
    for i, plugin in enumerate(plugins, 1):
        yield "volatility", f"[{i}/{total}] {plugin}…"
        out_file = out_dir / f"{plugin.replace('.','_')}.txt"
        rc, out = _run([py, str(vol3_dir / "vol.py"), "-f", str(dump_path), plugin],
                       timeout=300)
        out_file.write_text(out)
        lines = out.splitlines()
        for line in lines[:5]:
            yield "volatility", f"  {line}"
        if len(lines) > 5:
            yield "volatility", f"  … {len(lines)} lines → {out_file.name}"

    # HTML report
    yield "report", "Generating report…"
    try:
        from forensicx_hub.report_gen import generate_html_report
        report_path = generate_html_report(
            out_dir=out_dir, device_info={"dump": str(dump_path)},
            findings=[], case_name=f"Memory_{dump_path.stem}")
        yield "report", f"  ✓ {report_path}"
    except Exception:
        pass

    yield "done", f"✅ Memory analysis complete — {out_dir}"


# ─────────────────────────────────────────────────────────────────────────────
# QUICK SPYWARE SCAN (standalone)
# ─────────────────────────────────────────────────────────────────────────────

def quick_spyware_scan(serial: str, case_dir: Path) -> Iterator[Step]:
    """Fast spyware-only scan — runs in ~30 seconds."""
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"spyware_{serial}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    yield "spyware", "🕵️  Quick Spyware Scan started…"

    rc, apps_out = _adb(serial, "shell", "pm", "list", "packages", "-f", "-3")
    (out_dir / "packages.txt").write_text(apps_out)

    suspicious = []
    keywords = ("spy", "track", "monitor", "keylog", "surv", "stalker",
                 "hoverwatch", "mspy", "flexispy", "spyera", "cerberus")
    for line in apps_out.splitlines():
        pkg = line.split("=")[-1].strip()
        if any(k in pkg.lower() for k in keywords):
            suspicious.append(pkg)
            yield "spyware", f"  ⚠ SUSPICIOUS: {pkg}"

    if not suspicious:
        yield "spyware", "  ✓ No obviously suspicious packages detected"

    # Check for common spyware behaviors via ADB
    yield "spyware", "Checking device admin apps…"
    rc, admins = _adb(serial, "shell", "dumpsys", "device_policy")
    if "admin" in admins.lower():
        (out_dir / "device_admins.txt").write_text(admins)
        yield "spyware", f"  ⚠ Device admin entries found — see device_admins.txt"

    yield "spyware", "Checking running services…"
    rc, svc = _adb(serial, "shell", "dumpsys", "activity", "services")
    (out_dir / "services.txt").write_text(svc)
    for line in svc.splitlines():
        if any(k in line.lower() for k in keywords):
            yield "spyware", f"  ⚠ Suspicious service: {line.strip()[:80]}"

    yield "done", f"✅ Quick spyware scan done — {out_dir}"
    yield "done", f"  Suspicious packages: {len(suspicious)}"


# ─────────────────────────────────────────────────────────────────────────────
# Legacy aliases (keep existing callers working)
# ─────────────────────────────────────────────────────────────────────────────

def android_triage_workflow(serial: str, case_dir: Path,
                             run_alex: bool = True, run_triage: bool = True,
                             run_aleapp: bool = True) -> Iterator[Step]:
    yield from comprehensive_android_scan(
        serial=serial, case_dir=case_dir,
        run_alex=run_alex, run_triage=run_triage, run_aleapp=run_aleapp,
    )


def ios_triage_workflow(case_dir: Path) -> Iterator[Step]:
    yield from comprehensive_ios_scan(case_dir=case_dir)
