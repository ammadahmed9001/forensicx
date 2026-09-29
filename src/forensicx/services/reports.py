"""Report generation service."""
from __future__ import annotations

import json
from pathlib import Path

from forensicx.core import database as db
from forensicx.core.models import Case


def export_case_json(case_id: int, output_path: str | Path) -> Path:
    case = db.get_case(case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    evidence_list = db.list_evidence(case_id)
    report: dict = {
        "case": case.to_dict(),
        "evidence": [],
    }
    for ev in evidence_list:
        report["evidence"].append(ev.to_dict())

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    return out
