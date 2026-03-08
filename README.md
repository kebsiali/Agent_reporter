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

## 3) Search similar historical slides

```powershell
python -m reporter_agent search --query "compressor calibration sensitivity results" --index-dir data\index --top-k 5
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
