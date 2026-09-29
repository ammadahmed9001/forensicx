"""
ForensicX Professional Web Dashboard
Authority-grade DFIR platform — open-source, chain-of-custody compliant.

Launch: python3 -m forensicx_hub.web_app   (opens browser automatically)
"""
from __future__ import annotations

import datetime
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template_string, request, stream_with_context

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)

# ── Global broadcast queue for SSE ────────────────────────────────────────────
_sse_listeners: list[queue.Queue[str]] = []
_sse_lock = threading.Lock()

def _broadcast(event: str, data: dict) -> None:
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_listeners:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_listeners.remove(q)

# ── Device monitor ─────────────────────────────────────────────────────────────
_device_monitor = None

def _start_monitor() -> None:
    global _device_monitor
    try:
        from forensicx_hub.device_monitor import DeviceMonitor
        _device_monitor = DeviceMonitor(interval=4.0)
        _device_monitor.on_attach(lambda d: _broadcast("device_attach", {
            "serial": d.serial, "model": d.model,
            "manufacturer": d.manufacturer, "android": d.android_version,
            "state": d.state
        }))
        _device_monitor.on_detach(lambda s: _broadcast("device_detach", {"serial": s}))
        _device_monitor.start()
    except Exception:
        pass

threading.Thread(target=_start_monitor, daemon=True).start()

# ── DB helpers ─────────────────────────────────────────────────────────────────
def _db_cases() -> list[dict]:
    try:
        from forensicx.core import database as db
        return [c.to_dict() for c in db.list_cases()]
    except Exception:
        return []

def _db_create_case(name: str, investigator: str, notes: str) -> dict | None:
    try:
        from forensicx.core import database as db
        c = db.create_case(name=name, investigator=investigator, notes=notes)
        return c.to_dict()
    except Exception:
        return None

def _db_evidence(case_id: int) -> list[dict]:
    try:
        from forensicx.core import database as db
        return [e.to_dict() for e in db.list_evidence(case_id=case_id)]
    except Exception:
        return []

def _db_search(query: str) -> list[dict]:
    try:
        from forensicx.core import database as db
        return [a.to_dict() for a in db.search_artifacts(query)]
    except Exception:
        return []

# ── Tool registry ──────────────────────────────────────────────────────────────
def _tools_summary() -> dict:
    try:
        from forensicx_hub.tools_registry import ALL_TOOLS, CATEGORIES
        total = len(ALL_TOOLS)
        installed = sum(1 for t in ALL_TOOLS if t.is_installed)
        cats = {k: {"total": len(v), "installed": sum(1 for t in v if t.is_installed)}
                for k, v in CATEGORIES.items()}
        return {"total": total, "installed": installed, "categories": cats}
    except Exception:
        return {"total": 0, "installed": 0, "categories": {}}

def _tools_list() -> list[dict]:
    try:
        from forensicx_hub.tools_registry import ALL_TOOLS
        return [{
            "name": t.name, "category": t.category,
            "description": t.description, "license": t.license,
            "author": t.author, "repo_url": t.repo_url,
            "installed": t.is_installed, "install_type": t.install_type,
            "notes": t.notes or "",
        } for t in ALL_TOOLS]
    except Exception:
        return []

# ── SSE endpoint ───────────────────────────────────────────────────────────────
@app.route("/stream")
def stream() -> Response:
    q: queue.Queue[str] = queue.Queue(maxsize=50)
    with _sse_lock:
        _sse_listeners.append(q)

    def gen():
        yield "event: connected\ndata: {}\n\n"
        while True:
            try:
                msg = q.get(timeout=25)
                yield msg
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(stream_with_context(gen()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── API endpoints ──────────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats() -> Response:
    cases = _db_cases()
    ts = _tools_summary()
    devs = []
    if _device_monitor:
        devs = [{"serial": d.serial, "model": d.model,
                 "manufacturer": d.manufacturer,
                 "android": d.android_version, "state": d.state}
                for d in _device_monitor.devices]
    return jsonify({
        "cases": len(cases),
        "evidence": sum(len(_db_evidence(c["id"])) for c in cases[:20]),
        "tools_installed": ts["installed"],
        "tools_total": ts["total"],
        "devices": len(devs),
        "device_list": devs,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    })

@app.route("/api/cases", methods=["GET"])
def api_cases() -> Response:
    return jsonify(_db_cases())

@app.route("/api/cases", methods=["POST"])
def api_create_case() -> Response:
    body = request.get_json(force=True) or {}
    case = _db_create_case(
        name=body.get("name", "Untitled Case"),
        investigator=body.get("investigator", "Unknown"),
        notes=body.get("notes", ""),
    )
    if case:
        _broadcast("case_created", case)
        return jsonify(case), 201
    return jsonify({"error": "DB not initialised"}), 500

@app.route("/api/cases/<int:case_id>/evidence")
def api_evidence(case_id: int) -> Response:
    return jsonify(_db_evidence(case_id))

@app.route("/api/tools")
def api_tools() -> Response:
    return jsonify(_tools_list())

@app.route("/api/tools/summary")
def api_tools_summary() -> Response:
    return jsonify(_tools_summary())

@app.route("/api/search")
def api_search() -> Response:
    q = request.args.get("q", "")
    if not q:
        return jsonify([])
    return jsonify(_db_search(q))

@app.route("/api/devices")
def api_devices() -> Response:
    devs = []
    if _device_monitor:
        devs = [{"serial": d.serial, "model": d.model,
                 "manufacturer": d.manufacturer, "android": d.android_version,
                 "sdk": d.sdk_version, "state": d.state,
                 "display_name": d.display_name}
                for d in _device_monitor.devices]
    return jsonify(devs)

@app.route("/api/triage/android", methods=["POST"])
def api_triage_android() -> Response:
    body = request.get_json(force=True) or {}
    serial = body.get("serial", "")
    case_dir = Path(body.get("case_dir", str(ROOT / "cases")))
    if not serial:
        return jsonify({"error": "serial required"}), 400

    def run():
        try:
            from forensicx_hub.workflow import android_triage_workflow
            for step, msg in android_triage_workflow(serial=serial, case_dir=case_dir):
                _broadcast("triage_log", {"step": step, "msg": msg, "serial": serial})
            _broadcast("triage_done", {"serial": serial})
        except Exception as exc:
            _broadcast("triage_log", {"step": "error", "msg": str(exc), "serial": serial})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started", "serial": serial})

@app.route("/api/triage/ios", methods=["POST"])
def api_triage_ios() -> Response:
    body = request.get_json(force=True) or {}
    case_dir = Path(body.get("case_dir", str(ROOT / "cases")))

    def run():
        try:
            from forensicx_hub.workflow import ios_triage_workflow
            for step, msg in ios_triage_workflow(case_dir=case_dir):
                _broadcast("triage_log", {"step": step, "msg": msg, "serial": "ios"})
            _broadcast("triage_done", {"serial": "ios"})
        except Exception as exc:
            _broadcast("triage_log", {"step": "error", "msg": str(exc), "serial": "ios"})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/api/memory/analyze", methods=["POST"])
def api_memory() -> Response:
    body = request.get_json(force=True) or {}
    dump = body.get("dump_path", "")
    case_dir = Path(body.get("case_dir", str(ROOT / "cases")))
    if not dump:
        return jsonify({"error": "dump_path required"}), 400

    def run():
        try:
            from forensicx_hub.workflow import memory_triage_workflow
            for step, msg in memory_triage_workflow(Path(dump), case_dir):
                _broadcast("triage_log", {"step": step, "msg": msg, "serial": "memory"})
            _broadcast("triage_done", {"serial": "memory"})
        except Exception as exc:
            _broadcast("triage_log", {"step": "error", "msg": str(exc), "serial": "memory"})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started", "dump": dump})

@app.route("/api/report/<int:case_id>")
def api_report(case_id: int) -> Response:
    cases = [c for c in _db_cases() if c["id"] == case_id]
    if not cases:
        return jsonify({"error": "case not found"}), 404
    case = cases[0]
    evidence = _db_evidence(case_id)
    report = {
        "report_type": "ForensicX Case Report",
        "generated": datetime.datetime.utcnow().isoformat() + "Z",
        "forensicx_version": "0.2.0",
        "case": case,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "chain_of_custody": f"Report generated by ForensicX. All evidence hashes verified at import.",
    }
    return jsonify(report)

# ── Main SPA page ──────────────────────────────────────────────────────────────
@app.route("/")
def index() -> str:
    return render_template_string(DASHBOARD_HTML)

# ─────────────────────────────────────────────────────────────────────────────
# HTML / CSS / JS  — Professional DFIR Dashboard
# ─────────────────────────────────────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForensicX — Professional DFIR Platform</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
/* ── Reset & tokens ────────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:       #080c14;
  --surface:  #0d1220;
  --surface2: #111827;
  --surface3: #1a2235;
  --border:   #1e2d42;
  --border2:  #253348;
  --blue:     #3b82f6;
  --blue-l:   #60a5fa;
  --cyan:     #06b6d4;
  --green:    #10b981;
  --red:      #ef4444;
  --amber:    #f59e0b;
  --purple:   #8b5cf6;
  --pink:     #ec4899;
  --text:     #e2e8f0;
  --text2:    #94a3b8;
  --text3:    #64748b;
  --glow-b:   0 0 20px rgba(59,130,246,.35);
  --glow-g:   0 0 20px rgba(16,185,129,.35);
  --glow-r:   0 0 20px rgba(239,68,68,.35);
  --glow-p:   0 0 20px rgba(139,92,246,.35);
  --radius:   10px;
  --radius-sm:6px;
  --sidebar-w:260px;
  --header-h: 62px;
  --transition:.18s ease;
}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:14px;line-height:1.5}
a{color:var(--blue-l);text-decoration:none}
button{font-family:inherit;cursor:pointer}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--surface)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}

/* ── Layout ────────────────────────────────────────────────────────────────── */
#shell{display:grid;grid-template-columns:var(--sidebar-w) 1fr;grid-template-rows:var(--header-h) 1fr;height:100vh}
#header{grid-column:1/-1;grid-row:1;display:flex;align-items:center;gap:16px;padding:0 20px;background:var(--surface);border-bottom:1px solid var(--border);z-index:100;position:relative}
#header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--blue),transparent)}
#sidebar{grid-row:2;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;overflow-x:hidden}
#main{grid-row:2;overflow-y:auto;padding:24px;background:var(--bg)}

/* ── Logo ──────────────────────────────────────────────────────────────────── */
.logo{display:flex;align-items:center;gap:10px;user-select:none}
.logo-icon{width:34px;height:34px;background:linear-gradient(135deg,var(--blue),var(--purple));border-radius:8px;display:grid;place-items:center;font-size:16px;box-shadow:var(--glow-b)}
.logo-text{font-weight:700;font-size:17px;letter-spacing:.5px}
.logo-text span{color:var(--blue-l)}

/* ── Header badges ─────────────────────────────────────────────────────────── */
.hdr-sep{flex:1}
.hdr-badge{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:500;background:var(--surface2);border:1px solid var(--border);white-space:nowrap}
.hdr-badge .dot{width:7px;height:7px;border-radius:50%;animation:pulse 2s infinite}
.dot-green{background:var(--green);box-shadow:0 0 6px var(--green)}
.dot-red{background:var(--red)}
.dot-amber{background:var(--amber)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
#status-text{font-size:12px;color:var(--text2)}
.hdr-time{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text3)}

/* ── Sidebar nav ───────────────────────────────────────────────────────────── */
.nav-section{padding:12px 12px 4px;font-size:10px;font-weight:600;letter-spacing:1.2px;color:var(--text3);text-transform:uppercase}
.nav-item{display:flex;align-items:center;gap:11px;padding:9px 14px;margin:1px 8px;border-radius:var(--radius-sm);cursor:pointer;color:var(--text2);font-size:13px;font-weight:500;transition:var(--transition);position:relative}
.nav-item:hover{background:var(--surface2);color:var(--text)}
.nav-item.active{background:linear-gradient(90deg,rgba(59,130,246,.15),transparent);color:var(--blue-l);border-left:3px solid var(--blue)}
.nav-item .nav-icon{width:18px;text-align:center;font-size:14px}
.nav-badge{margin-left:auto;background:var(--blue);color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px;min-width:18px;text-align:center}
.nav-badge.red{background:var(--red)}
.nav-badge.green{background:var(--green)}
.sidebar-footer{margin-top:auto;padding:14px;border-top:1px solid var(--border);font-size:11px;color:var(--text3)}

/* ── Cards ─────────────────────────────────────────────────────────────────── */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border)}
.card-head h3{font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px}
.card-body{padding:18px}

