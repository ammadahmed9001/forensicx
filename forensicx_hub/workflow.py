"""
Automated forensic triage workflows.

Each workflow is a generator that yields (step_name, log_line) tuples
so the GUI can stream progress in real time.
"""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Generator, Iterator

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

Step = tuple[str, str]   # (step_name, message)


def _run(cmd: list[str], cwd: Path | None = None,
         env: dict | None = None, timeout: int = 300) -> tuple[int, str]:
    """Run a command, return (returncode, combined output)."""
    import os
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=cwd, env=full_env, timeout=timeout
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "Timed out"
    except Exception as exc:
        return -1, str(exc)


def _py(tool_dir: Path) -> str:
    venv = tool_dir / ".venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


# ──────────────────────────────────────────────────────────────────────────────
# ANDROID TRIAGE WORKFLOW
# ──────────────────────────────────────────────────────────────────────────────

def android_triage_workflow(
    serial: str,
    case_dir: Path,
    run_alex: bool = True,
    run_triage: bool = True,
    run_aleapp: bool = True,
) -> Iterator[Step]:
    """
    Full Android triage pipeline:
      1. Device info snapshot
      2. ALEX logical extraction  (optional)
      3. android_triage           (optional)
      4. ALEAPP artifact parsing  (optional)
      5. ForensicX case import
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"android_{serial}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    yield "init", f"Output directory: {out_dir}"

    # ── 1. device snapshot ────────────────────────────────────────────────────
    yield "device_info", "Collecting device info via ADB…"
    props = {
        "model":   "ro.product.model",
        "mfr":     "ro.product.manufacturer",
        "android": "ro.build.version.release",
        "sdk":     "ro.build.version.sdk",
        "build":   "ro.build.display.id",
        "serial":  "ro.serialno",
        "imei":    "persist.radio.imei",
    }
    info: dict[str, str] = {}
    for key, prop in props.items():
        rc, out = _run(["adb", "-s", serial, "shell", "getprop", prop])
        info[key] = out.strip()
        yield "device_info", f"  {key}: {info[key]}"

    (out_dir / "device_info.json").write_text(json.dumps(info, indent=2))

    # ADB bugreport for system logs
    yield "device_info", "Running adb bugreport (this may take a minute)…"
    rc, out = _run(["adb", "-s", serial, "bugreport", str(out_dir / "bugreport.zip")], timeout=180)
    if rc == 0:
        yield "device_info", "bugreport saved."
    else:
        yield "device_info", f"bugreport failed (non-fatal): {out[:200]}"

    # ── 2. ALEX logical extraction ────────────────────────────────────────────
    if run_alex:
        alex_dir = TOOLS_DIR / "mobile" / "ALEX"
        if not (alex_dir / "alex.py").exists():
            yield "alex", "ALEX not installed — skipping. Run scripts/install_tools.sh first."
        else:
            alex_out = out_dir / "ALEX_output"
            alex_out.mkdir(exist_ok=True)
            yield "alex", f"Running ALEX on device {serial}…"
            yield "alex", f"Output: {alex_out}"
            rc, out = _run(
                [_py(alex_dir), "alex.py", "--device", serial, "--output", str(alex_out)],
                cwd=alex_dir,
                timeout=600,
            )
            for line in out.splitlines()[-40:]:
                yield "alex", line
            if rc == 0:
                yield "alex", "ALEX extraction complete."
            else:
                yield "alex", f"ALEX exited with code {rc} (check output above)."

    # ── 3. android_triage ─────────────────────────────────────────────────────
    if run_triage:
        triage_dir = TOOLS_DIR / "mobile" / "android_triage"
        if not (triage_dir / "android_triage.sh").exists():
            yield "triage", "android_triage not installed — skipping."
        else:
            triage_out = out_dir / "triage_output"
            triage_out.mkdir(exist_ok=True)
            yield "triage", f"Running android_triage on {serial}…"
            rc, out = _run(
                ["bash", str(triage_dir / "android_triage.sh"),
                 "-s", serial, "-o", str(triage_out)],
                cwd=triage_dir,
                timeout=600,
            )
            for line in out.splitlines()[-40:]:
                yield "triage", line
            if rc == 0:
                yield "triage", "android_triage complete."
            else:
                yield "triage", f"android_triage exited {rc}."

    # ── 4. ALEAPP ─────────────────────────────────────────────────────────────
    if run_aleapp:
        aleapp_dir = TOOLS_DIR / "mobile" / "ALEAPP"
        if not (aleapp_dir / "aleapp.py").exists():
            yield "aleapp", "ALEAPP not installed — skipping."
        else:
            # Find input: prefer ALEX output, fall back to triage output, fallback to out_dir
            input_path = (
                out_dir / "ALEX_output" if (out_dir / "ALEX_output").exists() else
                out_dir / "triage_output" if (out_dir / "triage_output").exists() else
                out_dir
            )
            aleapp_out = out_dir / "ALEAPP_report"
            aleapp_out.mkdir(exist_ok=True)
            yield "aleapp", f"Running ALEAPP on {input_path}…"
            rc, out = _run(
                [_py(aleapp_dir), "aleapp.py", "-t", "fs",
                 "-i", str(input_path), "-o", str(aleapp_out)],
                cwd=aleapp_dir,
                timeout=600,
            )
            for line in out.splitlines()[-40:]:
                yield "aleapp", line
            if rc == 0:
                yield "aleapp", f"ALEAPP report: {aleapp_out}"
            else:
                yield "aleapp", f"ALEAPP exited {rc}."

    # ── 5. ForensicX case import ───────────────────────────────────────────────
    yield "import", "Importing evidence into ForensicX case database…"
    try:
        from forensicx.core import database as db
        case_name = f"Android_{info.get('model', serial)}_{ts}"
        case = db.create_case(
            name=case_name,
            investigator="ForensicX Auto-Triage",
            notes=json.dumps(info),
        )
        yield "import", f"Case created: #{case.id}  {case.name}"

        # Import device_info.json
        from forensicx.services.evidence import import_evidence
        ev = import_evidence(case_id=case.id, file_path=out_dir / "device_info.json")
        yield "import", f"Evidence #{ev.id}: device_info.json  sha256={ev.sha256[:16]}…"

        # Import any .zip / .tar.gz output from ALEAPP report
        for f in out_dir.rglob("*.json"):
            if f.name == "device_info.json":
                continue
            try:
                ev2 = import_evidence(case_id=case.id, file_path=f)
                yield "import", f"Evidence #{ev2.id}: {f.name}"
            except Exception:
                pass

        yield "import", f"ForensicX case #{case.id} ready. Run: forensicx search {case.id} <query>"
    except Exception as exc:
        yield "import", f"ForensicX import error: {exc}"

    yield "done", f"Triage complete. All output in: {out_dir}"


# ──────────────────────────────────────────────────────────────────────────────
# iOS TRIAGE WORKFLOW
# ──────────────────────────────────────────────────────────────────────────────

def ios_triage_workflow(case_dir: Path) -> Iterator[Step]:
    """
    iOS triage using UFADE → iLEAPP → ForensicX case.
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = case_dir / f"ios_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    yield "init", f"iOS triage output: {out_dir}"

    # ── libimobiledevice device info ──────────────────────────────────────────
    yield "device_info", "Checking iOS device via ideviceinfo…"
    rc, out = _run(["ideviceinfo"], timeout=10)
    if rc == 0:
        (out_dir / "ideviceinfo.txt").write_text(out)
        yield "device_info", f"Device info saved ({len(out)} chars)"
    else:
        yield "device_info", f"ideviceinfo failed: {out[:200]}"

    # ── UFADE extraction ──────────────────────────────────────────────────────
    ufade_dir = TOOLS_DIR / "mobile" / "UFADE"
    if (ufade_dir / "ufade.py").exists():
        ufade_out = out_dir / "UFADE_output"
        ufade_out.mkdir(exist_ok=True)
        yield "ufade", "Running UFADE…"
        rc, out = _run(
            [_py(ufade_dir), "ufade.py", "--output", str(ufade_out)],
            cwd=ufade_dir,
            timeout=600,
        )
        for line in out.splitlines()[-40:]:
            yield "ufade", line
    else:
        yield "ufade", "UFADE not installed — run scripts/install_tools.sh"

    # ── iLEAPP parsing ────────────────────────────────────────────────────────
    ileapp_dir = TOOLS_DIR / "mobile" / "iLEAPP"
    if (ileapp_dir / "ileapp.py").exists():
        ileapp_out = out_dir / "iLEAPP_report"
        ileapp_out.mkdir(exist_ok=True)
        input_path = out_dir / "UFADE_output" if (out_dir / "UFADE_output").exists() else out_dir
        yield "ileapp", f"Running iLEAPP on {input_path}…"
        rc, out = _run(
            [_py(ileapp_dir), "ileapp.py", "-t", "fs",
             "-i", str(input_path), "-o", str(ileapp_out)],
            cwd=ileapp_dir,
            timeout=600,
        )
        for line in out.splitlines()[-40:]:
            yield "ileapp", line
    else:
        yield "ileapp", "iLEAPP not installed."

    yield "done", f"iOS triage complete. Output: {out_dir}"


