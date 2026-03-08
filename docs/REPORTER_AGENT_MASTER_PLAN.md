# Reporter Agent Master Plan

## Spec Update Notice (2026-03-08)

This master plan is superseded for UX direction by:

1. `docs/GUI_PRODUCT_SPEC.md`

Key update:

1. GUI is mandatory as primary interface.
2. Drag/drop + `Add PPT` import is mandatory.
3. Chat must be inside GUI.
4. Multimodal inputs (PDF/plots/data/tables/equations) are mandatory.
5. Company template style fidelity is mandatory.

## 1. Vision and Outcome

Build a fully local, GPU-accelerated "reporter agent" that:

1. Learns from your historical PowerPoint reports.
2. Understands new task requests (simulation, calibration, sensitivity, literature review, ad-hoc boss requests).
3. Produces:
   - A slide-by-slide report plan
   - Auto-filled draft content from relevant historical material
   - Explicit blanks for missing data
   - A concrete checklist explaining where/how to get missing data
4. Provides chat-based interaction so the system grows with your feedback and usage history.
5. Never sends company data to external cloud services.

Success target: reduce report-prep time by at least 60% while improving consistency and traceability.

## 2. Product Scope

### 2.1 In Scope (MVP -> v2)

1. Local ingestion of `.pptx` (and later PDF/DOCX/XLSX).
2. Fast semantic retrieval across all prior reports.
3. Report blueprint generation for task types.
4. Draft PPT generation with placeholders.
5. Interactive chat assistant with retrieval-grounded answers.
6. User feedback loop: accept/reject edits to improve future drafts.
7. Evaluation dashboard for quality and speed metrics.

### 2.2 Out of Scope (initial)

1. Automatic final sign-off without human review.
2. Internet-connected data enrichment by default.
3. Multi-user server deployment (start single-user workstation first).

## 3. Core Requirements

### 3.1 Functional Requirements

1. Ingest historical reports and extract structured units:
   - slide title
   - bullets/body text
   - tables/charts captions (where accessible)
   - tags: objective/method/results/conclusion/etc.
2. Create a project knowledge base with searchable embeddings.
3. Accept a new task prompt and infer report type/template.
4. Generate slide plan:
   - objective of each slide
   - proposed content
   - confidence score
   - placeholders for missing specifics
   - "how to obtain missing info" checklist
5. Export outputs:
   - Markdown plan
   - JSON plan
   - Draft PPTX
6. Chat mode:
   - ask follow-ups
   - revise specific slides
   - ask "what data do I still need?"
7. Growth memory:
   - store final accepted edits
   - store rejected suggestions
   - improve ranking/prompting over time

### 3.2 Non-Functional Requirements

1. Fully local execution; no external API dependency.
2. Fast response on strong GPU workstations.
3. Deterministic reproducibility mode for critical reports.
4. Auditability: every generated statement should be traceable to source slides or user input.
5. Security: encryption at rest optional, access control for knowledge base.

## 4. System Architecture

## 4.1 High-Level Components

1. Ingestion Pipeline
2. Document Store + Metadata Store
3. Embedding and Vector Retrieval Engine
4. Reranker
5. Local LLM Orchestrator
6. Report Planner + Draft Composer
7. Chat Interface (CLI first, UI later)
8. Evaluation and Feedback Loop

### 4.2 Data Flow

1. Historical PPTX -> parser/chunker -> semantic units.
2. Semantic units -> embedding model -> vector index.
3. New task -> intent classifier + retrieval query.
4. Retrieved evidence -> reranker -> context pack.
5. Context pack + task -> LLM planner -> slide plan JSON.
6. Composer -> Markdown + PPTX draft.
7. User edits -> feedback store -> continual tuning of retrieval/prompts/templates.

## 5. Recommended Technical Stack (Rocket Mode, Local)

## 5.1 LLM Serving

Primary runtime options:

1. `Ollama` for simple local model management and chat APIs.
2. `llama.cpp` for high-performance quantized inference on local hardware.
3. `vLLM` (Linux-focused) for high-throughput serving if you run a dedicated inference machine.

Selection policy:

1. Workstation local default: Ollama or llama.cpp.
2. Dedicated multi-GPU node: vLLM service for batch generation speed.

### 5.2 Embedding + Retrieval

1. Embeddings: `sentence-transformers` (strong pretrained embedding models).
2. Vector index:
   - Fast local baseline: `FAISS`
   - Optional service-based index: `Qdrant`
3. Reranker: cross-encoder reranker model (improves relevance precision before generation).

