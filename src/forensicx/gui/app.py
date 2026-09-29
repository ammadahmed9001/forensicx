"""Tkinter GUI application."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from forensicx.core import database as db
from forensicx.services.evidence import import_evidence
from forensicx.services.reports import export_case_json


class ForensicXApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ForensicX")
        self.geometry("1000x650")
        self._build_ui()
        self.refresh_cases()

    def _build_ui(self) -> None:
        # ── top bar ──────────────────────────────────────────────────────────
        bar = ttk.Frame(self, padding=6)
        bar.pack(fill="x", side="top")
        ttk.Label(bar, text="ForensicX", font=("Helvetica", 16, "bold")).pack(side="left")

        # ── paned layout ─────────────────────────────────────────────────────
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=6)

        # Left — case list
        left = ttk.Frame(pane, padding=4)
        pane.add(left, weight=1)
        ttk.Label(left, text="Cases", font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.case_tree = ttk.Treeview(left, columns=("id", "name", "investigator"), show="headings")
        for col, w in (("id", 40), ("name", 180), ("investigator", 100)):
            self.case_tree.heading(col, text=col.capitalize())
            self.case_tree.column(col, width=w)
        self.case_tree.pack(fill="both", expand=True)
        self.case_tree.bind("<<TreeviewSelect>>", self._on_case_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=4)
        ttk.Button(btn_row, text="New Case", command=self._new_case).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Refresh", command=self.refresh_cases).pack(side="left", padx=2)

        # Right — evidence + search
        right = ttk.Frame(pane, padding=4)
        pane.add(right, weight=3)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # Evidence tab
        ev_frame = ttk.Frame(nb, padding=4)
        nb.add(ev_frame, text="Evidence")
        ttk.Button(ev_frame, text="Import File…", command=self._import_evidence).pack(anchor="w", pady=4)
        self.ev_tree = ttk.Treeview(
            ev_frame,
            columns=("id", "filename", "parser", "sha256", "size"),
            show="headings",
        )
        for col, w in (("id", 40), ("filename", 200), ("parser", 100), ("sha256", 160), ("size", 80)):
            self.ev_tree.heading(col, text=col.capitalize())
            self.ev_tree.column(col, width=w)
        self.ev_tree.pack(fill="both", expand=True)

        # Search tab
        search_frame = ttk.Frame(nb, padding=4)
        nb.add(search_frame, text="Search")
        sq = ttk.Frame(search_frame)
        sq.pack(fill="x", pady=4)
        self.search_var = tk.StringVar()
        ttk.Entry(sq, textvariable=self.search_var, width=40).pack(side="left", padx=2)
        ttk.Button(sq, text="Search", command=self._do_search).pack(side="left", padx=2)
        self.search_tree = ttk.Treeview(
            search_frame,
            columns=("id", "type", "source", "content"),
            show="headings",
        )
        for col, w in (("id", 40), ("type", 100), ("source", 160), ("content", 400)):
            self.search_tree.heading(col, text=col.capitalize())
            self.search_tree.column(col, width=w)
        self.search_tree.pack(fill="both", expand=True)

        # Report tab
        rep_frame = ttk.Frame(nb, padding=4)
        nb.add(rep_frame, text="Report")
        ttk.Button(rep_frame, text="Export JSON Report…", command=self._export_report).pack(anchor="w", pady=4)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

        self._selected_case_id: int | None = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def refresh_cases(self) -> None:
        for row in self.case_tree.get_children():
            self.case_tree.delete(row)
        for c in db.list_cases():
            self.case_tree.insert("", "end", values=(c.id, c.name, c.investigator))

    def _on_case_select(self, _event: object) -> None:
        sel = self.case_tree.selection()
        if not sel:
            return
        self._selected_case_id = int(self.case_tree.item(sel[0])["values"][0])
        self._refresh_evidence()
        self.status_var.set(f"Selected case #{self._selected_case_id}")

    def _refresh_evidence(self) -> None:
        for row in self.ev_tree.get_children():
            self.ev_tree.delete(row)
        if self._selected_case_id is None:
            return
        for e in db.list_evidence(self._selected_case_id):
            self.ev_tree.insert(
                "", "end",
                values=(e.id, e.filename, e.parser, e.sha256[:16] + "…", f"{e.size_bytes:,}"),
            )

    def _new_case(self) -> None:
        dlg = _NewCaseDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            db.create_case(**dlg.result)
            self.refresh_cases()
            self.status_var.set("Case created.")

    def _import_evidence(self) -> None:
        if self._selected_case_id is None:
            messagebox.showwarning("No case selected", "Please select a case first.")
            return
        path = filedialog.askopenfilename(title="Select evidence file")
        if not path:
            return
        try:
            ev = import_evidence(case_id=self._selected_case_id, file_path=path)
            self._refresh_evidence()
            self.status_var.set(f"Imported: {ev.filename}")
        except Exception as exc:
            messagebox.showerror("Import error", str(exc))

    def _do_search(self) -> None:
        if self._selected_case_id is None:
            messagebox.showwarning("No case selected", "Please select a case first.")
            return
        query = self.search_var.get().strip()
        if not query:
            return
        for row in self.search_tree.get_children():
            self.search_tree.delete(row)
        results = db.search_artifacts(self._selected_case_id, query)
        for r in results:
            self.search_tree.insert("", "end", values=(r.id, r.artifact_type, r.source, r.content[:120]))
        self.status_var.set(f"{len(results)} result(s) for {query!r}")

    def _export_report(self) -> None:
        if self._selected_case_id is None:
            messagebox.showwarning("No case selected", "Please select a case first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save report", defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            out = export_case_json(self._selected_case_id, path)
            self.status_var.set(f"Report saved: {out}")
        except Exception as exc:
            messagebox.showerror("Report error", str(exc))


class _NewCaseDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("New Case")
        self.resizable(False, False)
        self.result: dict | None = None
        self._build()
        self.grab_set()

    def _build(self) -> None:
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Case name:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self._name = ttk.Entry(f, width=30)
        self._name.grid(row=0, column=1, pady=4)
        ttk.Label(f, text="Investigator:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self._inv = ttk.Entry(f, width=30)
        self._inv.grid(row=1, column=1, pady=4)
        ttk.Label(f, text="Notes:").grid(row=2, column=0, sticky="ne", padx=4, pady=4)
        self._notes = tk.Text(f, width=30, height=4)
        self._notes.grid(row=2, column=1, pady=4)
        btns = ttk.Frame(f)
        btns.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Create", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _ok(self) -> None:
        name = self._name.get().strip()
        inv = self._inv.get().strip() or "Unknown"
        notes = self._notes.get("1.0", "end-1c").strip()
        if not name:
            messagebox.showwarning("Required", "Case name is required.", parent=self)
            return
        self.result = {"name": name, "investigator": inv, "notes": notes}
        self.destroy()


def run_gui() -> None:
    app = ForensicXApp()
    app.mainloop()
