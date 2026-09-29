"""
ForensicX HTML Report Generator
Produces a navigable, self-contained HTML report from a triage output directory.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path


def _size_fmt(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"


def _walk_tree(root: Path, base: Path) -> list[dict]:
    items = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return items
    for entry in entries:
        rel = str(entry.relative_to(base))
        item: dict = {"name": entry.name, "path": str(entry), "rel": rel}
        if entry.is_dir():
            item["type"] = "dir"
            item["children"] = _walk_tree(entry, base)
            item["count"] = len(list(entry.rglob("*")))
        else:
            item["type"] = "file"
            try:
                item["size"] = entry.stat().st_size
                item["size_fmt"] = _size_fmt(item["size"])
            except OSError:
                item["size"] = 0
                item["size_fmt"] = "?"
            suffix = entry.suffix.lower()
            item["ext"] = suffix
            if suffix in (".txt", ".json", ".csv", ".log", ".xml"):
                item["previewable"] = True
                try:
                    content = entry.read_text(errors="replace")
                    item["preview"] = content[:4000]
                    item["lines"] = len(content.splitlines())
                except Exception:
                    item["previewable"] = False
            else:
                item["previewable"] = False
        items.append(item)
    return items


def _render_tree_html(items: list[dict], depth: int = 0) -> str:
    if not items:
        return ""
    html = []
    for item in items:
        indent = depth * 20
        if item["type"] == "dir":
            count = item.get("count", 0)
            html.append(
                f'<div class="tree-dir" style="margin-left:{indent}px">'
                f'<span class="tree-toggle" onclick="toggleDir(this)">▶</span>'
                f'<span class="tree-icon">📁</span>'
                f'<span class="tree-name">{item["name"]}</span>'
                f'<span class="tree-meta">{count} items</span>'
                f'<div class="tree-children" style="display:none">'
                + _render_tree_html(item.get("children", []), depth + 1)
                + "</div></div>"
            )
        else:
            ext = item.get("ext", "")
            icons = {".txt": "📄", ".json": "📋", ".csv": "📊", ".log": "📜",
                     ".zip": "🗜️", ".html": "🌐", ".png": "🖼️", ".jpg": "🖼️"}
            icon = icons.get(ext, "📄")
            preview_btn = ""
            if item.get("previewable"):
                escaped = item.get("preview", "").replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                preview_btn = (
                    f'<button class="prev-btn" onclick="showPreview(`{item["name"]}`,`{escaped}`)">preview</button>'
                )
            html.append(
                f'<div class="tree-file" style="margin-left:{indent}px">'
                f'<span class="tree-icon">{icon}</span>'
                f'<span class="tree-name">{item["name"]}</span>'
                f'<span class="tree-meta">{item.get("size_fmt","")}</span>'
                f'<span class="tree-path mono">{item["path"]}</span>'
                f'{preview_btn}'
                f"</div>"
            )
    return "\n".join(html)


def generate_html_report(
    out_dir: Path,
    device_info: dict,
    findings: list[dict],
    case_name: str = "",
    investigator: str = "ForensicX Auto-Triage",
) -> Path:
    """
    Generate a self-contained HTML forensic report.
    Returns path to the report file.
    """
    tree_items = _walk_tree(out_dir, out_dir)
    tree_html = _render_tree_html(tree_items)

    ts = datetime.datetime.utcnow().isoformat() + "Z"
    model = device_info.get("model", "Unknown")
    mfr = device_info.get("mfr", "")
    serial = device_info.get("serial", "Unknown")
    android = device_info.get("android", "Unknown")
    imei = device_info.get("imei", "Unknown")

    findings_html = ""
    for f in findings:
        sev = f.get("severity", "info")
        color = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "info": "#6b7280"}.get(sev, "#6b7280")
        findings_html += f"""
        <div class="finding finding-{sev}">
          <div class="finding-head">
            <span class="finding-badge" style="background:{color}">{sev.upper()}</span>
            <strong>{f.get("title","Finding")}</strong>
          </div>
          <div class="finding-body">{f.get("description","")}</div>
          {f'<div class="finding-path"><code>{f["path"]}</code></div>' if f.get("path") else ""}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ForensicX Report — {case_name or model}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;font-size:14px;line-height:1.6}}