/* ── Stat tiles ────────────────────────────────────────────────────────────── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px}
.stat-tile{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px;position:relative;overflow:hidden;transition:var(--transition)}
.stat-tile:hover{border-color:var(--border2);transform:translateY(-1px)}
.stat-tile::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.tile-blue::before{background:linear-gradient(90deg,var(--blue),var(--cyan))}
.tile-green::before{background:linear-gradient(90deg,var(--green),#34d399)}
.tile-purple::before{background:linear-gradient(90deg,var(--purple),var(--pink))}
.tile-amber::before{background:linear-gradient(90deg,var(--amber),#fbbf24)}
.tile-cyan::before{background:linear-gradient(90deg,var(--cyan),var(--blue))}
.stat-label{font-size:11px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.stat-val{font-size:32px;font-weight:700;line-height:1;margin-bottom:4px}
.stat-sub{font-size:12px;color:var(--text3);display:flex;align-items:center;gap:5px}
.stat-icon{position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:36px;opacity:.08}

/* ── Buttons ────────────────────────────────────────────────────────────────── */
.btn{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;border:none;transition:var(--transition)}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover{background:#2563eb;box-shadow:var(--glow-b)}
.btn-success{background:var(--green);color:#fff}
.btn-success:hover{background:#059669;box-shadow:var(--glow-g)}
.btn-danger{background:var(--red);color:#fff}
.btn-danger:hover{background:#dc2626;box-shadow:var(--glow-r)}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{background:var(--surface2);color:var(--text);border-color:var(--border2)}
.btn-sm{padding:5px 10px;font-size:12px}
.btn-purple{background:var(--purple);color:#fff}
.btn-purple:hover{background:#7c3aed;box-shadow:var(--glow-p)}
.btn:disabled{opacity:.4;cursor:not-allowed}

/* ── Tables ─────────────────────────────────────────────────────────────────── */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:var(--text3);padding:10px 14px;text-align:left;border-bottom:1px solid var(--border);background:var(--surface2)}
td{padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;color:var(--text2);vertical-align:middle}
tr:hover td{background:rgba(255,255,255,.02)}
.mono{font-family:'JetBrains Mono',monospace;font-size:12px}

/* ── Badges ─────────────────────────────────────────────────────────────────── */
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge-green{background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3)}
.badge-red{background:rgba(239,68,68,.12);color:#f87171;border:1px solid rgba(239,68,68,.25)}
.badge-blue{background:rgba(59,130,246,.12);color:var(--blue-l);border:1px solid rgba(59,130,246,.25)}
.badge-amber{background:rgba(245,158,11,.12);color:#fbbf24;border:1px solid rgba(245,158,11,.25)}
.badge-purple{background:rgba(139,92,246,.12);color:#a78bfa;border:1px solid rgba(139,92,246,.25)}
.badge-gray{background:rgba(100,116,139,.12);color:var(--text3);border:1px solid rgba(100,116,139,.2)}

/* ── Log / terminal ─────────────────────────────────────────────────────────── */
.log-box{background:#060a0f;border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;height:300px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7}
.log-line{padding:1px 0;border-bottom:1px solid rgba(255,255,255,.03)}
.log-line .step{color:var(--text3);margin-right:8px;font-size:11px}
.log-ok   .step,.log-ok   .msg{color:var(--green)}
.log-err  .step,.log-err  .msg{color:var(--red)}
.log-info .msg{color:var(--text2)}
.log-warn .msg{color:var(--amber)}

/* ── Forms ──────────────────────────────────────────────────────────────────── */
.field{margin-bottom:14px}
label{display:block;font-size:12px;font-weight:500;color:var(--text2);margin-bottom:5px}
input[type=text],input[type=file],select,textarea{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px 12px;color:var(--text);font-family:inherit;font-size:13px;outline:none;transition:var(--transition)}
input:focus,select:focus,textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(59,130,246,.12)}
textarea{resize:vertical;min-height:80px}

/* ── Progress bar ────────────────────────────────────────────────────────────── */
.progress-wrap{background:var(--surface2);border-radius:10px;height:6px;overflow:hidden;margin:8px 0}
.progress-bar{height:100%;border-radius:10px;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width .4s ease;position:relative}
.progress-bar::after{content:'';position:absolute;top:0;right:0;bottom:0;width:40px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.3));animation:shimmer 1.5s infinite}
@keyframes shimmer{0%{transform:translateX(-40px)}100%{transform:translateX(40px)}}

/* ── Device card ─────────────────────────────────────────────────────────────── */
.device-card{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;display:flex;align-items:center;gap:14px;transition:var(--transition);cursor:pointer}
.device-card:hover,.device-card.selected{border-color:var(--blue);background:rgba(59,130,246,.06)}
.device-card.selected{box-shadow:0 0 0 2px rgba(59,130,246,.3)}
.device-icon{width:40px;height:40px;background:linear-gradient(135deg,var(--blue),var(--purple));border-radius:8px;display:grid;place-items:center;font-size:18px;flex-shrink:0}
.device-info{flex:1;min-width:0}
.device-name{font-weight:600;font-size:13px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.device-serial{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text3)}

/* ── Notification toasts ──────────────────────────────────────────────────────── */
#toasts{position:fixed;bottom:20px;right:20px;display:flex;flex-direction:column;gap:8px;z-index:1000;pointer-events:none}
.toast{display:flex;align-items:center;gap:10px;padding:10px 16px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,.5);pointer-events:auto;animation:slideIn .25s ease;min-width:280px;max-width:400px}
.toast-success{background:#064e3b;border:1px solid var(--green);color:var(--green)}
.toast-error  {background:#450a0a;border:1px solid var(--red);color:#f87171}
.toast-info   {background:#1e3a5f;border:1px solid var(--blue);color:var(--blue-l)}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* ── Page sections ───────────────────────────────────────────────────────────── */
.page{display:none}.page.active{display:block}
.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.page-title{font-size:20px;font-weight:700;display:flex;align-items:center;gap:10px}
.page-title .icon{width:36px;height:36px;border-radius:8px;display:grid;place-items:center;font-size:16px}

/* ── Grid helpers ─────────────────────────────────────────────────────────────── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.gap-16{gap:16px}
.mb-4{margin-bottom:4px}.mb-8{margin-bottom:8px}.mb-16{margin-bottom:16px}.mb-20{margin-bottom:20px}
.flex{display:flex}.items-center{align-items:center}.gap-8{gap:8px}.gap-12{gap:12px}.gap-16{gap:16px}
.ml-auto{margin-left:auto}.text-right{text-align:right}.w-full{width:100%}
.text-xs{font-size:11px}.text-sm{font-size:12px}.text-muted{color:var(--text3)}
.font-mono{font-family:'JetBrains Mono',monospace;font-size:12px}

/* ── Scan animation ──────────────────────────────────────────────────────────── */
@keyframes scan{0%{background-position:0 -200%}100%{background-position:0 400%}}
.scan-effect{background:linear-gradient(0deg,transparent 40%,rgba(59,130,246,.05) 50%,transparent 60%);background-size:100% 300%;animation:scan 4s linear infinite}

/* ── Hex grid background (decorative) ────────────────────────────────────────── */
#bg-canvas{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;opacity:.035;z-index:0}
#shell{position:relative;z-index:1}

/* ── Tool search ─────────────────────────────────────────────────────────────── */
.search-bar{position:relative;margin-bottom:16px}
.search-bar i{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--text3)}
.search-bar input{padding-left:34px;background:var(--surface2)}
.cat-filter{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.cat-chip{padding:3px 10px;border-radius:14px;font-size:11px;font-weight:600;border:1px solid var(--border);color:var(--text3);cursor:pointer;transition:var(--transition)}
.cat-chip:hover,.cat-chip.active{background:var(--blue);color:#fff;border-color:var(--blue)}

/* ── Chain-of-custody strip ──────────────────────────────────────────────────── */
.coc-strip{background:linear-gradient(90deg,rgba(16,185,129,.08),rgba(59,130,246,.08));border:1px solid rgba(16,185,129,.2);border-radius:var(--radius-sm);padding:8px 14px;font-size:11px;color:var(--text2);display:flex;align-items:center;gap:8px;margin-bottom:16px}

/* ── Timeline ─────────────────────────────────────────────────────────────────── */
.timeline{position:relative;padding-left:22px}
.timeline::before{content:'';position:absolute;left:7px;top:8px;bottom:8px;width:2px;background:var(--border)}
.tl-item{position:relative;margin-bottom:14px}
.tl-dot{position:absolute;left:-19px;top:4px;width:10px;height:10px;border-radius:50%;background:var(--blue);border:2px solid var(--bg);box-shadow:0 0 6px var(--blue)}
.tl-dot.green{background:var(--green);box-shadow:0 0 6px var(--green)}
.tl-dot.red  {background:var(--red);box-shadow:0 0 6px var(--red)}
.tl-dot.amber{background:var(--amber);box-shadow:0 0 6px var(--amber)}
.tl-time{font-size:11px;color:var(--text3);margin-bottom:2px}
.tl-text{font-size:13px;color:var(--text2)}

/* ── Modal ────────────────────────────────────────────────────────────────────── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;display:none;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-overlay.open{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);width:min(500px,90vw);max-height:85vh;overflow-y:auto}
.modal-head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)}
.modal-head h3{font-size:15px;font-weight:600}
.modal-body{padding:20px}
.modal-foot{padding:14px 20px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:8px}

/* ── Donut chart wrapper ──────────────────────────────────────────────────────── */
.chart-wrap{position:relative;height:200px;display:flex;align-items:center;justify-content:center}

/* ── RESPONSIVE ────────────────────────────────────────────────────────────────── */
@media(max-width:900px){
  :root{--sidebar-w:54px}
  .nav-item span,.nav-section,.logo-text,.sidebar-footer,.nav-badge{display:none}
  .nav-item{padding:10px;justify-content:center;margin:2px 4px}
  .nav-item.active{border-left:none;border-bottom:2px solid var(--blue)}
  .grid-2,.grid-3{grid-template-columns:1fr}
}
</style>
</head>
<body>
<canvas id="bg-canvas"></canvas>

<div id="shell">
<!-- ── HEADER ─────────────────────────────────────────────────────────────── -->
<header id="header">
  <div class="logo">
    <div class="logo-icon"><i class="fas fa-shield-halved"></i></div>
    <div class="logo-text">Forensic<span>X</span></div>
  </div>
  <div style="margin-left:8px;font-size:11px;color:var(--text3);font-weight:500;padding:3px 8px;background:rgba(59,130,246,.1);border-radius:4px;border:1px solid rgba(59,130,246,.2)">DFIR PLATFORM v0.2</div>
  <div class="hdr-sep"></div>
  <div class="hdr-badge" id="hdr-device-badge">
    <span class="dot dot-red" id="device-dot"></span>
    <span id="device-count-text">No Devices</span>
  </div>
  <div class="hdr-badge" id="hdr-status">
    <span class="dot dot-green"></span>
    <span id="status-text">System Ready</span>
  </div>
  <div class="hdr-time" id="clock">00:00:00 UTC</div>
</header>

<!-- ── SIDEBAR ──────────────────────────────────────────────────────────────── -->
<nav id="sidebar">
  <div class="nav-section">Overview</div>
  <div class="nav-item active" data-page="dashboard">
    <i class="fas fa-chart-line nav-icon"></i><span>Dashboard</span>
  </div>
  <div class="nav-section">Investigation</div>
  <div class="nav-item" data-page="cases">
    <i class="fas fa-folder-open nav-icon"></i><span>Cases</span>
    <span class="nav-badge" id="nav-case-count">0</span>
  </div>
  <div class="nav-item" data-page="evidence">
    <i class="fas fa-box-archive nav-icon"></i><span>Evidence</span>
  </div>
  <div class="nav-item" data-page="search">
    <i class="fas fa-magnifying-glass nav-icon"></i><span>Search</span>
  </div>
  <div class="nav-section">Acquisition</div>
  <div class="nav-item" data-page="devices">
    <i class="fas fa-mobile-screen nav-icon"></i><span>Device Triage</span>
    <span class="nav-badge red" id="nav-device-count" style="display:none">0</span>
  </div>
  <div class="nav-item" data-page="memory">
    <i class="fas fa-microchip nav-icon"></i><span>Memory Analysis</span>
  </div>
  <div class="nav-section">Arsenal</div>
  <div class="nav-item" data-page="tools">
    <i class="fas fa-toolbox nav-icon"></i><span>Tool Registry</span>
  </div>
  <div class="nav-item" data-page="reports">
    <i class="fas fa-file-lines nav-icon"></i><span>Reports</span>
  </div>
  <div class="nav-item" data-page="coc">
    <i class="fas fa-link nav-icon"></i><span>Chain of Custody</span>
  </div>
  <div class="sidebar-footer">
    <div>ForensicX © 2024</div>
    <div style="margin-top:2px;color:var(--text3)">Apache-2.0</div>
  </div>
</nav>

<!-- ── MAIN CONTENT ──────────────────────────────────────────────────────────── -->
<main id="main">

<!-- ─── DASHBOARD PAGE ────────────────────────────────────────────────────── -->
<section class="page active" id="page-dashboard">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--blue),var(--cyan))"><i class="fas fa-chart-line"></i></div>
      Operations Dashboard
    </div>
    <button class="btn btn-ghost btn-sm" onclick="loadStats()"><i class="fas fa-rotate"></i> Refresh</button>
  </div>

  <div class="coc-strip">
    <i class="fas fa-shield-check" style="color:var(--green)"></i>
    Chain-of-custody enforcement active — SHA-256 + MD5 on every evidence ingest. All hashes logged immutably.
  </div>

  <div class="stats-grid" id="stats-grid">
    <div class="stat-tile tile-blue">
      <div class="stat-label">Active Cases</div>
      <div class="stat-val" id="stat-cases">—</div>
      <div class="stat-sub"><i class="fas fa-folder"></i> total open investigations</div>
      <i class="fas fa-briefcase stat-icon"></i>
    </div>
    <div class="stat-tile tile-green">
      <div class="stat-label">Evidence Items</div>
      <div class="stat-val" id="stat-evidence">—</div>
      <div class="stat-sub"><i class="fas fa-shield-check"></i> all hashes verified</div>
      <i class="fas fa-box-archive stat-icon"></i>
    </div>
    <div class="stat-tile tile-purple">
      <div class="stat-label">Tools Installed</div>
      <div class="stat-val" id="stat-tools">—</div>
      <div class="stat-sub"><i class="fas fa-toolbox"></i> of 161 in registry</div>
      <i class="fas fa-wrench stat-icon"></i>
    </div>
    <div class="stat-tile tile-amber">
      <div class="stat-label">Connected Devices</div>
      <div class="stat-val" id="stat-devices">0</div>
      <div class="stat-sub"><i class="fas fa-mobile"></i> via ADB</div>
      <i class="fas fa-mobile-screen stat-icon"></i>
    </div>
    <div class="stat-tile tile-cyan">
      <div class="stat-label">Tool Categories</div>
      <div class="stat-val">17</div>
      <div class="stat-sub"><i class="fas fa-layer-group"></i> forensic domains covered</div>
      <i class="fas fa-layer-group stat-icon"></i>
    </div>
  </div>

  <div class="grid-2 mb-16">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-pie-chart" style="color:var(--blue)"></i> Tool Coverage</h3></div>
      <div class="card-body">
        <div class="chart-wrap"><canvas id="tool-chart"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-clock-rotate-left" style="color:var(--green)"></i> Activity Log</h3><span class="badge badge-green">Live</span></div>
      <div class="card-body" style="padding:12px 14px">
        <div id="activity-feed" style="max-height:220px;overflow-y:auto">
          <div class="tl-item" style="padding-left:22px;position:relative">
            <div class="tl-dot green" style="position:absolute;left:3px;top:5px"></div>
            <div class="tl-time" id="init-time"></div>
            <div class="tl-text">ForensicX dashboard initialized</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="grid-3">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-mobile" style="color:var(--cyan)"></i> Connected Devices</h3></div>
      <div class="card-body" id="dash-device-list"><div class="text-muted text-sm">No ADB devices detected</div></div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-folder" style="color:var(--amber)"></i> Recent Cases</h3></div>
      <div class="card-body" id="dash-case-list"><div class="text-muted text-sm">No cases yet</div></div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-terminal" style="color:var(--purple)"></i> Quick Actions</h3></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:8px">
        <button class="btn btn-primary w-full" onclick="nav('devices')"><i class="fas fa-mobile-screen"></i> New Phone Triage</button>
        <button class="btn btn-ghost w-full" onclick="openNewCaseModal()"><i class="fas fa-folder-plus"></i> Create New Case</button>
        <button class="btn btn-ghost w-full" onclick="nav('tools')"><i class="fas fa-download"></i> Install Tools</button>
        <button class="btn btn-ghost w-full" onclick="nav('memory')"><i class="fas fa-microchip"></i> Memory Analysis</button>
        <button class="btn btn-ghost w-full" onclick="nav('reports')"><i class="fas fa-file-export"></i> Generate Report</button>
      </div>
    </div>
  </div>
</section>

<!-- ─── CASES PAGE ─────────────────────────────────────────────────────────── -->
<section class="page" id="page-cases">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--amber),#f97316)"><i class="fas fa-folder-open"></i></div>
      Case Management
    </div>
    <button class="btn btn-primary" onclick="openNewCaseModal()"><i class="fas fa-plus"></i> New Case</button>
  </div>
  <div class="coc-strip"><i class="fas fa-gavel" style="color:var(--amber)"></i> Cases are write-once. Evidence hashes are recorded at import and cannot be modified.</div>
  <div class="card">
    <div class="card-head"><h3><i class="fas fa-list"></i> All Cases</h3><span id="case-total-badge" class="badge badge-blue">0 cases</span></div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>#</th><th>Case Name</th><th>Investigator</th><th>Created</th><th>Evidence</th><th>Actions</th></tr></thead>
        <tbody id="cases-tbody"><tr><td colspan="6" style="text-align:center;color:var(--text3);padding:30px">No cases yet — create one above</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ─── EVIDENCE PAGE ──────────────────────────────────────────────────────── -->
<section class="page" id="page-evidence">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--green),#34d399)"><i class="fas fa-box-archive"></i></div>
      Evidence Repository
    </div>
  </div>
  <div class="coc-strip"><i class="fas fa-fingerprint" style="color:var(--green)"></i> Every item is SHA-256 + MD5 hashed at ingest. Re-verify at any time to confirm integrity.</div>
  <div class="field" style="max-width:300px">
    <label>Filter by case</label>
    <select id="ev-case-select" onchange="loadEvidence()">
      <option value="">All cases</option>
    </select>
  </div>
  <div class="card">
    <div class="card-head"><h3><i class="fas fa-shield-check" style="color:var(--green)"></i> Evidence Items</h3></div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>ID</th><th>Filename</th><th>SHA-256</th><th>MD5</th><th>Size</th><th>Imported</th></tr></thead>
        <tbody id="evidence-tbody"><tr><td colspan="6" style="text-align:center;color:var(--text3);padding:30px">Select a case to view evidence</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ─── SEARCH PAGE ────────────────────────────────────────────────────────── -->
<section class="page" id="page-search">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--cyan),var(--blue))"><i class="fas fa-magnifying-glass"></i></div>
      Artifact Search
    </div>
  </div>
  <div class="card mb-16">
    <div class="card-body">
      <div style="display:flex;gap:8px">
        <input type="text" id="search-input" placeholder="Search artifacts across all cases (FTS5 full-text search)…" style="flex:1" onkeydown="if(event.key==='Enter')runSearch()">
        <button class="btn btn-primary" onclick="runSearch()"><i class="fas fa-search"></i> Search</button>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-head"><h3><i class="fas fa-list-check"></i> Results</h3><span id="search-count" class="badge badge-blue">0 results</span></div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Type</th><th>Value</th><th>Evidence ID</th><th>Case</th></tr></thead>
        <tbody id="search-tbody"><tr><td colspan="4" style="text-align:center;color:var(--text3);padding:30px">Enter a search query above</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ─── DEVICE TRIAGE PAGE ─────────────────────────────────────────────────── -->
<section class="page" id="page-devices">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--blue),var(--purple))"><i class="fas fa-mobile-screen"></i></div>
      Live Device Triage
    </div>
    <button class="btn btn-ghost btn-sm" onclick="loadDevices()"><i class="fas fa-rotate"></i> Refresh</button>
  </div>
  <div class="coc-strip"><i class="fas fa-lock" style="color:var(--blue)"></i> Use only on devices you are authorized to examine. Acquisition is logged with timestamps and operator info.</div>

  <div class="grid-2 mb-16">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-mobile" style="color:var(--cyan)"></i> ADB Devices</h3><span class="badge badge-green">Live</span></div>
      <div class="card-body" id="device-list-panel">
        <div class="text-muted text-sm">Scanning for ADB devices…</div>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-sliders" style="color:var(--purple)"></i> Triage Options</h3></div>
      <div class="card-body">
        <div class="field">
          <label>Output Directory</label>
          <input type="text" id="triage-case-dir" value="./cases">
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--text)">
            <input type="checkbox" id="opt-alex" checked style="width:auto"> ALEX — Logical extraction
          </label>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--text)">
            <input type="checkbox" id="opt-triage" checked style="width:auto"> android_triage — System artifacts
          </label>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--text)">
            <input type="checkbox" id="opt-aleapp" checked style="width:auto"> ALEAPP — Artifact parsing
          </label>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-success" id="btn-android-triage" onclick="startAndroidTriage()" disabled>
            <i class="fas fa-play"></i> Start Android Triage
          </button>
          <button class="btn btn-primary" onclick="startIosTriage()">
            <i class="fab fa-apple"></i> iOS Triage
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <h3><i class="fas fa-terminal" style="color:var(--green)"></i> Triage Output</h3>
      <div style="display:flex;gap:6px">
        <span id="triage-status" class="badge badge-gray">Idle</span>
        <button class="btn btn-ghost btn-sm" onclick="clearTriageLog()">Clear</button>
      </div>
    </div>
    <div class="card-body" style="padding:12px">
      <div id="triage-log" class="log-box"></div>
    </div>
  </div>
