import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.doctor import run_doctor


def test_doctor_reports_missing_files() -> None:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    kb = root / "kb.json"
    index_dir = root / "index"
    output = run_doctor(kb_path=kb, index_dir=index_dir)
    assert any("Knowledge base not found" in line for line in output)
    assert any("Semantic index files missing" in line for line in output)
    shutil.rmtree(root, ignore_errors=True)
