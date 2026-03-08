# CHILD Continuity Spec

## 1. Purpose

`CHILD` is the persistent learning identity of the reporter agent.  
This spec defines how CHILD memory survives:

1. software version upgrades
2. machine-to-machine moves
3. multi-user parallel usage
4. history merges into one stronger CHILD

Goal: migration and merge must be easy, explicit, and repeatable.

## 2. Core Principle

CHILD is not tied to one install folder.  
CHILD is defined by a **portable memory package** with strict schema/versioning.

## 3. Mandatory Data Domains in CHILD Memory

1. Interaction history (chat prompts/replies)
2. Report plans and revisions
3. Accepted/rejected slide feedback
4. Appraisals and punishments (positive/negative feedback events)
5. Template/style profiles
6. Retrieval preferences and ranking signals
7. Provenance metadata (machine, user, timestamps, software version)

## 4. Portable CHILD Package Format

Each CHILD export must produce one bundle directory (or zip) containing:

1. `manifest.json`
2. `schema_version`
3. `memory/`:
   - sessions
   - feedback
   - template profiles
   - preference model state
4. `artifacts_index/` (paths/hashes, not mandatory binary payload copies)
5. `checksums.json`

## 5. Version Compatibility and Migration

### 5.1 Strict Requirements

1. Every persisted structure must include `schema_version`.
2. App startup must run migration checks automatically.
3. If old schema detected, migration scripts must run before use.
4. No destructive migration without backup snapshot.
5. Migration logs must be stored and visible in GUI.

### 5.2 Backward/Forward Policy

1. Read support: current version reads N-2 minimum.
2. Write support: always writes current schema.
3. If unsupported schema detected, UI must offer:
   - export raw backup
   - guided migration tool

## 6. Cross-Machine Multi-History Model

Each machine/user instance generates a history stream with:

1. `child_id`
2. `instance_id`
3. `operator_id`
4. event ids (uuid)
5. monotonic event timestamps
6. optional signed hash chain for tamper detection

## 7. Merge CHILD Histories (GUI Required)

GUI must provide a `Merge CHILD Histories` button and flow:

1. Select multiple CHILD bundles or history sources.
2. Show merge preview:
   - event counts
   - overlap/duplicate counts
   - conflict buckets
3. Merge strategy options:
   - default: union + dedup by event id/hash
   - recency-biased conflict resolution
   - quality-weighted conflict resolution (based on appraisal scores)
4. Output:
   - new merged CHILD package
   - merge report with conflict summary
   - rollback checkpoint

## 8. Feedback Semantics (Appraisal/Punishment)

Feedback entries must be structured:

1. `feedback_type`: appraisal | punishment | neutral
2. `target`: slide | statement | style | retrieval result
3. `reason_code`
4. `operator_comment`
5. `impact_weight`
6. `timestamp`

Merged CHILD must preserve all feedback provenance.

## 9. Reliability Requirements (Hard)

1. Every write is atomic (temp file + rename).
2. Automatic periodic snapshots.
3. One-click `Export CHILD`.
4. One-click `Import CHILD`.
5. One-click `Merge CHILD Histories`.
6. One-click `Rollback to Snapshot`.

## 10. Security and Integrity

1. Optional bundle encryption with password/key.
2. Checksums for all bundle files.
3. Merge must verify integrity before applying.
4. Audit trail for import/export/merge/rollback operations.

## 11. Implementation Phases

## Phase 10: CHILD Persistence Foundation

1. Define schema and manifest contract.
2. Add migration engine and versioned storage adapters.
3. Add export/import API + GUI actions.

## Phase 11: Multi-History Merge Engine

1. Event normalization and dedup.
2. Conflict resolver strategies.
3. Merge report generation.
4. GUI merge wizard.

## Phase 12: Trust and Governance

1. Integrity/signature validation.
2. Snapshot/rollback UX.
3. Operator-level provenance filtering.

## 12. Acceptance Criteria

1. CHILD can be exported on machine A and imported on machine B with no memory loss.
2. CHILD from at least 3 machines can be merged into one with dedup and conflict reporting.
3. Merged CHILD retains appraisals and punishments with provenance.
4. Upgrading software versions keeps CHILD usable through auto-migrations.
5. GUI exposes import/export/merge/rollback without terminal use.