</section>

<!-- ─── MEMORY ANALYSIS PAGE ───────────────────────────────────────────────── -->
<section class="page" id="page-memory">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--purple),var(--pink))"><i class="fas fa-microchip"></i></div>
      Memory Forensics
    </div>
  </div>
  <div class="grid-2 mb-16">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-upload" style="color:var(--purple)"></i> Load Memory Dump</h3></div>
      <div class="card-body">
        <div class="field">
          <label>Dump File Path (.raw, .mem, .dmp, .vmem)</label>
          <input type="text" id="mem-dump-path" placeholder="/path/to/memory.raw">
        </div>
        <div class="field">
          <label>Output Directory</label>
          <input type="text" id="mem-out-dir" value="./cases">
        </div>
        <div style="margin-bottom:14px;padding:10px;background:var(--surface2);border-radius:var(--radius-sm)">
          <div class="text-sm" style="color:var(--text2);margin-bottom:6px"><strong>Volatility 3 Plugins:</strong></div>
          <div style="display:flex;flex-wrap:wrap;gap:4px" id="plugin-list">
            <span class="badge badge-purple">windows.pslist</span>
            <span class="badge badge-purple">windows.pstree</span>
            <span class="badge badge-purple">windows.cmdline</span>
            <span class="badge badge-purple">windows.netscan</span>
            <span class="badge badge-purple">windows.malfind</span>
            <span class="badge badge-purple">windows.dlllist</span>
            <span class="badge badge-purple">windows.handles</span>
          </div>
        </div>
        <button class="btn btn-purple w-full" onclick="startMemoryAnalysis()"><i class="fas fa-play"></i> Run Analysis</button>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-info-circle" style="color:var(--blue)"></i> About Memory Forensics</h3></div>
      <div class="card-body">
        <div class="timeline">
          <div class="tl-item">
            <div class="tl-dot blue"></div>
            <div class="tl-time">Step 1</div>
            <div class="tl-text">Load memory dump file (any format supported by Volatility 3)</div>
          </div>
          <div class="tl-item">
            <div class="tl-dot blue"></div>
            <div class="tl-time">Step 2</div>
            <div class="tl-text">Auto-detect OS and profile</div>
          </div>
          <div class="tl-item">
            <div class="tl-dot blue"></div>
            <div class="tl-time">Step 3</div>
            <div class="tl-text">Run 7 core plugins: processes, network, injection detection</div>
          </div>
          <div class="tl-item">
            <div class="tl-dot green"></div>
            <div class="tl-time">Step 4</div>
            <div class="tl-text">Results saved as text files + imported into ForensicX case</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-head"><h3><i class="fas fa-terminal" style="color:var(--purple)"></i> Analysis Output</h3><span id="mem-status" class="badge badge-gray">Idle</span></div>
    <div class="card-body" style="padding:12px"><div id="mem-log" class="log-box"></div></div>
  </div>
