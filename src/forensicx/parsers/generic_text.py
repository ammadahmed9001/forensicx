"""Generic plain-text parser — splits file into line-level artifacts."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Iterator

from forensicx.core.models import Artifact


class GenericTextParser:
    """Treat every non-blank line as a separate artifact."""

    name = "generic_text"

    def parse(self, path: Path, evidence_id: int) -> Iterator[Artifact]:
        with path.open(errors="replace") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                yield Artifact(
                    id=0,
                    evidence_id=evidence_id,
                    artifact_type="text_line",
                    timestamp=None,
                    source=f"{path.name}:{lineno}",
                    content=line,
                    raw={"line": lineno, "raw_text": line},
                )
