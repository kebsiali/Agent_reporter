# Reporter Agent (Local-Only)

A local Python CLI that:
- Reads historical `.pptx` reports
- Builds a reusable knowledge base from slide text
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

## 3) Generate a new report plan

```powershell
python -m reporter_agent plan `
  --kb data\knowledge_base.json `
  --task-name "Compressor map recalibration iteration 4" `
  --task-desc "Need a report for updated calibration and resulting sensitivity shifts for decision meeting." `
  --report-type model_calibration `
  --out-dir output
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
- Auto-filled text is based on historical slide text similarity only.
- Replace all `[[FILL: ...]]` placeholders before sharing.

## Test

```powershell
pytest -q
```