a{{color:#58a6ff}}
header{{background:linear-gradient(135deg,#1a2332,#0d1117);padding:24px 32px;border-bottom:1px solid #30363d}}
.logo{{display:flex;align-items:center;gap:12px;margin-bottom:12px}}
.logo-icon{{width:40px;height:40px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px}}
.logo-text{{font-size:20px;font-weight:700;color:#e6edf3}}
.report-meta{{display:flex;flex-wrap:wrap;gap:20px;font-size:12px;color:#8b949e}}
.meta-item strong{{color:#e6edf3}}
main{{max-width:1400px;margin:0 auto;padding:24px 32px}}
.section{{margin-bottom:28px}}
h2{{font-size:16px;font-weight:600;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:8px}}
.badge{{display:inline-flex;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}}
.grid-4{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;border-top:2px solid #3b82f6}}
.stat-val{{font-size:24px;font-weight:700;color:#58a6ff}}
.stat-lbl{{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.6px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#161b22;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#8b949e;border-bottom:1px solid #30363d}}
td{{padding:8px 12px;border-bottom:1px solid #21262d;color:#c9d1d9}}
tr:hover td{{background:rgba(255,255,255,.02)}}
.mono{{font-family:'Courier New',monospace;font-size:12px;word-break:break-all}}
.finding{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:10px}}
.finding-head{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
.finding-badge{{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;color:#fff}}
.finding-path{{margin-top:6px;font-size:12px;color:#8b949e}}
.finding-critical{{border-left:3px solid #ef4444}}
.finding-high    {{border-left:3px solid #f59e0b}}
.finding-medium  {{border-left:3px solid #3b82f6}}
.finding-info    {{border-left:3px solid #6b7280}}
/* tree */
.tree-root{{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px;font-size:13px;max-height:600px;overflow-y:auto}}
.tree-dir{{padding:3px 0}}
.tree-file{{padding:2px 0;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.tree-children{{padding-left:16px}}
.tree-icon{{width:18px;text-align:center}}
.tree-name{{font-weight:500;color:#e6edf3}}
.tree-meta{{color:#6b7280;font-size:11px}}
.tree-path{{color:#8b949e;font-size:11px;flex:1;min-width:200px}}
.tree-toggle{{cursor:pointer;color:#6b7280;width:16px;display:inline-block;user-select:none}}
.prev-btn{{background:#21262d;border:1px solid #30363d;color:#58a6ff;border-radius:4px;padding:1px 6px;font-size:11px;cursor:pointer}}
.prev-btn:hover{{background:#30363d}}
/* preview modal */
#preview-modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:100;align-items:center;justify-content:center}}
#preview-modal.open{{display:flex}}
.preview-box{{background:#161b22;border:1px solid #30363d;border-radius:10px;width:min(800px,90vw);max-height:80vh;overflow:hidden;display:flex;flex-direction:column}}
.preview-head{{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #30363d}}
.preview-body{{overflow-y:auto;padding:16px}}
pre{{font-family:'Courier New',monospace;font-size:12px;white-space:pre-wrap;word-break:break-word;color:#c9d1d9}}
.close-btn{{background:none;border:none;color:#8b949e;font-size:18px;cursor:pointer;padding:0 4px}}
/* coc */
.coc-box{{background:#0d2818;border:1px solid #1a7f37;border-radius:8px;padding:16px;display:flex;gap:12px}}
.coc-icon{{font-size:24px}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="logo-icon">🛡️</div>
    <div class="logo-text">ForensicX — Digital Forensic Report</div>
  </div>
  <div class="report-meta">
    <div><strong>Device:</strong> {mfr} {model}</div>
    <div><strong>Serial:</strong> {serial}</div>
    <div><strong>Android:</strong> {android}</div>
    <div><strong>IMEI:</strong> {imei}</div>
    <div><strong>Investigator:</strong> {investigator}</div>
    <div><strong>Generated:</strong> {ts}</div>
    <div><strong>Case:</strong> {case_name or "Auto-Triage"}</div>
  </div>
</header>

<main>
  <div class="section">
    <div class="coc-box">
      <div class="coc-icon">⛓️</div>
      <div>
        <strong>Chain of Custody</strong><br>
        All evidence hashed (SHA-256 + MD5) at acquisition. Output directory: <code>{out_dir}</code><br>
        This report was generated by ForensicX on {ts}. Investigator: {investigator}.
      </div>
    </div>
  </div>

  <div class="section">
    <h2>📊 Device Profile</h2>
    <div class="grid-4">
      <div class="stat"><div class="stat-val">{model}</div><div class="stat-lbl">Device Model</div></div>
      <div class="stat"><div class="stat-val">{android}</div><div class="stat-lbl">Android Version</div></div>
      <div class="stat"><div class="stat-val">{serial[:12] if len(serial)>12 else serial}</div><div class="stat-lbl">Serial Number</div></div>
      <div class="stat"><div class="stat-val">{len(findings)}</div><div class="stat-lbl">Findings</div></div>
    </div>
    <table>
      <thead><tr><th>Property</th><th>Value</th></tr></thead>
      <tbody>
        {''.join(f"<tr><td>{k}</td><td class='mono'>{v}</td></tr>" for k,v in device_info.items())}
      </tbody>
    </table>
  </div>

  {'<div class="section"><h2>🚨 Key Findings</h2>' + findings_html + '</div>' if findings else ''}

  <div class="section">
    <h2>📁 Output Files</h2>
    <p style="color:#8b949e;font-size:12px;margin-bottom:10px">Click ▶ to expand folders. Click <span style="color:#58a6ff">preview</span> to view file contents.</p>
    <div class="tree-root" id="file-tree">
      {tree_html}
    </div>
  </div>

  <div class="section">
    <h2>📋 Raw Device Info</h2>
    <pre>{json.dumps(device_info, indent=2)}</pre>
  </div>

  <div class="section" style="color:#6b7280;font-size:12px;border-top:1px solid #30363d;padding-top:16px">
    Generated by ForensicX DFIR Platform (Apache-2.0) · {ts}<br>
    Use only on devices you are authorized to examine.
  </div>
</main>

<!-- Preview modal -->
<div id="preview-modal">
  <div class="preview-box">
    <div class="preview-head">
      <strong id="preview-title">Preview</strong>
      <button class="close-btn" onclick="document.getElementById('preview-modal').classList.remove('open')">✕</button>
    </div>
    <div class="preview-body"><pre id="preview-content"></pre></div>
  </div>
</div>

<script>
function toggleDir(el) {{
  const children = el.parentElement.querySelector('.tree-children');
  if(!children) return;
  const open = children.style.display !== 'none';
  children.style.display = open ? 'none' : 'block';
  el.textContent = open ? '▶' : '▼';
}}
function showPreview(name, content) {{
  document.getElementById('preview-title').textContent = name;
  document.getElementById('preview-content').textContent = content;
  document.getElementById('preview-modal').classList.add('open');
}}
document.getElementById('preview-modal').addEventListener('click', function(e) {{
  if(e.target === this) this.classList.remove('open');
}});
// Auto-expand first level
document.querySelectorAll('#file-tree > .tree-dir > .tree-toggle').forEach(t => t.click());
</script>
</body>
</html>"""

    report_path = out_dir / "forensicx_report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path
