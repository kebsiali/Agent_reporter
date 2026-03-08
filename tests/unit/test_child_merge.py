import json
import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.child_memory.merge import apply_child_merge, preview_child_merge


def _root() -> Path:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_child_merge_preview_and_apply() -> None:
    root = _root()
    src = root / "src"
    tgt = root / "tgt"
    (src / "sessions").mkdir(parents=True, exist_ok=True)
    (tgt / "sessions").mkdir(parents=True, exist_ok=True)
    (src / "child" / "merge_reports").mkdir(parents=True, exist_ok=True)
    (tgt / "child" / "merge_reports").mkdir(parents=True, exist_ok=True)

    (src / "sessions" / "s1.json").write_text(
        json.dumps({"history": [{"role": "user", "message": "a"}]}), encoding="utf-8"
    )
    (tgt / "sessions" / "s1.json").write_text(json.dumps({"history": []}), encoding="utf-8")
    (src / "ingestion_registry.json").write_text(
        json.dumps({"files": [{"file_name": "a.pptx", "content_hash": "h1"}]}), encoding="utf-8"
    )
    (tgt / "ingestion_registry.json").write_text(json.dumps({"files": []}), encoding="utf-8")

    prev = preview_child_merge(src, tgt)
    assert prev["source_sessions"] == 1

    report = apply_child_merge(src, tgt, strategy="union_dedup")
    assert report["result"]["events_added"] >= 1
    assert Path(report["report_path"]).exists()
    shutil.rmtree(root, ignore_errors=True)

