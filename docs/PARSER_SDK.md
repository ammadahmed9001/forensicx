# Parser SDK

Parsers are drop-in Python classes registered in `forensicx/parsers/__init__.py`.

## Interface

```python
from pathlib import Path
from typing import Iterator
from forensicx.core.models import Artifact

class MyParser:
    name = "my_parser"  # unique identifier

    def parse(self, path: Path, evidence_id: int) -> Iterator[Artifact]:
        ...
        yield Artifact(
            id=0,                     # assigned by the DB layer
            evidence_id=evidence_id,
            artifact_type="sms",      # short slug
            timestamp=datetime_obj,   # None if unknown
            source="mmssms.db:row42",
            content="Hello world",    # the searchable text
            raw={...},                # any extra fields
        )
```

## Registration

Add your class to `PARSERS` in `src/forensicx/parsers/__init__.py`:

```python
from forensicx.parsers.my_parser import MyParser

PARSERS: dict[str, type] = {
    "generic_text": GenericTextParser,
    "my_parser": MyParser,
}
```

Then pass `--parser my_parser` on the CLI or select it in the GUI.

## Built-in Parsers

| Name           | Description                            |
|----------------|----------------------------------------|
| `generic_text` | One artifact per non-blank line        |

## Planned Android Parsers

| Name              | Artifact types                        |
|-------------------|---------------------------------------|
| `android_sms`     | SMS / MMS from `mmssms.db`            |
| `android_calls`   | Call log from `contacts2.db`          |
| `android_contacts`| Contacts from `contacts2.db`          |
| `android_location`| GPS fixes from `cache.cell` / `cache.wifi` |
| `android_browser` | Browser history from `browser.db`     |
| `android_wifi`    | Wi-Fi scan results                    |
