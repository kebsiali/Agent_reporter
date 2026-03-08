from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..child_memory import apply_child_merge
from ..storage.child_registry import MASTER_CHILD_ID, load_child_registry, save_child_registry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sync_log_path(base_data_dir: Path) -> Path:
    return base_data_dir / "gui_projects" / "master_sync_log.json"


def _load_sync_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"events": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_sync_log(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _registry_path(base_data_dir: Path) -> Path:
    return base_data_dir / "gui_projects" / "children_registry.json"


def _child_root(base_data_dir: Path, child_id: str) -> Path:
    return base_data_dir / "gui_projects" / child_id


def run_master_sync(
    base_data_dir: Path,
    strategy: str = "quality_weighted",
    mode: str = "manual",
) -> dict[str, Any]:
    reg_path = _registry_path(base_data_dir)
    reg = load_child_registry(reg_path)
    master_root = _child_root(base_data_dir, MASTER_CHILD_ID)
    master_root.mkdir(parents=True, exist_ok=True)

    merged_children = []
    for c in reg.get("children", []):
        cid = c.get("child_id")
        if cid == MASTER_CHILD_ID:
            continue
        if c.get("status") != "active":
            continue
        src = _child_root(base_data_dir, cid)
        if not src.exists():
            continue
        report = apply_child_merge(src, master_root, strategy=strategy)
        merged_children.append({"child_id": cid, "report_path": report.get("report_path")})

    reg["master_sync"] = {
        "policy_mode": reg.get("master_sync", {}).get("policy_mode", "scheduled"),
        "policy_strategy": reg.get("master_sync", {}).get("policy_strategy", "quality_weighted"),
        "last_sync_at": _now(),
        "last_mode": mode,
        "last_merged_children": [m["child_id"] for m in merged_children],
    }
    save_child_registry(reg_path, reg)

    log_path = _sync_log_path(base_data_dir)
    log = _load_sync_log(log_path)
    event = {
        "synced_at": _now(),
        "mode": mode,
        "strategy": strategy,
        "merged_children": merged_children,
        "count": len(merged_children),
    }
    log.setdefault("events", []).append(event)
    _save_sync_log(log_path, log)
    return event


def get_master_health(base_data_dir: Path) -> dict[str, Any]:
    reg = load_child_registry(_registry_path(base_data_dir))
    log = _load_sync_log(_sync_log_path(base_data_dir))
    children = reg.get("children", [])
    active_non_master = [
        c["child_id"]
        for c in children
        if c.get("child_id") != MASTER_CHILD_ID and c.get("status") == "active"
    ]
    last_event = log.get("events", [])[-1] if log.get("events") else None
    return {
        "master_child_id": MASTER_CHILD_ID,
        "policy_mode": reg.get("master_sync", {}).get("policy_mode", "scheduled"),
        "policy_strategy": reg.get("master_sync", {}).get("policy_strategy", "quality_weighted"),
        "last_sync_at": reg.get("master_sync", {}).get("last_sync_at"),
        "active_children_count": len(active_non_master),
        "active_children": active_non_master,
        "last_event": last_event,
        "total_sync_events": len(log.get("events", [])),
    }