</section>

<!-- ─── TOOLS PAGE ─────────────────────────────────────────────────────────── -->
<section class="page" id="page-tools">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--green),#34d399)"><i class="fas fa-toolbox"></i></div>
      Tool Registry (161 tools)
    </div>
    <button class="btn btn-primary" onclick="window.open('https://github.com/ammadahmed9001/forensicx/blob/main/scripts/install_tools.sh','_blank')">
      <i class="fas fa-download"></i> Install All
    </button>
  </div>
  <div class="search-bar"><i class="fas fa-search"></i><input type="text" id="tool-search" placeholder="Search tools…" oninput="filterTools()"></div>
  <div class="cat-filter" id="cat-filter"></div>
  <div id="tools-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px"></div>
</section>

<!-- ─── REPORTS PAGE ──────────────────────────────────────────────────────── -->
<section class="page" id="page-reports">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--amber),#f97316)"><i class="fas fa-file-lines"></i></div>
      Report Generator
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-file-export" style="color:var(--amber)"></i> Generate Case Report</h3></div>
      <div class="card-body">
        <div class="field">
          <label>Select Case</label>
          <select id="report-case-select"><option value="">— choose a case —</option></select>
        </div>
        <div class="field">
          <label>Report Format</label>
          <select id="report-format">
            <option value="json">JSON (machine-readable)</option>
            <option value="html">HTML (formatted)</option>
            <option value="csv">CSV (spreadsheet)</option>
          </select>
        </div>
        <button class="btn btn-primary w-full mb-8" onclick="generateReport()"><i class="fas fa-file-arrow-down"></i> Generate Report</button>
        <div id="report-output" style="display:none">
          <div class="card-head" style="padding:8px;margin-top:10px;border-radius:var(--radius-sm)"><h3>Report Preview</h3></div>
          <div class="log-box" style="height:400px" id="report-content"></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-shield-check" style="color:var(--green)"></i> Report Standards</h3></div>
      <div class="card-body">
        <div class="timeline">
          <div class="tl-item"><div class="tl-dot green"></div><div class="tl-time">ISO/IEC 27037</div><div class="tl-text">Digital evidence identification, collection, acquisition and preservation</div></div>
          <div class="tl-item"><div class="tl-dot green"></div><div class="tl-time">RFC 3227</div><div class="tl-text">Guidelines for evidence collection and archiving</div></div>
          <div class="tl-item"><div class="tl-dot green"></div><div class="tl-time">ACPO Principles</div><div class="tl-text">Association of Chief Police Officers digital evidence guidelines</div></div>
          <div class="tl-item"><div class="tl-dot blue"></div><div class="tl-time">Chain of Custody</div><div class="tl-text">Every report includes cryptographic hash verification trail</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ─── CHAIN OF CUSTODY PAGE ─────────────────────────────────────────────── -->
