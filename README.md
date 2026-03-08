# Reporter Agent (Local-Only)

A local Python CLI that:
- Reads historical `.pptx` reports
- Builds a reusable knowledge base from slide text
- Builds a semantic vector index for fast relevance search
- Generates a new report plan for a new task
- Auto-fills what it can, inserts explicit blanks where data is missing
- Exports draft outputs as Markdown, JSON, and PPTX

## 1) Setup

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## 2) Index your existing reports

```powershell
python -m reporter_agent index --source-dir "C:\path\to\old\reports" --kb-out data\knowledge_base.json
```

This also builds semantic index files in `data/index` by default.
It also writes diagnostics to `data/index_diagnostics.json` (skipped files/reasons).
For performance tuning on strong hardware:

```powershell
python -m reporter_agent index --source-dir "C:\path\to\old\reports" --device cuda --batch-size 128
```

## 3) Search similar historical slides

```powershell
python -m reporter_agent search --query "compressor calibration sensitivity results" --index-dir data\index --top-k 5
```

Force a specific encode device if needed:

```powershell
python -m reporter_agent search --query "..." --index-dir data\index --device cuda
```

## 4) Generate a new report plan

```powershell
python -m reporter_agent plan `
  --kb data\knowledge_base.json `
  --task-name "Compressor map recalibration iteration 4" `
  --task-desc "Need a report for updated calibration and resulting sensitivity shifts for decision meeting." `
  --report-type model_calibration `
  --index-dir data\index `
  --semantic-top-k 4 `
  --out-dir output
```

Disable semantic mode if needed:

```powershell
python -m reporter_agent plan --kb data\knowledge_base.json --task-name "X" --task-desc "Y" --no-semantic
```

## 5) Chat mode with growing session memory

Create/continue a session:

```powershell
python -m reporter_agent chat --session-id projA --kb data\knowledge_base.json --index-dir data\index --message "new task: recalibrate compressor map and summarize sensitivity changes"
```

Useful follow-up messages:

```powershell
python -m reporter_agent chat --session-id projA --message "what is missing"
python -m reporter_agent chat --session-id projA --message "show sources slide 2"
python -m reporter_agent chat --session-id projA --message "revise slide 3: replace with latest validated numbers from run 47"
python -m reporter_agent chat --session-id projA --message "accept slide 3"
python -m reporter_agent chat --session-id projA --message "reject slide 4: lacks baseline comparison"
python -m reporter_agent chat --session-id projA --message "export plan"
```

## 6) Performance benchmark

```powershell
python -m reporter_agent benchmark `
  --kb data\knowledge_base.json `
  --index-dir data\index `
  --query "compressor calibration sensitivity" `
  --task-name "Benchmark task" `
  --task-desc "Need calibration and sensitivity summary" `
  --report-type model_calibration `
  --out-json output\benchmark.json
```

## 7) Environment doctor

```powershell
python -m reporter_agent doctor --kb data\knowledge_base.json --index-dir data\index
```

## 8) Build a release zip

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_release.ps1 -Version v0.1.0
```

Zip output:
- `dist\reporter-agent-v0.1.0.zip`

Optional logging:

```powershell
python -m reporter_agent --log-level DEBUG plan --kb data\knowledge_base.json --task-name "X" --task-desc "Y"
```

Output files:
- `output/<task>.md` -> human-editable report blueprint
- `output/<task>.json` -> structured plan for automation
- `output/<task>.pptx` -> slide skeleton with draft text + placeholders

## Report Types

- `simulation_request`
- `literature_review`
- `model_calibration`
- `model_sensitivity_analysis`

## Notes

- Everything runs locally. No cloud calls.
- Auto-filled text now uses semantic retrieval when index files are available (fallback: keyword mode).
- Replace all `[[FILL: ...]]` placeholders before sharing.

## Test

```powershell
pytest -q
```
