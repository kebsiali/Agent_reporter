import json
import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.master_sync.engine import get_master_health, run_master_sync
from reporter_agent.storage.child_registry import create_child, load_child_registry, save_child_registry


def _root() -> Path:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_master_sync_runs_and_logs_event() -> None:
    root = _root()
    base = root / "data"
    reg_path = base / "gui_projects" / "children_registry.json"
    reg = load_child_registry(reg_path)
    create_child(reg, "CHILD_A", "Child A")
    save_child_registry(reg_path, reg)

    child_a_root = base / "gui_projects" / "CHILD_A"
    (child_a_root / "sessions").mkdir(parents=True, exist_ok=True)
    (child_a_root / "sessions" / "s1.json").write_text(
        json.dumps({"history": [{"role": "user", "message": "hello"}]}), encoding="utf-8"
    )
    (child_a_root / "ingestion_registry.json").write_text(json.dumps({"files": []}), encoding="utf-8")

    event = run_master_sync(base_data_dir=base, strategy="union_dedup", mode="manual")
    assert event["count"] >= 1

    health = get_master_health(base_data_dir=base)
    assert health["total_sync_events"] >= 1
    assert "CHILD_A" in health["active_children"]
    shutil.rmtree(root, ignore_errors=True)