### 5.3 Document Parsing

1. Existing parser: `python-pptx` for reliable PPTX extraction and generation.
2. Advanced parser option: `Docling` for richer multi-format ingestion as you expand beyond PPTX.

### 5.4 App Framework

1. Backend: Python package + CLI.
2. Later UI: lightweight web app (`FastAPI` + minimal frontend) or desktop wrapper.
3. Storage:
   - SQLite/PostgreSQL for metadata
   - local filesystem for artifacts
   - FAISS/Qdrant for vectors

## 6. Knowledge Model and Data Schema

### 6.1 Document-Level Schema

1. `doc_id`
2. `source_path`
3. `task_type`
4. `project_tags`
5. `date`
6. `version`

### 6.2 Slide/Chunk Schema

1. `chunk_id`
2. `doc_id`
3. `slide_number`
4. `section_label` (objective/method/results/conclusion/etc.)
5. `raw_text`
6. `normalized_text`
7. `embedding_vector`
8. `quality_flags` (ocr/noise/empty)
9. `evidence_links`

### 6.3 Interaction/Feedback Schema

1. `session_id`
2. `task_prompt`
3. `generated_plan_id`
4. `user_edits` (diff)
5. `accepted_blocks`
6. `rejected_blocks`
7. `final_report_link`

## 7. Methods and Algorithms

### 7.1 Task Understanding

1. Rule-based + classifier hybrid for task type detection.
2. Intent slots:
   - deliverable type
   - scenario/scope
   - constraints/deadline
   - required KPIs

### 7.2 Retrieval Pipeline (RAG)

1. Query rewrite from user task.
2. Dense retrieval top-K.
3. Metadata filtering by project/task/date.
4. Rerank top-N for precision.
5. Evidence pack assembly with source attribution.

### 7.3 Draft Planning

1. Select report template skeleton.
2. Fill each slide from evidence pack.
3. Apply confidence thresholds:
   - high: auto-fill
   - medium: auto-fill + warning
   - low: placeholder only
4. Generate missing-info checklist from template rules + missing entities.

### 7.4 Continuous Learning

1. Embed final edited reports back into KB.
2. Learn preferred language/style via prompt-profile memory.
3. Track section-level acceptance rate and adapt retrieval weighting.

## 8. Implementation Roadmap

## Phase 0: Foundation Hardening (1 week)

1. Clean repo structure (`src`, `tests`, `docs`, `configs`, `scripts`).
2. Add environment management and lock files.
3. Add logging, config system, and typed settings.
4. Define data schemas and migration strategy.

Deliverables:

1. Project skeleton
2. Baseline CI checks (lint, tests)
3. Architecture docs

## Phase 1: Strong Retrieval Core (2 weeks)

1. Replace keyword-only similarity with embedding retrieval.
2. Add FAISS index and metadata filters.
3. Add reranking pass.
4. Build benchmark harness for retrieval relevance.

Deliverables:

1. `index` command v2 (embeddings + metadata)
2. `search` diagnostic command
3. Relevance benchmark report

## Phase 2: Planner v2 + Missing-Info Intelligence (2 weeks)

1. Add robust template engine by task type.
2. Add confidence scoring per section.
3. Add missing-data detector and guidance generator.
4. Improve PPT draft generation with cleaner layout placeholders.

Deliverables:

1. `plan` command v2 with confidence traces
2. Better Markdown/JSON/PPT outputs
3. Missing-info checklists grounded in evidence

## Phase 3: Chatbot Mode + Memory (2 weeks)

1. Add `chat` command with retrieval-grounded assistant.
2. Session memory (task context + edits).
3. Commands:
   - "revise slide 3"
   - "show sources for this claim"
   - "what is missing?"
4. Persist accepted edits for future generation biasing.

Deliverables:

1. Local chatbot loop
2. Source citation tracing in responses
3. Feedback capture module

## Phase 4: Performance/GPU Optimization (1-2 weeks)

1. Quantized model matrix and latency benchmarks.
2. Batch embedding pipelines.
3. Parallel ingestion and caching.
4. Optional dedicated inference server mode.

Deliverables:

1. Throughput/latency benchmark sheet
2. Recommended runtime profiles by hardware tier

## Phase 5: Reliability and UX (2 weeks)

1. Add robust regression test suite.
2. Add failure-handling for malformed/legacy PPTX.
3. Optional minimal web UI.
4. Packaging (installer or executable workflow).

Deliverables:

1. Release candidate
2. User guide and operations runbook

## 9. Testing and Validation Plan

### 9.1 Test Levels

