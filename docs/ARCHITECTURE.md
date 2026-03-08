# Architecture (Phase 0 Baseline)

## Runtime Layers

1. `ingestion`: parse PPTX and build knowledge base records.
2. `planning`: build task-specific report plans from indexed records.
3. `export`: produce markdown/json/pptx outputs.
4. `retrieval`: embedding/vector retrieval layer (FAISS + sentence-transformers).
5. `chat` (placeholder): upcoming conversational interface.
6. `eval` (placeholder): upcoming benchmark and quality metrics tooling.
7. `storage` (placeholder): upcoming persistence for feedback/session memory.

## Current Entry Points

1. `python -m reporter_agent index`
2. `python -m reporter_agent plan`
3. `python -m reporter_agent search`

## Configuration

Environment variables:

1. `REPORTER_DATA_DIR` (default: `data`)
2. `REPORTER_OUTPUT_DIR` (default: `output`)
3. `REPORTER_LOG_LEVEL` (default: `INFO`)
