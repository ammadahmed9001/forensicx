"""SQLite persistence layer."""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any

from forensicx.core.models import Artifact, Case, Evidence

DB_PATH = Path("forensicx.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    investigator TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id),
    filename    TEXT NOT NULL,
    path        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    md5         TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    acquired_at TEXT NOT NULL,
    parser      TEXT NOT NULL DEFAULT 'generic_text',
    notes       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS artifacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id   INTEGER NOT NULL REFERENCES evidence(id),
    artifact_type TEXT NOT NULL,
    timestamp     TEXT,
    source        TEXT NOT NULL,
    content       TEXT NOT NULL,
    raw_json      TEXT NOT NULL DEFAULT '{}'
);

CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
    content,
    content=artifacts,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS artifacts_ai AFTER INSERT ON artifacts BEGIN
    INSERT INTO artifacts_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS artifacts_ad AFTER DELETE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;
CREATE TRIGGER IF NOT EXISTS artifacts_au AFTER UPDATE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, content) VALUES ('delete', old.id, old.content);
    INSERT INTO artifacts_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _row_to_case(row: sqlite3.Row) -> Case:
    return Case(
        id=row["id"],
        name=row["name"],
        investigator=row["investigator"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        notes=row["notes"],
    )


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence(
        id=row["id"],
        case_id=row["case_id"],
        filename=row["filename"],
        path=row["path"],
        sha256=row["sha256"],
        md5=row["md5"],
        size_bytes=row["size_bytes"],
        acquired_at=datetime.datetime.fromisoformat(row["acquired_at"]),
        parser=row["parser"],
        notes=row["notes"],
    )


def create_case(name: str, investigator: str, notes: str = "", db_path: Path = DB_PATH) -> Case:
    init_db(db_path)
    now = datetime.datetime.utcnow().isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO cases (name, investigator, created_at, notes) VALUES (?,?,?,?)",
            (name, investigator, now, notes),
        )
        return Case(
            id=cur.lastrowid,  # type: ignore[arg-type]
            name=name,
            investigator=investigator,
            created_at=datetime.datetime.fromisoformat(now),
            notes=notes,
        )


def list_cases(db_path: Path = DB_PATH) -> list[Case]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM cases ORDER BY id").fetchall()
    return [_row_to_case(r) for r in rows]


def get_case(case_id: int, db_path: Path = DB_PATH) -> Case | None:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return _row_to_case(row) if row else None


def add_evidence(
    case_id: int,
    filename: str,
    path: str,
    sha256: str,
    md5: str,
    size_bytes: int,
    parser: str = "generic_text",
    notes: str = "",
    db_path: Path = DB_PATH,
) -> Evidence:
    init_db(db_path)
    now = datetime.datetime.utcnow().isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO evidence
               (case_id, filename, path, sha256, md5, size_bytes, acquired_at, parser, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (case_id, filename, path, sha256, md5, size_bytes, now, parser, notes),
        )
        return Evidence(
            id=cur.lastrowid,  # type: ignore[arg-type]
            case_id=case_id,
            filename=filename,
            path=path,
            sha256=sha256,
            md5=md5,
            size_bytes=size_bytes,
            acquired_at=datetime.datetime.fromisoformat(now),
            parser=parser,
            notes=notes,
        )


def list_evidence(case_id: int, db_path: Path = DB_PATH) -> list[Evidence]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM evidence WHERE case_id=? ORDER BY id", (case_id,)
        ).fetchall()
    return [_row_to_evidence(r) for r in rows]


def add_artifact(
    evidence_id: int,
    artifact_type: str,
    source: str,
    content: str,
    timestamp: datetime.datetime | None = None,
    raw: dict[str, Any] | None = None,
    db_path: Path = DB_PATH,
) -> Artifact:
    import json

    init_db(db_path)
    ts = timestamp.isoformat() if timestamp else None
    raw_json = json.dumps(raw or {})
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO artifacts (evidence_id, artifact_type, timestamp, source, content, raw_json)
               VALUES (?,?,?,?,?,?)""",
            (evidence_id, artifact_type, ts, source, content, raw_json),
        )
        return Artifact(
            id=cur.lastrowid,  # type: ignore[arg-type]
            evidence_id=evidence_id,
            artifact_type=artifact_type,
            timestamp=timestamp,
            source=source,
            content=content,
            raw=raw or {},
        )


def search_artifacts(
    case_id: int, query: str, limit: int = 100, db_path: Path = DB_PATH
) -> list[Artifact]:
    import json

    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT a.*
               FROM artifacts a
               JOIN artifacts_fts fts ON fts.rowid = a.id
               JOIN evidence e ON e.id = a.evidence_id
               WHERE e.case_id = ? AND artifacts_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (case_id, query, limit),
        ).fetchall()
    results = []
    for r in rows:
        results.append(
            Artifact(
                id=r["id"],
                evidence_id=r["evidence_id"],
                artifact_type=r["artifact_type"],
                timestamp=(
                    datetime.datetime.fromisoformat(r["timestamp"]) if r["timestamp"] else None
                ),
                source=r["source"],
                content=r["content"],
                raw=json.loads(r["raw_json"]),
            )
        )
    return results