1. Unit tests:
   - parser
   - chunker
   - retrieval scoring
   - template filling
2. Integration tests:
   - end-to-end index -> plan -> ppt export
3. Regression tests:
   - fixed sample corpus and expected outputs
4. Performance tests:
   - ingestion throughput
   - retrieval latency
   - plan generation latency
5. Human evaluation:
   - quality scoring by you on generated drafts

### 9.2 Quality Metrics

1. Retrieval precision@k / recall@k
2. Section fill accuracy (useful autofill ratio)
3. Placeholder correctness (missing data caught)
4. Citation faithfulness (claims linked to evidence)
5. End-to-end time saved vs manual baseline
6. User acceptance rate per section

### 9.3 Validation Protocol

1. Build a gold set of 30-50 historical tasks + their final reports.
2. Hide the final report and generate from task prompt only.
3. Compare output with gold report structure/content.
4. Record where it helps and where it fails.
5. Iterate retrieval and prompts before expanding scope.

## 10. Security, Privacy, and Governance

1. Local-only runtime by default.
2. Optional encrypted vector/metadata store.
3. Audit log for:
   - indexed files
   - generated outputs
   - user edits
4. Access model files and KB directories via OS permissions.
5. Add policy checks before export (for sensitive sections).

## 11. Risks and Mitigations

1. Risk: weak relevance when slide text is sparse.
   - Mitigation: table/chart extraction improvements + reranking.
2. Risk: hallucinated statements.
   - Mitigation: evidence-grounded generation and mandatory source display.
3. Risk: model latency for large contexts.
   - Mitigation: tighter retrieval, chunking, quantization profiles.
4. Risk: overfitting to one writing style.
   - Mitigation: style profiles + per-project template variants.

## 12. Project Structure Proposal

```text
reporter/
  docs/
    REPORTER_AGENT_MASTER_PLAN.md
    ARCHITECTURE.md
  reporter_agent/
    cli.py
    config.py
    ingestion/
    retrieval/
    planning/
    chat/
    export/
    eval/
    storage/
  tests/
    unit/
    integration/
    regression/
    performance/
  data/
    kb/
    eval_corpus/
  scripts/
    benchmark/
    maintenance/
```

## 13. Milestones and Gates

### Gate A (End Phase 1)

1. Retrieval precision@5 >= 0.75 on gold set.
2. Indexing stable on at least 200 PPT files.

### Gate B (End Phase 2)

1. At least 50% of slide sections useful with minimal edits.
2. Missing-info checklist quality approved by user review.

### Gate C (End Phase 3)

1. Chat can revise specific slides reliably.
2. Source attribution appears for generated claims.

### Gate D (Release Candidate)

1. Median draft generation time < 2 minutes per report.
2. End-to-end time saving >= 60% vs manual process.

## 14. Immediate Next Steps (Execution Order)

1. Lock phase goals and acceptance metrics (this document).
2. Implement Phase 0 hardening and repository refactor.
3. Implement embedding retrieval core (Phase 1).
4. Run first benchmark on your real historical corpus.
5. Tune model/index choices based on benchmark results, not assumptions.

## 15. Local Packages to Prepare (Planned)

Core:

1. `python-pptx`
2. `sentence-transformers`
3. `faiss-cpu` (or GPU-capable FAISS build where available)
4. `numpy`, `pandas`, `pydantic`, `typer` or `argparse`
5. `pytest`

Optional/advanced:

1. `qdrant-client`
2. `docling`
3. `fastapi` + `uvicorn` (for local service/UI)
4. `onnxruntime-gpu` for accelerated embedding/reranking pipelines

Model runtime (choose one or more):

1. `Ollama` local model server
2. `llama.cpp` binaries/runtime
3. `vLLM` (if deploying dedicated Linux inference node)

## 16. Source References

The plan choices above are aligned with current official documentation:

1. Ollama docs: https://docs.ollama.com/
2. Ollama Modelfile reference: https://docs.ollama.com/modelfile
3. llama.cpp official repo: https://github.com/ggml-org/llama.cpp
4. vLLM quickstart: https://docs.vllm.ai/en/v0.8.5.post1/getting_started/quickstart.html
5. Sentence Transformers docs: https://www.sbert.net/
6. FAISS official repo: https://github.com/facebookresearch/faiss
7. Qdrant docs: https://qdrant.tech/documentation/
8. python-pptx docs: https://python-pptx.readthedocs.io/en/stable/index.html
9. Docling docs: https://docling-project.github.io/docling/
10. pytest docs: https://docs.pytest.org/