<section class="page" id="page-coc">
  <div class="page-head">
    <div class="page-title">
      <div class="icon" style="background:linear-gradient(135deg,var(--green),var(--cyan))"><i class="fas fa-link"></i></div>
      Chain of Custody
    </div>
  </div>
  <div class="coc-strip"><i class="fas fa-gavel" style="color:var(--green)"></i> All evidence ingest operations are SHA-256 + MD5 verified. The chain of custody is recorded in the local SQLite database with WAL journaling.</div>
  <div class="grid-2">
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-shield-halved" style="color:var(--green)"></i> Integrity Guarantees</h3></div>
      <div class="card-body">
        <div style="display:flex;flex-direction:column;gap:12px">
          <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm);border-left:3px solid var(--green)">
            <div style="font-weight:600;margin-bottom:4px;color:var(--green)"><i class="fas fa-check"></i> Dual-hash verification</div>
            <div class="text-sm text-muted">Every evidence file is hashed with SHA-256 and MD5 at import. Hashes are stored in the forensic database.</div>
          </div>
          <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm);border-left:3px solid var(--blue)">
            <div style="font-weight:600;margin-bottom:4px;color:var(--blue-l)"><i class="fas fa-check"></i> Write-once records</div>
            <div class="text-sm text-muted">Case and evidence records are never modified after creation. All data is append-only.</div>
          </div>
          <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm);border-left:3px solid var(--purple)">
            <div style="font-weight:600;margin-bottom:4px;color:#a78bfa"><i class="fas fa-check"></i> SQLite WAL journal</div>
            <div class="text-sm text-muted">Database uses Write-Ahead Logging for atomic transactions and crash recovery.</div>
          </div>
          <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm);border-left:3px solid var(--amber)">
            <div style="font-weight:600;margin-bottom:4px;color:var(--amber)"><i class="fas fa-check"></i> Timestamped audit trail</div>
            <div class="text-sm text-muted">Every operation is timestamped in UTC. All triage runs generate dated output directories.</div>
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><h3><i class="fas fa-scale-balanced" style="color:var(--amber)"></i> Legal Admissibility</h3></div>
      <div class="card-body">
        <div class="text-sm" style="color:var(--text2);line-height:1.8">
          <p class="mb-8">ForensicX is built on open-source tools with documented, reproducible methodology — a requirement for evidence admissibility in most jurisdictions.</p>
          <p class="mb-8"><strong style="color:var(--amber)">Important:</strong> Commercial tools like Cellebrite, EnCase, and FTK are listed in the registry as reference only. ForensicX does not install, crack, or replicate proprietary software. Using licensed commercial tools alongside ForensicX is fully supported and recommended for court-ready investigations.</p>
          <p class="mb-8">Never use unauthorized or cracked software in a forensic investigation. Cracked tools can contaminate evidence, introduce malware, and make findings inadmissible.</p>
          <p>Refer to your jurisdiction's digital evidence guidelines (ISO 27037, ACPO, SWGDE) for case-specific requirements.</p>
        </div>
      </div>
    </div>
  </div>
