# ForensicX Architecture

## Overview

ForensicX follows a layered pipeline architecture:

```
Evidence Files
     │
     ▼
┌──────────────┐
│  Acquisition │  hash_file() — SHA-256 + MD5 on ingest
│   (hashing)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Parsers    │  GenericTextParser, AndroidSmsParser, …
│  (plugins)   │
└──────┬───────┘
       │  Artifact stream
       ▼
┌──────────────┐
│ Normalization│  Artifact dataclass — type, timestamp, source, content, raw
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Persistence │  SQLite (WAL mode) + FTS5 full-text index
│  (database)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Correlation │  (planned) timeline join across evidence items
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Search /   │  FTS5 query, timeline view, graph
│   Timeline   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Reports    │  JSON, PDF (planned), HTML (planned)
└──────────────┘
```

## Key Components

### `forensicx.core.database`
SQLite persistence using WAL journal mode and FTS5 virtual table for full-text search. Three main tables: `cases`, `evidence`, `artifacts`.

### `forensicx.core.hashing`
Hash-first ingest: every file is SHA-256 + MD5 hashed before parsing to support chain of custody.

### `forensicx.core.models`
Pure dataclasses: `Case`, `Evidence`, `Artifact`. No ORM dependency.

### `forensicx.parsers`
Plugin-style registry. Each parser implements `parse(path, evidence_id) -> Iterator[Artifact]`.

### `forensicx.services`
Business logic layer that orchestrates hashing → DB write → parsing → artifact ingestion.

### `forensicx.cli`
Click-based CLI. Mirrors all GUI functionality.

### `forensicx.gui`
Tkinter GUI, zero extra dependencies beyond the stdlib.

## Data Model

```
Case (1) ──── (N) Evidence (1) ──── (N) Artifact
```

- A **Case** groups related evidence under a single investigation.
- An **Evidence** item is one imported file with its hash and metadata.
- **Artifacts** are extracted records (a text line, an SMS, a GPS fix, …).
