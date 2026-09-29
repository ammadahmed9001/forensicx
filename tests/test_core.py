"""Core unit tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forensicx.core import database as db
from forensicx.core.hashing import hash_file, verify_hash
from forensicx.services.evidence import import_evidence


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    return db_path


def test_create_and_list_cases(tmp_db):
    c1 = db.create_case("Alpha", "Alice", db_path=tmp_db)
    c2 = db.create_case("Beta", "Bob", db_path=tmp_db)
    cases = db.list_cases(db_path=tmp_db)
    assert len(cases) == 2
    assert cases[0].name == "Alpha"
    assert cases[1].name == "Beta"


def test_get_case(tmp_db):
    c = db.create_case("Gamma", "Carol", db_path=tmp_db)
    fetched = db.get_case(c.id, db_path=tmp_db)
    assert fetched is not None
    assert fetched.investigator == "Carol"


def test_get_case_missing(tmp_db):
    db.init_db(tmp_db)
    assert db.get_case(999, db_path=tmp_db) is None


def test_hash_file(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello world")
    digests = hash_file(f)
    assert "sha256" in digests
    assert "md5" in digests
    assert len(digests["sha256"]) == 64


def test_verify_hash(tmp_path):
    import hashlib
    f = tmp_path / "data.bin"
    data = b"forensicx test"
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert verify_hash(f, expected)
    assert not verify_hash(f, "0" * 64)


def test_import_evidence(tmp_path, tmp_db):
    case = db.create_case("Import Test", "Tester", db_path=tmp_db)
    ev_file = tmp_path / "sample.txt"
    ev_file.write_text("line one\nline two\nline three\n")

    ev = import_evidence(case_id=case.id, file_path=ev_file)
    assert ev.filename == "sample.txt"
    assert ev.size_bytes > 0

    items = db.list_evidence(case.id, db_path=tmp_db)
    assert len(items) == 1
    assert items[0].sha256 == ev.sha256


def test_search_artifacts(tmp_path, tmp_db):
    case = db.create_case("Search Test", "Tester", db_path=tmp_db)
    ev_file = tmp_path / "log.txt"
    ev_file.write_text("GPS location: 37.42N 122.08W\ncall log entry\n")

    import_evidence(case_id=case.id, file_path=ev_file)
    results = db.search_artifacts(case.id, "location", db_path=tmp_db)
    assert len(results) >= 1
    assert "location" in results[0].content.lower()