</section>

</main><!-- /main -->
</div><!-- /shell -->

<!-- ── MODAL: New Case ─────────────────────────────────────────────────────── -->
<div class="modal-overlay" id="new-case-modal">
  <div class="modal">
    <div class="modal-head">
      <h3><i class="fas fa-folder-plus" style="color:var(--blue)"></i> Create New Case</h3>
      <button class="btn btn-ghost btn-sm" onclick="closeModal('new-case-modal')"><i class="fas fa-xmark"></i></button>
    </div>
    <div class="modal-body">
      <div class="field"><label>Case Name *</label><input type="text" id="nc-name" placeholder="e.g. DF-2024-001 Android Seizure"></div>
      <div class="field"><label>Investigator</label><input type="text" id="nc-investigator" placeholder="Officer / analyst name"></div>
      <div class="field"><label>Notes / Synopsis</label><textarea id="nc-notes" placeholder="Brief description of the case…"></textarea></div>
    </div>
    <div class="modal-foot">
      <button class="btn btn-ghost" onclick="closeModal('new-case-modal')">Cancel</button>
      <button class="btn btn-primary" onclick="createCase()"><i class="fas fa-plus"></i> Create Case</button>
    </div>
  </div>
</div>

<div id="toasts"></div>

<script>
// ── Utility ─────────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const el = (tag,cls='',html='') => { const e=document.createElement(tag); if(cls)e.className=cls; if(html)e.innerHTML=html; return e; };
const fmt = d => new Date(d).toLocaleString();
const utcNow = () => new Date().toUTCString().replace(' GMT','');

function toast(msg, type='info') {
  const t = el('div', `toast toast-${type}`);
  const ico = type==='success'?'check-circle':type==='error'?'triangle-exclamation':'info-circle';
  t.innerHTML = `<i class="fas fa-${ico}"></i>${msg}`;
  $('toasts').appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  $('clock').textContent = now.toUTCString().match(/\d\d:\d\d:\d\d/)[0] + ' UTC';
  $('init-time').textContent = utcNow();
}
setInterval(updateClock, 1000);
updateClock();

// ── Navigation ────────────────────────────────────────────────────────────────
let currentPage = 'dashboard';
function nav(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  $(`page-${page}`) && $(`page-${page}`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`) && document.querySelector(`[data-page="${page}"]`).classList.add('active');
  currentPage = page;
  if(page==='tools')    loadTools();
  if(page==='cases')    loadCases();
  if(page==='evidence') loadEvidence();
  if(page==='devices')  loadDevices();
  if(page==='reports')  loadReportCases();
}
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => nav(item.dataset.page));
});

// ── Stats ────────────────────────────────────────────────────────────────────
let toolChartInst = null;
async function loadStats() {
  try {
    const r = await fetch('/api/stats'); const d = await r.json();
    $('stat-cases').textContent    = d.cases;
    $('stat-evidence').textContent = d.evidence;
    $('stat-tools').textContent    = `${d.tools_installed}/${d.tools_total}`;
    $('stat-devices').textContent  = d.devices;
    $('nav-case-count').textContent = d.cases;
    updateDeviceBadge(d.device_list || []);
    updateDashDevices(d.device_list || []);
  } catch(e) {}
  // Tool chart
  try {
    const r = await fetch('/api/tools/summary'); const d = await r.json();
    const cats = Object.entries(d.categories || {});
    if(cats.length) {
      const labels = cats.map(([k])=>k.replace(/_/g,' '));
      const vals   = cats.map(([,v])=>v.installed);
      const total  = cats.map(([,v])=>v.total);
      if(toolChartInst) toolChartInst.destroy();
      const ctx = document.getElementById('tool-chart').getContext('2d');
      toolChartInst = new Chart(ctx, {
        type:'bar',
        data:{
          labels,
          datasets:[
            {label:'Installed',data:vals,backgroundColor:'rgba(59,130,246,.7)',borderRadius:4},
            {label:'Total',data:total,backgroundColor:'rgba(59,130,246,.15)',borderRadius:4}
          ]
        },
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#94a3b8',boxWidth:12,font:{size:11}}}},scales:{x:{ticks:{color:'#64748b',font:{size:10}},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,.04)'}}}}
      });
    }
  } catch(e) {}
  // Recent cases
  try {
    const r = await fetch('/api/cases'); const cases = await r.json();
    const el = $('dash-case-list');
    if(!cases.length) { el.innerHTML='<div class="text-muted text-sm">No cases yet</div>'; return; }
    el.innerHTML = cases.slice(-5).reverse().map(c=>`
      <div style="padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="nav('cases')">
        <div style="font-weight:600;font-size:13px">#${c.id} ${c.name}</div>
        <div class="text-xs text-muted">${c.investigator || 'Unknown'} · ${fmt(c.created_at)}</div>
      </div>`).join('');
  } catch(e) {}
}
loadStats();

function updateDeviceBadge(devs) {
  $('device-dot').className = 'dot ' + (devs.length ? 'dot-green' : 'dot-red');
  $('device-count-text').textContent = devs.length ? `${devs.length} Device${devs.length>1?'s':''}` : 'No Devices';
  const nb = $('nav-device-count');
  if(devs.length){ nb.textContent=devs.length; nb.style.display=''; }
  else nb.style.display='none';
}

function updateDashDevices(devs) {
  const el = $('dash-device-list');
  if(!devs.length){ el.innerHTML='<div class="text-muted text-sm">No ADB devices detected — plug in a device with USB debugging enabled</div>'; return; }
  el.innerHTML = devs.map(d=>`
    <div class="device-card mb-8" onclick="nav('devices')">
      <div class="device-icon"><i class="fas fa-mobile-screen"></i></div>
      <div class="device-info">
        <div class="device-name">${d.manufacturer} ${d.model||d.serial}</div>
        <div class="device-serial">${d.serial} · Android ${d.android||'?'}</div>
      </div>
      <span class="badge ${d.state==='device'?'badge-green':'badge-amber'}">${d.state}</span>
    </div>`).join('');
}

// ── Cases ────────────────────────────────────────────────────────────────────
async function loadCases() {
  const r = await fetch('/api/cases'); const cases = await r.json();
  $('case-total-badge').textContent = `${cases.length} cases`;
  $('nav-case-count').textContent = cases.length;
  if(!cases.length){ $('cases-tbody').innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:30px">No cases yet</td></tr>'; return; }
  $('cases-tbody').innerHTML = cases.map(c=>`
    <tr>
      <td><span class="badge badge-blue">#${c.id}</span></td>
      <td style="font-weight:500;color:var(--text)">${c.name}</td>
      <td>${c.investigator||'—'}</td>
      <td class="text-xs text-muted mono">${fmt(c.created_at)}</td>
      <td><span class="badge badge-gray" id="ev-count-${c.id}">—</span></td>
      <td><button class="btn btn-ghost btn-sm" onclick="viewEvidence(${c.id})"><i class="fas fa-eye"></i> View</button>
          <button class="btn btn-ghost btn-sm" onclick="exportCase(${c.id})"><i class="fas fa-download"></i></button></td>
    </tr>`).join('');
  // async fill evidence counts
  cases.forEach(async c => {
    const r2 = await fetch(`/api/cases/${c.id}/evidence`); const ev = await r2.json();
    const el = $(`ev-count-${c.id}`); if(el) el.textContent = ev.length;
  });
  // populate evidence select
  const sel = $('ev-case-select');
  while(sel.options.length > 1) sel.remove(1);
  cases.forEach(c => { const o=document.createElement('option'); o.value=c.id; o.textContent=`#${c.id} ${c.name}`; sel.appendChild(o); });
}

function openNewCaseModal() { $('new-case-modal').classList.add('open'); }
function closeModal(id) { $(id).classList.remove('open'); }

async function createCase() {
  const name = $('nc-name').value.trim();
  if(!name){ toast('Case name is required','error'); return; }
  const r = await fetch('/api/cases', {method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, investigator:$('nc-investigator').value, notes:$('nc-notes').value})});
  if(r.ok){ toast(`Case created: ${name}`,'success'); closeModal('new-case-modal'); $('nc-name').value=''; $('nc-investigator').value=''; $('nc-notes').value=''; loadCases(); loadStats(); }
  else toast('Failed to create case','error');
}

