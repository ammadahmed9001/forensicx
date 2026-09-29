"""
ForensicX Hub — comprehensive forensic tool launcher.
Tkinter-based GUI; zero Qt dependency.
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

from forensicx_hub.tools_registry import ALL_TOOLS, CATEGORIES, Tool

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "cases"
TOOLS_DIR = ROOT / "tools"


# ── helpers ───────────────────────────────────────────────────────────────────

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def adb_devices() -> str:
    try:
        r = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=8)
        return r.stdout.strip() or r.stderr.strip() or "No output"
    except FileNotFoundError:
        return "adb not found — install android-tools-adb"
    except Exception as exc:
        return f"Error: {exc}"


def resolve_cmd(tool: Tool) -> list[str]:
    td = str(tool.tool_dir)
    return [p.replace("{TOOL_DIR}", td) for p in tool.launch_cmd]


# ── main window ───────────────────────────────────────────────────────────────

class ForensicXHub(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ForensicX — Forensic Tool Hub")
        self.geometry("1400x820")
        self._build_ui()
        self.after(100, self._refresh_all)

    def _build_ui(self) -> None:
        # ── menu bar ──────────────────────────────────────────────────────────
        mb = tk.Menu(self)
        tools_m = tk.Menu(mb, tearoff=0)
        tools_m.add_command(label="Refresh tool status", command=self._refresh_all)
        tools_m.add_command(label="Open tools directory", command=lambda: os.startfile(str(TOOLS_DIR)) if sys.platform == "win32" else subprocess.Popen(["xdg-open", str(TOOLS_DIR)]))
        mb.add_cascade(label="Tools", menu=tools_m)
        help_m = tk.Menu(mb, tearoff=0)
        help_m.add_command(label="About ForensicX", command=self._show_about)
        mb.add_cascade(label="Help", menu=help_m)
        self.config(menu=mb)

        # ── top banner ────────────────────────────────────────────────────────
        banner = ttk.Frame(self, padding=(12, 6))
        banner.pack(fill="x")
        ttk.Label(banner, text="ForensicX  |  Open-Source Forensic Tool Hub",
                  font=("Helvetica", 18, "bold")).pack(side="left")
        ttk.Label(banner, text="Use only on devices / evidence you are authorized to examine.",
                  foreground="red").pack(side="right", padx=8)

        # ── main pane ─────────────────────────────────────────────────────────
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=6)

        # LEFT: category + tool list
        left = ttk.Frame(pane, padding=4)
        pane.add(left, weight=2)

        ttk.Label(left, text="Category", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self._cat_var = tk.StringVar(value=list(CATEGORIES.keys())[0])
        cat_cb = ttk.Combobox(left, textvariable=self._cat_var,
                              values=list(CATEGORIES.keys()), state="readonly", width=28)
        cat_cb.pack(fill="x", pady=2)
        cat_cb.bind("<<ComboboxSelected>>", lambda _e: self._populate_tools())

        search_frame = ttk.Frame(left)
        search_frame.pack(fill="x", pady=4)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._populate_tools())
        ttk.Entry(search_frame, textvariable=self._search_var).pack(side="left", fill="x", expand=True, padx=4)

        cols = ("status", "name", "description", "license")
        self._tool_tree = ttk.Treeview(left, columns=cols, show="headings", height=28)
        for col, w, anchor in (
            ("status", 80, "center"),
            ("name", 130, "w"),
            ("description", 380, "w"),
            ("license", 90, "center"),
        ):
            self._tool_tree.heading(col, text=col.capitalize())
            self._tool_tree.column(col, width=w, anchor=anchor)
        self._tool_tree.tag_configure("ready", foreground="#22aa22")
        self._tool_tree.tag_configure("missing", foreground="#cc4400")
        self._tool_tree.tag_configure("manual", foreground="#888800")
        sb = ttk.Scrollbar(left, orient="vertical", command=self._tool_tree.yview)
        self._tool_tree.configure(yscrollcommand=sb.set)
        self._tool_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self._tool_tree.bind("<<TreeviewSelect>>", self._on_tool_select)
        self._tool_tree.bind("<Double-1>", lambda _e: self._launch_selected())

        # RIGHT: tool detail + workspace + ADB
        right = ttk.Frame(pane, padding=4)
        pane.add(right, weight=3)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # ── Tool Detail tab ───────────────────────────────────────────────────
        detail_frame = ttk.Frame(nb, padding=8)
        nb.add(detail_frame, text="Tool Detail")

        self._detail_name = ttk.Label(detail_frame, text="Select a tool",
                                      font=("Helvetica", 14, "bold"))
        self._detail_name.pack(anchor="w")
        self._detail_desc = ttk.Label(detail_frame, text="", wraplength=560)
        self._detail_desc.pack(anchor="w", pady=2)

        info_frame = ttk.LabelFrame(detail_frame, text="Info", padding=6)
        info_frame.pack(fill="x", pady=4)
        self._info_vars: dict[str, tk.StringVar] = {}
        for lbl in ("author", "license", "homepage", "install_type", "notes"):
            row = ttk.Frame(info_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=f"{lbl.capitalize()}:", width=14, anchor="e").pack(side="left")
            var = tk.StringVar()
            self._info_vars[lbl] = var
            ttk.Label(row, textvariable=var, wraplength=440).pack(side="left", padx=4)

        btn_row = ttk.Frame(detail_frame)
        btn_row.pack(fill="x", pady=8)
        self._launch_btn = ttk.Button(btn_row, text="Launch Tool", command=self._launch_selected, state="disabled")
        self._launch_btn.pack(side="left", padx=4)
        ttk.Button(btn_row, text="Open in File Manager", command=self._open_tool_dir).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Copy Homepage URL", command=self._copy_homepage).pack(side="left", padx=4)

        self._log = scrolledtext.ScrolledText(detail_frame, height=12, state="disabled",
                                               font=("Monospace", 9))
        self._log.pack(fill="both", expand=True, pady=4)

        # ── Case Workspace tab ────────────────────────────────────────────────
        ws_frame = ttk.Frame(nb, padding=8)
        nb.add(ws_frame, text="Case Workspace")

        cf = ttk.LabelFrame(ws_frame, text="Case", padding=8)
        cf.pack(fill="x", pady=4)
        ttk.Label(cf, text="Case name:").grid(row=0, column=0, sticky="e", padx=4)
        self._case_name = ttk.Entry(cf, width=30)
        self._case_name.insert(0, "case-001")
        self._case_name.grid(row=0, column=1, sticky="w")
        self._case_path_var = tk.StringVar()
        ttk.Label(cf, text="Output dir:").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Entry(cf, textvariable=self._case_path_var, width=50).grid(row=1, column=1, sticky="w")
        ttk.Button(cf, text="Create Case Folder", command=self._create_case).grid(row=2, column=1, sticky="w", pady=4)

        hf = ttk.LabelFrame(ws_frame, text="Hash Evidence File", padding=8)
        hf.pack(fill="x", pady=4)
        self._ev_path_var = tk.StringVar()
        ttk.Entry(hf, textvariable=self._ev_path_var, width=60).pack(side="left", padx=4)
        ttk.Button(hf, text="Browse…", command=self._pick_evidence).pack(side="left", padx=2)
        ttk.Button(hf, text="SHA-256", command=self._hash_evidence).pack(side="left", padx=2)
        self._hash_result = ttk.Label(ws_frame, text="", font=("Monospace", 9))
        self._hash_result.pack(anchor="w", pady=2)

        # Case log output
        self._ws_log = scrolledtext.ScrolledText(ws_frame, height=18, state="disabled",
                                                  font=("Monospace", 9))
        self._ws_log.pack(fill="both", expand=True)

        # ── ADB / Android tab ─────────────────────────────────────────────────
        adb_frame = ttk.Frame(nb, padding=8)
        nb.add(adb_frame, text="Android / ADB")

        ttk.Label(adb_frame, text="ADB Device Status", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(adb_frame, text="Ensure USB Debugging is enabled on the authorized test device.").pack(anchor="w")
        self._adb_text = scrolledtext.ScrolledText(adb_frame, height=12, state="disabled",
                                                    font=("Monospace", 9))
        self._adb_text.pack(fill="both", expand=True, pady=4)

        ab = ttk.Frame(adb_frame)
        ab.pack(fill="x")
        ttk.Button(ab, text="Refresh ADB Devices", command=self._refresh_adb).pack(side="left", padx=4)
        ttk.Button(ab, text="Launch ALEX (Android Acquisition)", command=lambda: self._launch_by_name("ALEX")).pack(side="left", padx=4)
        ttk.Button(ab, text="Launch android_triage", command=lambda: self._launch_by_name("android_triage")).pack(side="left", padx=4)

        # ── Install tab ───────────────────────────────────────────────────────
        install_frame = ttk.Frame(nb, padding=8)
        nb.add(install_frame, text="Install Tools")

        ttk.Label(install_frame, text="Install open-source forensic tools",
                  font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(install_frame, text=(
            "Run scripts/install_tools.sh to clone and install all git-based tools.\n"
            "apt-based tools can be installed with the button below (requires sudo).\n"
            "Binary/manual tools: see the Tool Detail tab for download links."
        ), wraplength=600).pack(anchor="w", pady=6)

        ib = ttk.Frame(install_frame)
        ib.pack(fill="x")
        ttk.Button(ib, text="Run install_tools.sh", command=self._run_installer).pack(side="left", padx=4)
        ttk.Button(ib, text="Install apt tools (sudo)", command=self._install_apt).pack(side="left", padx=4)
        ttk.Button(ib, text="Install pip tools", command=self._install_pip).pack(side="left", padx=4)

        self._install_log = scrolledtext.ScrolledText(install_frame, height=24, state="disabled",
                                                       font=("Monospace", 9))
        self._install_log.pack(fill="both", expand=True, pady=6)

        # ── status bar ────────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom", ipady=2)

        self._selected_tool: Tool | None = None

    # ── tool list ─────────────────────────────────────────────────────────────

    def _populate_tools(self) -> None:
        for row in self._tool_tree.get_children():
            self._tool_tree.delete(row)
        cat = self._cat_var.get()
        query = self._search_var.get().lower()
        tools = CATEGORIES.get(cat, [])
        if query:
            tools = [t for t in ALL_TOOLS if query in t.name.lower() or query in t.description.lower()]
        for tool in tools:
            if tool.is_installed:
                status, tag = "READY", "ready"
            elif tool.install_type == "manual":
                status, tag = "MANUAL", "manual"
            else:
                status, tag = "NOT INSTALLED", "missing"
            self._tool_tree.insert("", "end", iid=tool.name,
                                   values=(status, tool.name, tool.description, tool.license),
                                   tags=(tag,))

    def _refresh_all(self) -> None:
        self._populate_tools()
        self._refresh_adb()
        self._status_var.set(f"Tools loaded: {len(ALL_TOOLS)} across {len(CATEGORIES)} categories")

    def _on_tool_select(self, _event: object) -> None:
        sel = self._tool_tree.selection()
        if not sel:
            return
        name = sel[0]
        from forensicx_hub.tools_registry import TOOL_BY_NAME
        tool = TOOL_BY_NAME.get(name)
        if not tool:
            return
        self._selected_tool = tool
        self._detail_name.config(text=tool.name)
        self._detail_desc.config(text=tool.description)
        for key in ("author", "license", "homepage", "install_type", "notes"):
            self._info_vars[key].set(getattr(tool, key, ""))
        self._launch_btn.config(state="normal" if tool.is_installed else "disabled")
        self._status_var.set(f"Selected: {tool.name} — {tool.homepage}")

    # ── launch ────────────────────────────────────────────────────────────────

    def _launch_selected(self) -> None:
        if not self._selected_tool:
            return
        self._launch_tool(self._selected_tool)

    def _launch_by_name(self, name: str) -> None:
        from forensicx_hub.tools_registry import TOOL_BY_NAME
        tool = TOOL_BY_NAME.get(name)
        if not tool:
            messagebox.showerror("Not found", f"Tool {name!r} not in registry.")
            return
        if not tool.is_installed:
            messagebox.showwarning("Not installed",
                                   f"{name} is not installed.\nRun scripts/install_tools.sh first.")
            return
        self._launch_tool(tool)

    def _launch_tool(self, tool: Tool) -> None:
        cmd = resolve_cmd(tool)
        case_out = self._case_path_var.get().strip() or str(CASES_DIR / self._case_name.get().strip())
        Path(case_out).mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["FORENSICX_OUTPUT"] = case_out
        self._log_write(self._log, f"[LAUNCH] {tool.name}\n  cmd: {' '.join(cmd)}\n  output: {case_out}\n")
        self._status_var.set(f"Launching {tool.name}…")
        try:
            subprocess.Popen(cmd, env=env, cwd=str(tool.tool_dir if tool.tool_dir.exists() else ROOT))
        except Exception as exc:
            messagebox.showerror("Launch error", str(exc))

    # ── workspace ─────────────────────────────────────────────────────────────

    def _create_case(self) -> None:
        p = CASES_DIR / self._case_name.get().strip()
        for sub in ("evidence", "reports", "exports", "tool_output"):
            (p / sub).mkdir(parents=True, exist_ok=True)
        self._case_path_var.set(str(p))
        self._log_write(self._ws_log, f"Created case workspace: {p}\n")
        self._status_var.set(f"Case created: {p}")

    def _pick_evidence(self) -> None:
        path = filedialog.askopenfilename(title="Select evidence file")
        if path:
            self._ev_path_var.set(path)

    def _hash_evidence(self) -> None:
        path = self._ev_path_var.get().strip()
        if not path or not Path(path).exists():
            messagebox.showwarning("No file", "Select a file first.")
            return
        self._status_var.set("Hashing…")
        def _run() -> None:
            digest = sha256_file(path)
            self._hash_result.config(text=f"SHA-256: {digest}")
            self._log_write(self._ws_log, f"SHA-256 {path}\n  {digest}\n")
            self._status_var.set("Hash complete")
        threading.Thread(target=_run, daemon=True).start()

    # ── ADB ───────────────────────────────────────────────────────────────────

    def _refresh_adb(self) -> None:
        def _run() -> None:
            out = adb_devices()
            self._adb_text.config(state="normal")
            self._adb_text.delete("1.0", "end")
            self._adb_text.insert("end", out)
            self._adb_text.config(state="disabled")
        threading.Thread(target=_run, daemon=True).start()

    # ── install ───────────────────────────────────────────────────────────────

    def _run_installer(self) -> None:
        script = ROOT / "scripts" / "install_tools.sh"
        if not script.exists():
            messagebox.showerror("Missing", f"Installer not found: {script}")
            return
        self._log_write(self._install_log, f"Running {script}…\n")
        self._run_cmd_streaming(["bash", str(script)], self._install_log)

    def _install_apt(self) -> None:
        from forensicx_hub.tools_registry import ALL_TOOLS
        pkgs = [t.entry_point for t in ALL_TOOLS if t.install_type == "apt" and not t.is_installed]
        if not pkgs:
            self._log_write(self._install_log, "All apt tools already installed.\n")
            return
        cmd = ["sudo", "apt-get", "install", "-y"] + pkgs
        self._log_write(self._install_log, f"apt-get install: {' '.join(pkgs)}\n")
        self._run_cmd_streaming(cmd, self._install_log)

    def _install_pip(self) -> None:
        from forensicx_hub.tools_registry import ALL_TOOLS
        pkgs = [t.name for t in ALL_TOOLS if t.install_type == "pip" and not t.is_installed]
        if not pkgs:
            self._log_write(self._install_log, "All pip tools already installed.\n")
            return
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + pkgs
        self._log_write(self._install_log, f"pip install: {' '.join(pkgs)}\n")
        self._run_cmd_streaming(cmd, self._install_log)

    def _run_cmd_streaming(self, cmd: list[str], output: scrolledtext.ScrolledText) -> None:
        def _run() -> None:
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:  # type: ignore[union-attr]
                    self._log_write(output, line)
                proc.wait()
                self._log_write(output, f"\n[DONE] exit code {proc.returncode}\n")
                self._populate_tools()
            except Exception as exc:
                self._log_write(output, f"[ERROR] {exc}\n")
        threading.Thread(target=_run, daemon=True).start()

    # ── misc ──────────────────────────────────────────────────────────────────

    def _open_tool_dir(self) -> None:
        if not self._selected_tool:
            return
        d = self._selected_tool.tool_dir
        d.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(d))
            else:
                subprocess.Popen(["xdg-open", str(d)])
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _copy_homepage(self) -> None:
        if not self._selected_tool:
            return
        self.clipboard_clear()
        self.clipboard_append(self._selected_tool.homepage)
        self._status_var.set(f"Copied: {self._selected_tool.homepage}")

    def _show_about(self) -> None:
        messagebox.showinfo("About ForensicX Hub",
                            "ForensicX Forensic Tool Hub\n\n"
                            f"Registered tools: {len(ALL_TOOLS)}\n"
                            "Categories: " + ", ".join(CATEGORIES.keys()) + "\n\n"
                            "Use only on authorized evidence.")

    @staticmethod
    def _log_write(widget: scrolledtext.ScrolledText, text: str) -> None:
        widget.config(state="normal")
        widget.insert("end", text)
        widget.see("end")
        widget.config(state="disabled")


def run_hub() -> None:
    app = ForensicXHub()
    app.mainloop()


if __name__ == "__main__":
    run_hub()
