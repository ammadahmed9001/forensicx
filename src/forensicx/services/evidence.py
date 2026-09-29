"""Evidence import service."""
from __future__ import annotations

from pathlib import Path

from forensicx.core import database as db
from forensicx.core.hashing import hash_file
from forensicx.core.models import Evidence
from forensicx.parsers import get_parser


def import_evidence(
    case_id: int,
    file_path: str | Path,
    parser_name: str = "generic_text",
    notes: str = "",
) -> Evidence:
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    digests = hash_file(path)
    ev = db.add_evidence(
        case_id=case_id,
        filename=path.name,
        path=str(path),
        sha256=digests["sha256"],
        md5=digests["md5"],
        size_bytes=path.stat().st_size,
        parser=parser_name,
        notes=notes,
    )

    parser_cls = get_parser(parser_name)
    parser = parser_cls()
    for artifact in parser.parse(path, ev.id):
        db.add_artifact(
            evidence_id=ev.id,
            artifact_type=artifact.artifact_type,
            source=artifact.source,
            content=artifact.content,
            timestamp=artifact.timestamp,
            raw=artifact.raw,
        )

    return ev