// ── Evidence ─────────────────────────────────────────────────────────────────
async function loadEvidence() {
  const cid = $('ev-case-select').value;
  if(!cid){ $('evidence-tbody').innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:30px">Select a case</td></tr>'; return; }
  const r = await fetch(`/api/cases/${cid}/evidence`); const items = await r.json();
  if(!items.length){ $('evidence-tbody').innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:30px">No evidence in this case</td></tr>'; return; }
  $('evidence-tbody').innerHTML = items.map(e=>`
    <tr>
      <td><span class="badge badge-blue">#${e.id}</span></td>
      <td style="font-weight:500;color:var(--text)">${e.filename||e.file_path}</td>
      <td class="mono text-xs">${(e.sha256||'').substring(0,24)}…</td>
      <td class="mono text-xs">${(e.md5||'').substring(0,16)}…</td>
      <td>${e.size ? (e.size/1024).toFixed(1)+'KB' : '—'}</td>
      <td class="mono text-xs">${fmt(e.imported_at||e.created_at)}</td>
    </tr>`).join('');
}

function viewEvidence(caseId) {
  nav('evidence');
  $('ev-case-select').value = caseId;
  loadEvidence();
}

// ── Search ────────────────────────────────────────────────────────────────────
async function runSearch() {
  const q = $('search-input').value.trim(); if(!q) return;
  const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`); const items = await r.json();
  $('search-count').textContent = `${items.length} results`;
  if(!items.length){ $('search-tbody').innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:30px">No results found</td></tr>'; return; }
  $('search-tbody').innerHTML = items.map(a=>`
    <tr>
      <td><span class="badge badge-purple">${a.artifact_type||'artifact'}</span></td>
      <td class="mono text-xs" style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${a.value||''}</td>
      <td>${a.evidence_id||'—'}</td>
      <td>${a.case_id||'—'}</td>
    </tr>`).join('');
}

// ── Devices ───────────────────────────────────────────────────────────────────
let selectedSerial = null;
async function loadDevices() {
  const r = await fetch('/api/devices'); const devs = await r.json();
  updateDeviceBadge(devs);
  const panel = $('device-list-panel');
  if(!devs.length){
    panel.innerHTML='<div style="text-align:center;padding:20px"><i class="fas fa-mobile" style="font-size:36px;color:var(--text3);margin-bottom:8px;display:block"></i><div class="text-muted text-sm">No ADB devices found.<br>Enable USB debugging and connect a device.</div></div>';
    $('btn-android-triage').disabled = true;
    return;
  }
  panel.innerHTML = devs.map(d=>`
    <div class="device-card mb-8 ${d.serial===selectedSerial?'selected':''}" onclick="selectDevice('${d.serial}','${d.display_name||d.serial}')">
      <div class="device-icon"><i class="fas fa-mobile-screen"></i></div>
      <div class="device-info">
        <div class="device-name">${d.manufacturer||''} ${d.model||d.serial}</div>
        <div class="device-serial">${d.serial}</div>
        <div class="text-xs text-muted">Android ${d.android||'?'} · SDK ${d.sdk||'?'}</div>
      </div>
      <span class="badge ${d.state==='device'?'badge-green':'badge-amber'}">${d.state}</span>
    </div>`).join('');
}
function selectDevice(serial, name) {
  selectedSerial = serial;
  $('btn-android-triage').disabled = false;
  document.querySelectorAll('.device-card').forEach(c => { c.classList.toggle('selected', c.onclick.toString().includes(`'${serial}'`)); });
  toast(`Selected: ${name}`, 'info');
}

async function startAndroidTriage() {
  if(!selectedSerial){ toast('Select a device first','error'); return; }
  $('triage-status').className='badge badge-blue';
  $('triage-status').textContent='Running';
  addTriageLog('init', `Starting Android triage on ${selectedSerial}…`, 'info');
  const body = {
    serial: selectedSerial,
    case_dir: $('triage-case-dir').value,
    run_alex: $('opt-alex').checked,
    run_triage: $('opt-triage').checked,
    run_aleapp: $('opt-aleapp').checked,
  };
  const r = await fetch('/api/triage/android', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if(!r.ok) toast('Failed to start triage', 'error');
}

async function startIosTriage() {
  $('triage-status').className='badge badge-blue'; $('triage-status').textContent='Running';
  addTriageLog('init','Starting iOS triage…','info');
  await fetch('/api/triage/ios',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_dir:$('triage-case-dir').value})});
}

function addTriageLog(step, msg, cls='info') {
  const box = $('triage-log');
  const line = el('div',`log-line log-${cls}`);
  line.innerHTML = `<span class="step">[${step}]</span><span class="msg">${msg}</span>`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}
function clearTriageLog() { $('triage-log').innerHTML=''; $('triage-status').className='badge badge-gray'; $('triage-status').textContent='Idle'; }

// ── Memory ────────────────────────────────────────────────────────────────────
async function startMemoryAnalysis() {
  const dump = $('mem-dump-path').value.trim();
  if(!dump){ toast('Enter a dump file path','error'); return; }
  $('mem-status').className='badge badge-purple'; $('mem-status').textContent='Running';
  addMemLog('init',`Loading dump: ${dump}`,'info');
  await fetch('/api/memory/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dump_path:dump,case_dir:$('mem-out-dir').value})});
}
function addMemLog(step,msg,cls='info') {
  const box=$('mem-log'); const line=el('div',`log-line log-${cls}`);
  line.innerHTML=`<span class="step">[${step}]</span><span class="msg">${msg}</span>`;
  box.appendChild(line); box.scrollTop=box.scrollHeight;
}

// ── Tools ─────────────────────────────────────────────────────────────────────
let allTools = []; let activeCategory = '';
async function loadTools() {
  if(allTools.length) { renderTools(); return; }
  const r = await fetch('/api/tools'); allTools = await r.json();
  // build category chips
  const cats = [...new Set(allTools.map(t=>t.category))].sort();
  const cf = $('cat-filter');
  cf.innerHTML = '<div class="cat-chip active" onclick="filterCat(\'\',this)">All</div>' +
    cats.map(c=>`<div class="cat-chip" onclick="filterCat('${c}',this)">${c.replace(/_/g,' ')}</div>`).join('');
  renderTools();
}
function filterCat(cat, chip) {
  activeCategory = cat;
  document.querySelectorAll('.cat-chip').forEach(c=>c.classList.remove('active'));
  chip.classList.add('active');
  renderTools();
}
function filterTools() { renderTools(); }
function renderTools() {
  const q = ($('tool-search').value||'').toLowerCase();
  const filtered = allTools.filter(t =>
    (!activeCategory || t.category===activeCategory) &&
    (!q || t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q) || t.category.toLowerCase().includes(q))
  );
  const catColors = {
    'Mobile Android':'blue','Mobile iOS':'cyan','Disk & Imaging':'amber',
    'Memory':'purple','Logs & Timeline':'green','Network':'red',
    'Artifact Analysis':'purple','Password & Hash':'amber','Malware & RE':'red',
    'IR':'blue','Case Management':'green','Windows Artifacts':'cyan',
    'OSINT':'pink','Cloud & Container':'cyan','Reporting':'green',
    'Forensic Distros':'amber','Commercial Reference':'gray',
  };
  $('tools-grid').innerHTML = filtered.map(t => {
    const col = catColors[t.category]||'blue';
    const badge = t.installed ? '<span class="badge badge-green"><i class="fas fa-check"></i> Installed</span>' : '<span class="badge badge-gray">Not installed</span>';
    const isCommercial = t.category === 'Commercial Reference';
    return `<div class="card" style="border-top:2px solid var(--${col})">
      <div class="card-head" style="padding:10px 14px">
        <div style="font-weight:600;font-size:13px;display:flex;align-items:center;gap:6px">
          <span>${t.name}</span>
          <span class="badge badge-${col}" style="font-size:10px">${t.category.replace(/_/g,' ')}</span>
        </div>
        ${badge}
      </div>
      <div style="padding:10px 14px">
        <div class="text-sm text-muted mb-8">${t.description}</div>
        <div class="flex gap-8 mb-8" style="flex-wrap:wrap">
          <span class="text-xs text-muted"><i class="fas fa-code-branch"></i> ${t.license||'—'}</span>
          <span class="text-xs text-muted"><i class="fas fa-user"></i> ${t.author||'—'}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${t.repo_url?`<a href="${t.repo_url}" target="_blank" class="btn btn-ghost btn-sm"><i class="fas fa-arrow-up-right-from-square"></i> Repo</a>`:''}
          ${isCommercial?`<span class="btn btn-ghost btn-sm" style="cursor:default"><i class="fas fa-building"></i> Commercial</span>`:''}
        </div>
        ${t.notes?`<div class="text-xs text-muted" style="margin-top:6px;font-style:italic">${t.notes}</div>`:''}
      </div>
    </div>`;
  }).join('');
}

// ── Reports ───────────────────────────────────────────────────────────────────
async function loadReportCases() {
  const r = await fetch('/api/cases'); const cases = await r.json();
  const sel = $('report-case-select');
  while(sel.options.length > 1) sel.remove(1);
  cases.forEach(c => { const o=document.createElement('option'); o.value=c.id; o.textContent=`#${c.id} ${c.name}`; sel.appendChild(o); });
}
async function generateReport() {
  const cid = $('report-case-select').value; if(!cid){ toast('Select a case','error'); return; }
  const r = await fetch(`/api/report/${cid}`); const data = await r.json();
  const fmt2 = $('report-format').value;
  let out;
  if(fmt2==='json') out = JSON.stringify(data,null,2);
  else if(fmt2==='csv') {
    const ev = data.evidence||[];
    out = 'ID,Filename,SHA256,MD5,Size,Imported\n' + ev.map(e=>`${e.id},"${e.filename||e.file_path}",${e.sha256||''},${e.md5||''},${e.size||''},${e.imported_at||''}`).join('\n');
  } else {
    out = `<html><head><title>ForensicX Report — Case #${cid}</title></head><body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h1>ForensicX Case Report</h1>
<p><strong>Case:</strong> ${data.case.name}</p>
<p><strong>Investigator:</strong> ${data.case.investigator||'—'}</p>
<p><strong>Created:</strong> ${fmt(data.case.created_at)}</p>
<p><strong>Generated:</strong> ${data.generated}</p>
<p><strong>Evidence items:</strong> ${data.evidence_count}</p>
<hr><h2>Chain of Custody</h2><p>${data.chain_of_custody}</p>
<h2>Evidence</h2><table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr><th>ID</th><th>File</th><th>SHA-256</th><th>Imported</th></tr>
${(data.evidence||[]).map(e=>`<tr><td>${e.id}</td><td>${e.filename||e.file_path}</td><td style="font-size:11px;font-family:monospace">${e.sha256||''}</td><td>${fmt(e.imported_at||e.created_at)}</td></tr>`).join('')}
</table></body></html>`;
  }
  $('report-content').textContent = out;
  $('report-output').style.display = 'block';
  // Download
  const blob = new Blob([out], {type: fmt2==='json'?'application/json':fmt2==='csv'?'text/csv':'text/html'});
  const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=`forensicx-case-${cid}.${fmt2}`; a.click();
  toast(`Report generated for case #${cid}`, 'success');
}

async function exportCase(caseId) {
  $('report-case-select').value = caseId;
  nav('reports');
  setTimeout(generateReport, 200);
}

// ── SSE ───────────────────────────────────────────────────────────────────────
function addActivity(msg, type='info') {
  const feed = $('activity-feed');
  const item = el('div','tl-item',`
    <div class="tl-dot ${type==='ok'?'green':type==='err'?'red':'blue'}" style="position:absolute;left:3px;top:5px"></div>
    <div class="tl-time">${utcNow()}</div>
    <div class="tl-text">${msg}</div>
  `);
  item.style.cssText='position:relative;padding-left:22px;margin-bottom:10px';
  feed.insertBefore(item, feed.firstChild);
  while(feed.children.length > 30) feed.removeChild(feed.lastChild);
}

const sse = new EventSource('/stream');
sse.addEventListener('device_attach', e => {
  const d = JSON.parse(e.data);
  toast(`Device connected: ${d.manufacturer} ${d.model} (${d.serial})`, 'success');
  addActivity(`Device attached: ${d.serial}`, 'ok');
  loadStats(); if(currentPage==='devices') loadDevices();
});
sse.addEventListener('device_detach', e => {
  const d = JSON.parse(e.data);
  toast(`Device disconnected: ${d.serial}`, 'info');
  addActivity(`Device removed: ${d.serial}`);
  loadStats(); if(currentPage==='devices') loadDevices();
});
sse.addEventListener('case_created', e => {
  const d = JSON.parse(e.data);
  addActivity(`Case created: #${d.id} ${d.name}`, 'ok');
  loadStats();
});
sse.addEventListener('triage_log', e => {
  const d = JSON.parse(e.data);
  const cls = d.step==='done'?'ok':d.step==='error'?'err':'info';
  addTriageLog(d.step, d.msg, cls);
  addMemLog(d.step, d.msg, cls);
  if(d.step==='done') {
    toast('Triage complete!', 'success');
    $('triage-status').className='badge badge-green'; $('triage-status').textContent='Done';
    $('mem-status').className='badge badge-green'; $('mem-status').textContent='Done';
    loadStats();
  }
});
sse.addEventListener('triage_done', e => {
  const d = JSON.parse(e.data);
  addActivity(`Triage complete: ${d.serial}`, 'ok');
});

// ── Background canvas (subtle hex dots) ─────────────────────────────────────
(function(){
  const c = $('bg-canvas'); const ctx = c.getContext('2d');
  function resize(){ c.width=innerWidth; c.height=innerHeight; }
  resize(); window.addEventListener('resize', resize);
  const pts = Array.from({length:80}, ()=>({x:Math.random()*4000, y:Math.random()*3000, r:Math.random()*1.5+.5}));
  function draw(){
    ctx.clearRect(0,0,c.width,c.height);
    pts.forEach(p=>{ ctx.beginPath(); ctx.arc(p.x%c.width, p.y%c.height, p.r, 0, Math.PI*2); ctx.fillStyle='#60a5fa'; ctx.fill(); });
  }
  draw();
})();

// ── Init ──────────────────────────────────────────────────────────────────────
setTimeout(loadStats, 200);
</script>
</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────────
def run_web(host: str = "127.0.0.1", port: int = 5000,
            open_browser: bool = True, debug: bool = False) -> None:
    import webbrowser
    url = f"http://{host}:{port}"
    print(f"\n  ForensicX Web Dashboard  →  {url}\n  Press Ctrl+C to stop.\n")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=debug, threaded=True,
            use_reloader=False)

if __name__ == "__main__":
    run_web()
