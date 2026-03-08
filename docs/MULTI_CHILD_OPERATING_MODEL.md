# Multi-CHILD Operating Model

## 1. Objective

Support many CHILD agents in one system, with:

1. child creation at will
2. child selection before work
3. import bundle as new child or into existing child
4. merge between children
5. one default `MASTER_CHILD` always kept up to date

## 2. Core Concepts

### 2.1 Child Identity

Each child has:

1. `child_id` (unique immutable id)
2. `child_name` (display name)
3. `role` (`master` or `standard`)
4. `created_at`, `updated_at`
5. `status` (`active`, `archived`, `locked`)
6. `origin` metadata (source machine/user/import path)

### 2.2 Child Registry

A global registry persists all children:

1. child metadata
2. storage locations
3. schema versions
4. last sync time with MASTER_CHILD

Registry must be the source of truth for GUI selection.

## 3. Required GUI Features

## 3.1 Child Workspace Switcher

1. `Select Child` dropdown
2. `Create Child` button
3. `Clone Child` button
4. `Archive Child` action
5. visible current child badge in all pages

### 3.2 Import/Export Actions

1. `Export CHILD` (for selected child)
2. `Import as New Child`
3. `Import into Existing Child`
4. `Preview Import` before commit

### 3.3 Merge Actions

1. `Merge Children` button
2. source child selector (one or many)
3. target child selector
4. merge strategy selector
5. conflict preview and final merge report

## 4. MASTER_CHILD Policy

## 4.1 Behavior

`MASTER_CHILD` is special:

1. exists by default
2. receives periodic sync from other children
3. acts as fallback knowledge source
4. cannot be deleted (only backed up/restored)

### 4.2 Sync Modes

1. `automatic`: every accepted learning event propagates to master
2. `scheduled`: batch sync every N hours
3. `manual`: user triggers `Sync to MASTER_CHILD`

Default: scheduled + manual override.

## 5. Import Modes

## Mode A: Import as New Child

1. creates new child identity
2. imported memory stays isolated
3. optional post-import sync to master

## Mode B: Import into Existing Child

1. bundle merged into chosen child
2. dedup by event id/hash
3. conflict strategy required before apply

## 6. Merge Strategies (Required)

1. `union_dedup`:
   - keep all unique events
2. `quality_weighted`:
   - prefer events with stronger appraisal scores
3. `recency_weighted`:
   - prefer newest conflicting entries
4. `master_priority`:
   - keep master values unless explicit override

All merges must output:

1. conflict summary
2. dropped/replaced event list
3. rollback snapshot pointer

## 7. Ingenious Workflow Proposal

## 7.1 Everyday Flow

1. User selects child by project/team context.
2. Child learns from that domain without polluting others.
3. Accepted/rejected/appraisal/punishment feedback is captured.

## 7.2 Weekly Learning Council

1. Open `Merge Children` wizard.
2. Select high-performing project children.
3. Preview conflicts and quality metrics.
4. Merge into `MASTER_CHILD` with `quality_weighted` strategy.
5. Publish updated master snapshot.

## 7.3 New Machine Onboarding

1. Install app.
2. Import `MASTER_CHILD` bundle as baseline.
3. Continue work with local child branches.
4. Periodically export and merge back to master.

## 7.4 Branch-and-Fuse Model

1. Create child branch per problem domain:
   - `CHILD_SIMULATION`
   - `CHILD_CALIBRATION`
   - `CHILD_LITERATURE`
2. Let each specialize.
3. Fuse improvements into master with merge wizard.
4. Redistribute refreshed master to all machines.

## 8. Data Model Additions

1. `children_registry.json`
2. `child_sync_log.json`
3. `merge_reports/<timestamp>.json`
4. `snapshots/<child_id>/<timestamp>/...`

## 9. Roadmap

## Phase 13: Multi-Child Registry + Selector

1. registry persistence
2. GUI child switcher
3. create/clone/archive actions

## Phase 14: Import Routing + Targeted Merge

1. import as new child
2. import into existing child
3. merge preview and conflict report

## Phase 15: MASTER_CHILD Sync Engine

1. scheduled sync jobs
2. sync policies per child
3. master health dashboard

## 10. Acceptance Criteria

1. User can create and switch among at least 50 children.
2. Any exported child can be imported as new or into existing.
3. MASTER_CHILD can be kept current via configured sync mode.
4. Every merge/import is reversible through snapshot rollback.
5. Full workflow available through GUI only (no terminal required).

