import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.storage.child_registry import (
    MASTER_CHILD_ID,
    archive_child,
    create_child,
    load_child_registry,
    save_child_registry,
    set_active_child,
)


def _root() -> Path:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_child_registry_has_master_by_default() -> None:
    root = _root()
    reg = load_child_registry(root / "children_registry.json")
    assert reg["active_child_id"] == MASTER_CHILD_ID
    assert any(c["child_id"] == MASTER_CHILD_ID for c in reg["children"])
    shutil.rmtree(root, ignore_errors=True)


def test_create_select_archive_child() -> None:
    root = _root()
    reg_path = root / "children_registry.json"
    reg = load_child_registry(reg_path)
    create_child(reg, "CHILD_A", "Child A")
    set_active_child(reg, "CHILD_A")
    assert reg["active_child_id"] == "CHILD_A"
    archived = archive_child(reg, "CHILD_A")
    assert archived["status"] == "archived"
    assert reg["active_child_id"] == MASTER_CHILD_ID
    save_child_registry(reg_path, reg)
    shutil.rmtree(root, ignore_errors=True)

