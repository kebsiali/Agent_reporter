# GUI Product Spec (Mandatory Before Next Build Iterations)

## 1. Product Direction Change

The reporter agent is now **GUI-first**. Terminal commands remain developer/admin tools, but normal user workflow must be fully in GUI.

Continuity requirement:

1. CHILD memory continuity and merge behavior is governed by `docs/CHILD_CONTINUITY_SPEC.md`.

## 2. Mandatory User Workflow

1. User opens desktop/local web GUI.
2. User creates a new report request workspace.
3. User imports historical PPTs by:
   - drag-and-drop pull into import area, or
   - clicking `Add PPT` button.
4. User adds current-task artifacts:
   - text brief/context
   - images/plots (`png`, `jpg`, `svg`)
   - data files (`csv`, `xlsx`, `json`)
   - PDFs
   - optional equations/snippets.
5. User chats with the assistant **inside the GUI** only.
6. Assistant generates draft PPT using company style template.
7. User edits/accepts/rejects inside GUI, and system learns from feedback.

## 3. GUI Requirements

## 3.1 Main Views

1. `Project Dashboard`
   - project list
   - status
   - latest generated deck
2. `Ingestion Workspace`
   - drag-and-drop zone
   - `Add PPT` button
   - file queue with parse status/errors
3. `Chat + Plan Studio`
   - chat panel
   - slide plan panel (confidence/gaps/sources)
   - missing-info checklist
4. `Deck Preview`
   - slide thumbnails
   - source references
   - export/download actions
5. `Learning Console`
   - accepted/rejected edits
   - style profile updates
   - template/profile versions

### 3.2 Interaction Requirements

1. Real-time progress bars for indexing/embedding/generation.
2. Non-blocking UI for long jobs (background tasks).
3. Inline error diagnostics (malformed file, parse failure, missing fields).
4. One-click rerun of failed ingestion items.
5. Source traceability per generated claim/slide.
6. A visible `Ingested PPTs` button/panel showing already indexed PPT names.
7. Import dedup behavior: if user adds an already ingested PPT, software must skip re-ingestion and mark it as `Already Ingested`.
8. A visible `Merge CHILD Histories` button/wizard.
9. A visible `Export CHILD` and `Import CHILD` action set.

## 4. Input and Parsing Requirements

### 4.1 Historical Knowledge Inputs

1. PPT/PPTX (required)
2. PDF (required)
3. CSV/XLSX/JSON (required)
4. Image plots (required)

### 4.3 Ingestion Registry and Dedup (Required)

1. Maintain an ingestion registry containing:
   - file path
   - file name
   - content fingerprint/hash
   - first-ingested timestamp
   - latest-ingested timestamp
   - status
2. GUI must expose this registry through `Ingested PPTs` view/button.
3. During import, dedup check must run before parsing/embedding.
4. If exact same file/content is already ingested, skip full pipeline and inform user.
5. If same path but content changed, treat as new version and re-index.

### 4.2 PDF and Figure Understanding (Required)

For provided PDFs, the system must detect and parse:

1. Vectorized plots
2. Raster plots (PNG-like embedded figures)
3. Tables
4. Equations
5. Captions and nearby explanatory text

Extracted elements must be indexed and linkable as evidence in generated slides.

## 5. Company Template Fidelity Requirements

Generated PPT must preserve company style:

1. Color scheme
2. Font family and sizes
3. Slide structure/layout patterns
4. Title/subtitle conventions
5. Chart/table styling defaults
6. Footer/header/logo placement rules

Implementation expectation:

1. User uploads company template deck(s).
2. System extracts style profile.
3. Generator applies style profile by default to all output decks.
4. Style profile versioned and auditable.

## 6. Learning and Improvement Requirements

The system must continuously improve using local feedback:

1. Content preference learning from accepted/rejected edits.
2. Template fidelity learning from manual formatting corrections.
3. Reporting style learning (tone, phrasing, structure tendencies).
4. Retrieval reranking updates from relevance feedback.

Note:

Use practical local preference learning/weight updates first. Full RL-style optimization is a later enhancement.

## 7. Revised Architecture Additions

1. `frontend_gui` layer (desktop/local web).
2. `artifact_intelligence` layer for PDF figures/tables/equations parsing.
3. `template_profiler` for extracting and enforcing company style.
4. `feedback_trainer` for local preference updates.

## 8. Revised Milestones (After Current Phase 5)

## Phase 6: GUI Foundation

1. FastAPI backend + local web UI shell.
2. Drag-and-drop + `Add PPT` ingestion panel.
3. In-GUI chat connected to existing chat engine.
4. `Ingested PPTs` panel with search/filter/status.
5. Dedup pre-check in ingestion flow.

## Phase 7: Template Fidelity Engine

1. Template import and style profile extraction.
2. Style-locked PPT generation.
3. Side-by-side template conformity validator.

## Phase 8: Multimodal Artifact Intelligence

1. PDF figure/table/equation extraction pipeline.
2. Plot/table/equation indexing and evidence linking.
3. Use extracted artifacts directly in draft deck generation.

## Phase 9: Learning Loop v2

1. Structured feedback capture in GUI.
2. Local preference update jobs.
3. Quality dashboard tracking trend improvements.

## 9. Acceptance Criteria for This Spec Update

1. No required user interaction through terminal for normal reporting workflow.
2. GUI can complete end-to-end flow: ingest -> chat -> generate -> review -> export.
3. Generated deck follows company template profile by default.
4. PDF plots/tables/equations are discoverable and usable as evidence.
5. Feedback loop measurably improves relevance and style consistency over time.
