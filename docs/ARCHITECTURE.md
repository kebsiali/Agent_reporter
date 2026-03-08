# Architecture (Phase 0 Baseline)

## Direction Update

Primary product direction is now GUI-first per:

1. `docs/GUI_PRODUCT_SPEC.md`

CLI remains available for development, automation, and diagnostics.

GUI requirement update:

1. GUI must provide an `Ingested PPTs` panel/button listing already ingested PPT names.
2. Ingestion flow must deduplicate using file fingerprint/hash to avoid repeated indexing.

## Runtime Layers

1. `ingestion`: parse PPTX and build knowledge base records.
2. `gui`: FastAPI web UI with drag/drop ingestion, in-GUI chat, and plan generation.
3. `planning`: build task-specific report plans from indexed records.
4. `export`: produce markdown/json/pptx outputs.
5. `retrieval`: embedding/vector retrieval layer (FAISS + sentence-transformers).
6. `chat`: session-based conversational interface with plan revision actions.
7. `eval`: benchmark and quality metrics tooling.
8. `storage`: persistence for feedback/session memory.
9. `doctor`: environment and readiness checks for dependencies/indexes.
10. `ingestion_registry`: persistent catalog of ingested files and dedup metadata.
11. `template`: company template profile extraction and style-locked export.

## Current Entry Points

1. `python -m reporter_agent index`
2. `python -m reporter_agent plan`
3. `python -m reporter_agent search`
4. `python -m reporter_agent chat`
5. `python -m reporter_agent benchmark`
6. `python -m reporter_agent doctor`
7. `python -m reporter_agent gui`

## Configuration

Environment variables:

1. `REPORTER_DATA_DIR` (default: `data`)
2. `REPORTER_OUTPUT_DIR` (default: `output`)
3. `REPORTER_LOG_LEVEL` (default: `INFO`)