# ──────────────────────────────────────────────────────────────────────────────
# MEMORY TRIAGE WORKFLOW
# ──────────────────────────────────────────────────────────────────────────────

def memory_triage_workflow(dump_path: Path, case_dir: Path,
                            profile: str = "") -> Iterator[Step]:
    """Run Volatility 3 on a memory dump."""
    vol3_dir = TOOLS_DIR / "memory" / "volatility3"
    if not (vol3_dir / "vol.py").exists():
        yield "error", "Volatility 3 not installed. Run scripts/install_tools.sh"
        return

    out_dir = case_dir / f"memory_analysis_{dump_path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    plugins = [
        "windows.pslist",
        "windows.pstree",
        "windows.cmdline",
        "windows.netscan",
        "windows.malfind",
        "windows.dlllist",
        "windows.handles",
    ]

    py = _py(vol3_dir)
    for plugin in plugins:
        yield "volatility", f"Running {plugin}…"
        out_file = out_dir / f"{plugin.replace('.', '_')}.txt"
        rc, out = _run(
            [py, str(vol3_dir / "vol.py"), "-f", str(dump_path), plugin],
            timeout=300,
        )
        out_file.write_text(out)
        lines = out.splitlines()
        for line in lines[:5]:
            yield "volatility", f"  {line}"
        if len(lines) > 5:
            yield "volatility", f"  … ({len(lines)} lines) → {out_file.name}"

    yield "done", f"Memory analysis complete. Results: {out_dir}"
