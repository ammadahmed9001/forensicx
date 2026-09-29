"""File hashing utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path | str, algorithms: tuple[str, ...] = ("sha256", "md5")) -> dict[str, str]:
    """Return a dict of {algorithm: hex_digest} for the given file."""
    path = Path(path)
    hashers = {alg: hashlib.new(alg) for alg in algorithms}
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            for h in hashers.values():
                h.update(chunk)
    return {alg: h.hexdigest() for alg, h in hashers.items()}


def verify_hash(path: Path | str, expected_sha256: str) -> bool:
    """Return True if the file's SHA-256 matches the expected digest."""
    digests = hash_file(path, ("sha256",))
    return digests["sha256"].lower() == expected_sha256.lower()
