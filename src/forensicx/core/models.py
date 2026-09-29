"""Core data models."""
from __future__ import annotations

import dataclasses
import datetime
from typing import Any


@dataclasses.dataclass
class Case:
    id: int
    name: str
    investigator: str
    created_at: datetime.datetime
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "investigator": self.investigator,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }


@dataclasses.dataclass
class Evidence:
    id: int
    case_id: int
    filename: str
    path: str
    sha256: str
    md5: str
    size_bytes: int
    acquired_at: datetime.datetime
    parser: str = "generic_text"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "filename": self.filename,
            "path": self.path,
            "sha256": self.sha256,
            "md5": self.md5,
            "size_bytes": self.size_bytes,
            "acquired_at": self.acquired_at.isoformat(),
            "parser": self.parser,
            "notes": self.notes,
        }


@dataclasses.dataclass
class Artifact:
    id: int
    evidence_id: int
    artifact_type: str
    timestamp: datetime.datetime | None
    source: str
    content: str
    raw: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "evidence_id": self.evidence_id,
            "artifact_type": self.artifact_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "content": self.content,
            "raw": self.raw,
        }
