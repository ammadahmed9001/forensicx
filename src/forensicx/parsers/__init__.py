"""Artifact parser registry."""
from __future__ import annotations

from forensicx.parsers.generic_text import GenericTextParser

PARSERS: dict[str, type] = {
    "generic_text": GenericTextParser,
}


def get_parser(name: str) -> type:
    if name not in PARSERS:
        raise KeyError(f"Unknown parser: {name!r}. Available: {list(PARSERS)}")
    return PARSERS[name]
