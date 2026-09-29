"""
ForensicX Hub — comprehensive forensic tool launcher with live device detection.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from forensicx_hub.device_monitor import AndroidDevice, DeviceMonitor
from forensicx_hub.tools_registry import ALL_TOOLS, CATEGORIES, Tool

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "cases"
TOOLS_DIR = ROOT / "tools"

PALETTE = {
    "ready":    "#22aa22",
    "missing":  "#cc4400",
    "manual":   "#888800",
    "warn":     "#cc7700",
    "device":   "#1a7ab5",
    "header_bg": "#1e2a3a",
    "header_fg": "#e8edf2",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_cmd(tool: Tool) -> list[str]:
    td = str(tool.tool_dir)
    return [p.replace("{TOOL_DIR}", td) for p in tool.launch_cmd]


def _log(widget: scrolledtext.ScrolledText, text: str,
         tag: str = "") -> None:
    """Append text to a ScrolledText widget thread-safely."""
    def _do() -> None:
        widget.config(state="normal")
        if tag:
            widget.insert("end", text + "\n", tag)
        else:
            widget.insert("end", text + "\n")
        widget.see("end")
        widget.config(state="disabled")
    widget.after(0, _do)


# ── main window ───────────────────────────────────────────────────────────────

class ForensicXHub(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ForensicX — Forensic Tool Hub")
        self.geometry("1500x900")
        self.minsize(1100, 700)
        self._monitor = DeviceMonitor(interval=3.0)
        self._monitor.on_attach(self._on_device_attach)
        self._monitor.on_detach(self._on_device_detach)
        self._monitor.on_update(self._on_devices_update)
        self._build_ui()
        self._monitor.start()
        self.after(200, self._refresh_tools)
        self.after(500, lambda: self._monitor.refresh_once())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── menu ──────────────────────────────────────────────────────────────
        mb = tk.Menu(self)
        file_m = tk.Menu(mb, tearoff=0)
        file_m.add_command(label="New Case…", command=self._create_case)
        file_m.add_command(label="Open Cases Dir", command=lambda: self._open_dir(CASES_DIR))
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self._on_close)
        mb.add_cascade(label="File", menu=file_m)

        tools_m = tk.Menu(mb, tearoff=0)
        tools_m.add_command(label="Refresh Tool Status", command=self._refresh_tools)
        tools_m.add_command(label="Open Tools Dir", command=lambda: self._open_dir(TOOLS_DIR))
        tools_m.add_separator()
        tools_m.add_command(label="Run Installer", command=self._run_installer)
        tools_m.add_command(label="Install apt Tools", command=self._install_apt)
        tools_m.add_command(label="Install pip Tools", command=self._install_pip)
        mb.add_cascade(label="Tools", menu=tools_m)

        help_m = tk.Menu(mb, tearoff=0)
        help_m.add_command(label="About", command=self._show_about)
        mb.add_cascade(label="Help", menu=help_m)
        self.config(menu=mb)

        # ── header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=PALETTE["header_bg"], height=52)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  ForensicX  |  Digital Forensics Tool Hub",
                 bg=PALETTE["header_bg"], fg=PALETTE["header_fg"],
                 font=("Helvetica", 17, "bold")).pack(side="left", padx=8)
        self._device_badge = tk.Label(hdr, text="No devices",
                                      bg=PALETTE["header_bg"], fg="#aaaaaa",
                                      font=("Helvetica", 11))
        self._device_badge.pack(side="right", padx=16)
        tk.Label(hdr, text="Authorized use only  |  ",
                 bg=PALETTE["header_bg"], fg="#cc5555",
                 font=("Helvetica", 10)).pack(side="right")

        # ── main pane ─────────────────────────────────────────────────────────
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)

        # LEFT column ──────────────────────────────────────────────────────────
        left = ttk.Frame(pane, padding=4)
        pane.add(left, weight=2)

        # search + category
        sf = ttk.Frame(left)
        sf.pack(fill="x", pady=2)
        ttk.Label(sf, text="Category:").pack(side="left")
        self._cat_var = tk.StringVar(value=list(CATEGORIES.keys())[0])
        cat_cb = ttk.Combobox(sf, textvariable=self._cat_var,
                              values=list(CATEGORIES.keys()), state="readonly", width=24)
        cat_cb.pack(side="left", padx=4)
        cat_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_tools())

        qf = ttk.Frame(left)
        qf.pack(fill="x", pady=2)
        ttk.Label(qf, text="Search:").pack(side="left")
        self._q = tk.StringVar()
        self._q.trace_add("write", lambda *_: self._refresh_tools())
        ttk.Entry(qf, textvariable=self._q).pack(side="left", fill="x", expand=True, padx=4)

        # tool tree
        cols = ("status", "name", "type", "description")
        self._tree = ttk.Treeview(left, columns=cols, show="headings", height=32)
        self._tree.heading("status", text="Status")
        self._tree.heading("name", text="Tool")
        self._tree.heading("type", text="Install")
        self._tree.heading("description", text="Description")
        self._tree.column("status", width=90, anchor="center")
        self._tree.column("name", width=140)
        self._tree.column("type", width=70, anchor="center")
        self._tree.column("description", width=360)
        self._tree.tag_configure("ready",   foreground=PALETTE["ready"])
        self._tree.tag_configure("missing", foreground=PALETTE["missing"])
        self._tree.tag_configure("manual",  foreground=PALETTE["manual"])
        self._tree.tag_configure("commercial", foreground="#888888", font=("Helvetica", 9, "italic"))
        sb = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._launch_selected())

        # RIGHT column ─────────────────────────────────────────────────────────
        right = ttk.Frame(pane, padding=4)
        pane.add(right, weight=3)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # ── Tab 1: Tool Detail ────────────────────────────────────────────────
        self._tab_detail(nb)

        # ── Tab 2: Phone Triage (live) ────────────────────────────────────────
        self._tab_phone(nb)

        # ── Tab 3: Case Workspace ─────────────────────────────────────────────
        self._tab_workspace(nb)

        # ── Tab 4: Memory Analysis ────────────────────────────────────────────
        self._tab_memory(nb)

        # ── Tab 5: Install ────────────────────────────────────────────────────
        self._tab_install(nb)

        # status bar
        self._status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status, relief="sunken", anchor="w"
                  ).pack(fill="x", side="bottom", ipady=2)

        self._sel: Tool | None = None

    # ── tab builders ──────────────────────────────────────────────────────────

    def _tab_detail(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Tool Detail")

        self._det_name = ttk.Label(f, text="Select a tool",
                                   font=("Helvetica", 14, "bold"))
        self._det_name.pack(anchor="w")
        self._det_desc = ttk.Label(f, text="", wraplength=580)
        self._det_desc.pack(anchor="w", pady=2)

        info = ttk.LabelFrame(f, text="Info", padding=6)
        info.pack(fill="x", pady=4)
        self._info: dict[str, tk.StringVar] = {}
        for lbl in ("author", "license", "homepage", "install_type", "notes"):
            row = ttk.Frame(info)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=f"{lbl.capitalize()}:", width=14, anchor="e").pack(side="left")
            v = tk.StringVar()
            self._info[lbl] = v
            ttk.Label(row, textvariable=v, wraplength=460).pack(side="left", padx=4)

        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=6)
        self._launch_btn = ttk.Button(btns, text="▶  Launch", command=self._launch_selected, state="disabled")
        self._launch_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Open Dir", command=self._open_tool_dir).pack(side="left", padx=4)
        ttk.Button(btns, text="Copy URL", command=self._copy_url).pack(side="left", padx=4)

        self._det_log = scrolledtext.ScrolledText(f, height=14, state="disabled",
                                                   font=("Monospace", 9))
        self._det_log.pack(fill="both", expand=True, pady=4)

    def _tab_phone(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="📱 Phone Triage")

        ttk.Label(f, text="Live Android / iOS Device Triage",
                  font=("Helvetica", 13, "bold")).pack(anchor="w")
        ttk.Label(f, text=(
            "Plug in your authorized test device (USB Debugging ON).\n"
            "ForensicX will detect it automatically."
        )).pack(anchor="w", pady=2)

        # device list
        dev_frame = ttk.LabelFrame(f, text="Connected Devices", padding=6)
        dev_frame.pack(fill="x", pady=4)
        cols = ("serial", "state", "model", "android", "sdk")
        self._dev_tree = ttk.Treeview(dev_frame, columns=cols, show="headings", height=4)
        for col, w, txt in (
            ("serial", 140, "Serial"),
            ("state",   80, "State"),
            ("model",  180, "Model"),
            ("android", 80, "Android"),
            ("sdk",      60, "SDK"),
        ):
            self._dev_tree.heading(col, text=txt)
            self._dev_tree.column(col, width=w)
        self._dev_tree.pack(fill="x")
        self._dev_tree.tag_configure("ready", foreground=PALETTE["ready"])
        self._dev_tree.tag_configure("notready", foreground=PALETTE["missing"])

        ttk.Button(dev_frame, text="Refresh Devices",
                   command=lambda: self._monitor.refresh_once()).pack(anchor="w", pady=4)

        # triage options
        opt_frame = ttk.LabelFrame(f, text="Triage Options", padding=6)
        opt_frame.pack(fill="x", pady=4)
        self._run_alex = tk.BooleanVar(value=True)
        self._run_triage = tk.BooleanVar(value=True)
        self._run_aleapp = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="ALEX  (logical extraction via ADB)",
                        variable=self._run_alex).pack(anchor="w")
        ttk.Checkbutton(opt_frame, text="android_triage  (ADB triage script)",
                        variable=self._run_triage).pack(anchor="w")
        ttk.Checkbutton(opt_frame, text="ALEAPP  (artifact parsing)",
                        variable=self._run_aleapp).pack(anchor="w")

        # case name
        cf = ttk.Frame(f)
        cf.pack(fill="x", pady=4)
        ttk.Label(cf, text="Case name:").pack(side="left")
        self._triage_case = ttk.Entry(cf, width=30)
        self._triage_case.insert(0, "android-triage-001")
        self._triage_case.pack(side="left", padx=6)

        # action buttons
        ab = ttk.Frame(f)
        ab.pack(fill="x", pady=6)
        self._triage_btn = ttk.Button(ab, text="▶  Start Android Triage",
                                       command=self._start_android_triage)
        self._triage_btn.pack(side="left", padx=4)
        ttk.Button(ab, text="▶  Start iOS Triage",
                   command=self._start_ios_triage).pack(side="left", padx=4)
        ttk.Button(ab, text="Open Output Dir",
                   command=lambda: self._open_dir(CASES_DIR)).pack(side="left", padx=4)

        # live output
        self._triage_log = scrolledtext.ScrolledText(f, height=18, state="disabled",
                                                      font=("Monospace", 9))
        self._triage_log.tag_configure("ok",   foreground=PALETTE["ready"])
        self._triage_log.tag_configure("err",  foreground=PALETTE["missing"])
        self._triage_log.tag_configure("info", foreground=PALETTE["device"])
        self._triage_log.pack(fill="both", expand=True, pady=4)

    def _tab_workspace(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Case Workspace")

        cf = ttk.LabelFrame(f, text="Create Case", padding=8)
        cf.pack(fill="x", pady=4)
        ttk.Label(cf, text="Case name:").grid(row=0, column=0, sticky="e", padx=4)
        self._ws_name = ttk.Entry(cf, width=30)
        self._ws_name.insert(0, "case-001")
        self._ws_name.grid(row=0, column=1, sticky="w")
        ttk.Label(cf, text="Investigator:").grid(row=1, column=0, sticky="e", padx=4)
        self._ws_inv = ttk.Entry(cf, width=30)
        self._ws_inv.insert(0, "Examiner")
        self._ws_inv.grid(row=1, column=1, sticky="w")
        self._ws_path = tk.StringVar()
        ttk.Label(cf, text="Output dir:").grid(row=2, column=0, sticky="e", padx=4)
        ttk.Entry(cf, textvariable=self._ws_path, width=50).grid(row=2, column=1, sticky="w")
        ttk.Button(cf, text="Create", command=self._create_case).grid(row=3, column=1, sticky="w", pady=4)

        hf = ttk.LabelFrame(f, text="Hash Evidence", padding=8)
        hf.pack(fill="x", pady=4)
        self._ev_path = tk.StringVar()
        ttk.Entry(hf, textvariable=self._ev_path, width=60).pack(side="left", padx=4)
        ttk.Button(hf, text="Browse…", command=self._pick_evidence).pack(side="left", padx=2)
        ttk.Button(hf, text="SHA-256", command=self._hash_evidence).pack(side="left", padx=2)
        ttk.Button(hf, text="Import to Case", command=self._import_evidence).pack(side="left", padx=2)
        self._hash_lbl = ttk.Label(f, text="", font=("Monospace", 9))
        self._hash_lbl.pack(anchor="w", pady=2)

        self._ws_log = scrolledtext.ScrolledText(f, height=20, state="disabled",
                                                  font=("Monospace", 9))
        self._ws_log.pack(fill="both", expand=True)

    def _tab_memory(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Memory Analysis")

        ttk.Label(f, text="Volatility 3 — Memory Dump Analysis",
                  font=("Helvetica", 13, "bold")).pack(anchor="w")

        dump_f = ttk.LabelFrame(f, text="Memory dump", padding=6)
        dump_f.pack(fill="x", pady=4)
        self._dump_path = tk.StringVar()
        ttk.Entry(dump_f, textvariable=self._dump_path, width=70).pack(side="left", padx=4)
        ttk.Button(dump_f, text="Browse…", command=self._pick_dump).pack(side="left", padx=2)

        case_f = ttk.LabelFrame(f, text="Output", padding=6)
        case_f.pack(fill="x", pady=4)
        ttk.Label(case_f, text="Case dir:").pack(side="left")
        self._mem_case = ttk.Entry(case_f, width=50)
        self._mem_case.insert(0, str(CASES_DIR / "memory_analysis"))
        self._mem_case.pack(side="left", padx=4)

        ab = ttk.Frame(f)
        ab.pack(fill="x", pady=6)
        ttk.Button(ab, text="▶  Run Volatility 3", command=self._run_volatility).pack(side="left", padx=4)
        ttk.Button(ab, text="Open Vol3 GUI", command=lambda: self._launch_by_name("volatility3")).pack(side="left", padx=4)

        self._mem_log = scrolledtext.ScrolledText(f, height=22, state="disabled",
                                                   font=("Monospace", 9))
        self._mem_log.pack(fill="both", expand=True)

    def _tab_install(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Install Tools")

        ttk.Label(f, text="Install / Update Forensic Tools",
                  font=("Helvetica", 13, "bold")).pack(anchor="w")
        ttk.Label(f, text=(
            "scripts/install_tools.sh clones all git tools, creates venvs, and "
            "downloads pre-built binaries.\n"
            "apt tools require sudo. Binary/manual tools: see Tool Detail → homepage."
        ), wraplength=700).pack(anchor="w", pady=4)

        stats = ttk.LabelFrame(f, text="Registry summary", padding=6)
        stats.pack(fill="x", pady=4)
        summary = "  ".join(
            f"{cat}: {len(tools)}" for cat, tools in CATEGORIES.items()
        )
        ttk.Label(stats, text=f"Total tools: {len(ALL_TOOLS)}", font=("Helvetica", 10, "bold")).pack(anchor="w")
        ttk.Label(stats, text=summary, wraplength=700).pack(anchor="w")

        ib = ttk.Frame(f)
        ib.pack(fill="x", pady=4)
        ttk.Button(ib, text="Run install_tools.sh", command=self._run_installer).pack(side="left", padx=4)
        ttk.Button(ib, text="apt install (sudo)", command=self._install_apt).pack(side="left", padx=4)
        ttk.Button(ib, text="pip install", command=self._install_pip).pack(side="left", padx=4)
        ttk.Button(ib, text="Refresh Status", command=self._refresh_tools).pack(side="left", padx=4)

        self._inst_log = scrolledtext.ScrolledText(f, height=26, state="disabled",
                                                    font=("Monospace", 9))
        self._inst_log.tag_configure("ok",   foreground=PALETTE["ready"])
        self._inst_log.tag_configure("err",  foreground=PALETTE["missing"])
        self._inst_log.pack(fill="both", expand=True, pady=4)

    # ── tool list ─────────────────────────────────────────────────────────────

    def _refresh_tools(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        cat = self._cat_var.get()
        query = self._q.get().lower()
        tools = CATEGORIES.get(cat, [])
        if query:
            tools = [t for t in ALL_TOOLS
                     if query in t.name.lower() or query in t.description.lower()
                     or query in t.category.lower()]
        ready = missing = manual = 0
        for tool in tools:
            if tool.category == "commercial":
                status, tag = "COMMERCIAL", "commercial"
            elif tool.is_installed:
                status, tag = "✓ READY", "ready"
                ready += 1
            elif tool.install_type == "manual":
                status, tag = "MANUAL", "manual"
                manual += 1
            else:
                status, tag = "NOT INSTALLED", "missing"
                missing += 1
            self._tree.insert("", "end", iid=tool.name,
                              values=(status, tool.name, tool.install_type, tool.description),
                              tags=(tag,))
        self._status.set(
            f"{len(tools)} tools  |  ✓ {ready} ready  |  ✗ {missing} not installed  |  "
            f"{manual} manual  |  Total registered: {len(ALL_TOOLS)}"
        )

    def _on_select(self, _: object) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        from forensicx_hub.tools_registry import TOOL_BY_NAME
        tool = TOOL_BY_NAME.get(sel[0])
        if not tool:
            return
        self._sel = tool
        self._det_name.config(text=tool.name)
        self._det_desc.config(text=tool.description)
        for k in ("author", "license", "homepage", "install_type", "notes"):
            self._info[k].set(getattr(tool, k, ""))
        self._launch_btn.config(
            state="normal" if (tool.is_installed and tool.install_type != "commercial") else "disabled"
        )

    # ── launch ────────────────────────────────────────────────────────────────

    def _launch_selected(self) -> None:
        if self._sel:
            self._launch_tool(self._sel)

    def _launch_by_name(self, name: str) -> None:
        from forensicx_hub.tools_registry import TOOL_BY_NAME
        tool = TOOL_BY_NAME.get(name)
        if not tool:
            messagebox.showerror("Not found", f"Tool {name!r} not registered.")
            return
        if not tool.is_installed:
            messagebox.showwarning("Not installed",
                                   f"{name} is not installed.\nRun scripts/install_tools.sh first.")
            return
        self._launch_tool(tool)

    def _launch_tool(self, tool: Tool) -> None:
        if tool.install_type == "commercial":
            messagebox.showinfo("Commercial tool",
                                f"{tool.name} is proprietary software.\n{tool.notes}\n\n{tool.homepage}")
            return
        cmd = resolve_cmd(tool)
        case_out = self._ws_path.get().strip() or str(CASES_DIR / self._ws_name.get().strip())
        Path(case_out).mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["FORENSICX_OUTPUT"] = case_out
        _log(self._det_log, f"[LAUNCH] {tool.name}")
        _log(self._det_log, f"  cmd: {' '.join(cmd)}")
        _log(self._det_log, f"  output: {case_out}")
        self._status.set(f"Launching {tool.name}…")
        try:
            subprocess.Popen(cmd, env=env,
                             cwd=str(tool.tool_dir if tool.tool_dir.exists() else ROOT))
        except Exception as exc:
            messagebox.showerror("Launch error", str(exc))

    # ── phone triage ──────────────────────────────────────────────────────────

    def _on_device_attach(self, dev: AndroidDevice) -> None:
        self._triage_log.after(0, lambda: _log(
            self._triage_log,
            f"[DEVICE ATTACHED] {dev.display_name}  state={dev.state}",
            "ok" if dev.is_ready else "err",
        ))
        if dev.is_ready:
            self._device_badge.after(0, lambda: self._device_badge.config(
                text=f"📱  {dev.display_name}",
                fg=PALETTE["ready"],
            ))

    def _on_device_detach(self, serial: str) -> None:
        self._triage_log.after(0, lambda: _log(
            self._triage_log, f"[DEVICE DETACHED] {serial}", "err"
        ))
        self._device_badge.after(0, lambda: self._device_badge.config(
            text="No devices", fg="#aaaaaa"
        ))

    def _on_devices_update(self, devices: list[AndroidDevice]) -> None:
        def _do() -> None:
            for row in self._dev_tree.get_children():
                self._dev_tree.delete(row)
            for d in devices:
                tag = "ready" if d.is_ready else "notready"
                self._dev_tree.insert("", "end", iid=d.serial,
                                      values=(d.serial, d.state, d.model,
                                              d.android_version, d.sdk_version),
                                      tags=(tag,))
            if devices:
                ready = [d for d in devices if d.is_ready]
                if ready:
                    self._device_badge.config(
                        text=f"📱  {len(ready)} device(s) ready",
                        fg=PALETTE["ready"],
                    )
            else:
                self._device_badge.config(text="No devices", fg="#aaaaaa")
        self._dev_tree.after(0, _do)

    def _start_android_triage(self) -> None:
        devices = self._monitor.devices
        ready = [d for d in devices if d.is_ready]
        if not ready:
            messagebox.showwarning("No device",
                                   "No authorized Android device connected.\n\n"
                                   "Enable USB Debugging on your test device and connect via USB.")
            return
        serial = ready[0].serial
        case_dir = CASES_DIR / self._triage_case.get().strip()
        case_dir.mkdir(parents=True, exist_ok=True)
        run_alex = self._run_alex.get()
        run_triage = self._run_triage.get()
        run_aleapp = self._run_aleapp.get()

        _log(self._triage_log, f"Starting triage on {serial}  case={case_dir}", "info")

        def _run() -> None:
            from forensicx_hub.workflow import android_triage_workflow
            for step, msg in android_triage_workflow(
                serial=serial,
                case_dir=case_dir,
                run_alex=run_alex,
                run_triage=run_triage,
                run_aleapp=run_aleapp,
            ):
                tag = "ok" if step == "done" else "err" if "error" in msg.lower() else ""
                _log(self._triage_log, f"[{step.upper()}] {msg}", tag)
            self._status.set("Android triage complete.")
            self._triage_btn.after(0, lambda: self._triage_btn.config(state="normal"))

        self._triage_btn.config(state="disabled")
        threading.Thread(target=_run, daemon=True).start()

    def _start_ios_triage(self) -> None:
        case_dir = CASES_DIR / self._triage_case.get().strip()
        case_dir.mkdir(parents=True, exist_ok=True)
        _log(self._triage_log, "Starting iOS triage…", "info")

        def _run() -> None:
            from forensicx_hub.workflow import ios_triage_workflow
            for step, msg in ios_triage_workflow(case_dir):
                _log(self._triage_log, f"[{step.upper()}] {msg}")
            self._status.set("iOS triage complete.")

        threading.Thread(target=_run, daemon=True).start()

    # ── memory analysis ───────────────────────────────────────────────────────

    def _pick_dump(self) -> None:
        p = filedialog.askopenfilename(title="Select memory dump")
        if p:
            self._dump_path.set(p)

    def _run_volatility(self) -> None:
        dump = self._dump_path.get().strip()
        if not dump or not Path(dump).exists():
            messagebox.showwarning("No dump", "Select a memory dump file first.")
            return
        case_dir = Path(self._mem_case.get().strip())
        case_dir.mkdir(parents=True, exist_ok=True)
        _log(self._mem_log, f"Volatility 3 on {dump}", "")

        def _run() -> None:
            from forensicx_hub.workflow import memory_triage_workflow
            for step, msg in memory_triage_workflow(Path(dump), case_dir):
                _log(self._mem_log, f"[{step.upper()}] {msg}")
            self._status.set("Memory analysis complete.")

        threading.Thread(target=_run, daemon=True).start()

    # ── workspace ─────────────────────────────────────────────────────────────

    def _create_case(self) -> None:
        name = self._ws_name.get().strip()
        p = CASES_DIR / name
        for sub in ("evidence", "reports", "exports", "tool_output"):
            (p / sub).mkdir(parents=True, exist_ok=True)
        self._ws_path.set(str(p))
        try:
            from forensicx.core import database as db
            inv = self._ws_inv.get().strip() or "Examiner"
            case = db.create_case(name=name, investigator=inv)
            _log(self._ws_log, f"Case #{case.id} '{case.name}' created at {p}")
        except Exception as exc:
            _log(self._ws_log, f"DB case not created: {exc}")
            _log(self._ws_log, f"Folder created at {p}")
        self._status.set(f"Case created: {p}")

    def _pick_evidence(self) -> None:
        p = filedialog.askopenfilename(title="Select evidence file")
        if p:
            self._ev_path.set(p)

    def _hash_evidence(self) -> None:
        path = self._ev_path.get().strip()
        if not path or not Path(path).exists():
            messagebox.showwarning("No file", "Select a file first.")
            return
        def _run() -> None:
            digest = sha256_file(path)
            self._hash_lbl.after(0, lambda: self._hash_lbl.config(text=f"SHA-256: {digest}"))
            _log(self._ws_log, f"SHA-256  {path}\n  {digest}")
            self._status.set("Hash complete")
        threading.Thread(target=_run, daemon=True).start()

    def _import_evidence(self) -> None:
        path = self._ev_path.get().strip()
        if not path or not Path(path).exists():
            messagebox.showwarning("No file", "Select a file first.")
            return
        try:
            from forensicx.core import database as db
            cases = db.list_cases()
            if not cases:
                messagebox.showwarning("No cases", "Create a case first.")
                return
            case = cases[-1]
            from forensicx.services.evidence import import_evidence
            ev = import_evidence(case_id=case.id, file_path=path)
            _log(self._ws_log, f"Imported evidence #{ev.id}: {ev.filename}  sha256={ev.sha256[:16]}…")
        except Exception as exc:
            _log(self._ws_log, f"Import error: {exc}")

    # ── misc ──────────────────────────────────────────────────────────────────

    def _open_tool_dir(self) -> None:
        if self._sel:
            self._sel.tool_dir.mkdir(parents=True, exist_ok=True)
            self._open_dir(self._sel.tool_dir)

    def _open_dir(self, d: Path) -> None:
        d.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(d))
            else:
                subprocess.Popen(["xdg-open", str(d)])
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _copy_url(self) -> None:
        if self._sel:
            self.clipboard_clear()
            self.clipboard_append(self._sel.homepage)
            self._status.set(f"Copied: {self._sel.homepage}")

    def _run_installer(self) -> None:
        script = ROOT / "scripts" / "install_tools.sh"
        if not script.exists():
            messagebox.showerror("Missing", str(script))
            return
        _log(self._inst_log, f"Running {script}…")
        self._stream(["bash", str(script)], self._inst_log)

    def _install_apt(self) -> None:
        pkgs = [t.entry_point for t in ALL_TOOLS
                if t.install_type == "apt" and not t.is_installed]
        if not pkgs:
            _log(self._inst_log, "All apt tools already installed.")
            return
        _log(self._inst_log, f"apt install: {' '.join(pkgs[:8])}…")
        self._stream(["sudo", "apt-get", "install", "-y"] + pkgs, self._inst_log)

    def _install_pip(self) -> None:
        pkgs = [t.name for t in ALL_TOOLS
                if t.install_type == "pip" and not t.is_installed]
        if not pkgs:
            _log(self._inst_log, "All pip tools already installed.")
            return
        _log(self._inst_log, f"pip install: {' '.join(pkgs)}")
        self._stream([sys.executable, "-m", "pip", "install", "--upgrade"] + pkgs, self._inst_log)

    def _stream(self, cmd: list[str], output: scrolledtext.ScrolledText) -> None:
        def _run() -> None:
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:  # type: ignore[union-attr]
                    _log(output, line.rstrip())
                proc.wait()
                _log(output, f"\n[DONE] exit {proc.returncode}",
                     "ok" if proc.returncode == 0 else "err")
                self.after(0, self._refresh_tools)
            except Exception as exc:
                _log(output, f"[ERROR] {exc}", "err")
        threading.Thread(target=_run, daemon=True).start()

    def _show_about(self) -> None:
        messagebox.showinfo("About ForensicX Hub",
                            f"ForensicX Forensic Tool Hub\n\n"
                            f"Registered tools: {len(ALL_TOOLS)}\n"
                            f"Categories: {len(CATEGORIES)}\n\n"
                            "Use only on authorized evidence.\n"
                            "https://github.com/ammadahmed9001/forensicx")

    def _on_close(self) -> None:
        self._monitor.stop()
        self.destroy()


def run_hub() -> None:
    app = ForensicXHub()
    app.mainloop()


if __name__ == "__main__":
    run_hub()
