from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MASTER_CHILD_ID = "MASTER_CHILD"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_registry() -> dict[str, Any]:
    now = _now()
    return {
        "active_child_id": MASTER_CHILD_ID,
        "children": [
            {
                "child_id": MASTER_CHILD_ID,
                "child_name": "Master Child",
                "role": "master",
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "origin": "system_default",
            }
        ],
    }


def load_child_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _default_registry()
    data = json.loads(path.read_text(encoding="utf-8"))
    if "children" not in data or not isinstance(data["children"], list):
        data = _default_registry()
    ensure_master_child(data)
    return data


def save_child_registry(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def ensure_master_child(registry: dict[str, Any]) -> None:
    for c in registry.get("children", []):
        if c.get("child_id") == MASTER_CHILD_ID:
            return
    registry.setdefault("children", []).insert(
        0,
        {
            "child_id": MASTER_CHILD_ID,
            "child_name": "Master Child",
            "role": "master",
            "status": "active",
            "created_at": _now(),
            "updated_at": _now(),
            "origin": "system_default",
        },
    )
    registry["active_child_id"] = MASTER_CHILD_ID


def list_children(registry: dict[str, Any]) -> list[dict[str, Any]]:
    children = registry.get("children", [])
    return sorted(children, key=lambda c: (c.get("role") != "master", c.get("child_name", "")))


def find_child(registry: dict[str, Any], child_id: str) -> dict[str, Any] | None:
    for c in registry.get("children", []):
        if c.get("child_id") == child_id:
            return c
    return None


def create_child(
    registry: dict[str, Any],
    child_id: str,
    child_name: str,
    origin: str = "user_created",
) -> dict[str, Any]:
    if find_child(registry, child_id):
        raise ValueError(f"child_id already exists: {child_id}")
    entry = {
        "child_id": child_id,
        "child_name": child_name,
        "role": "standard",
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
        "origin": origin,
    }
    registry.setdefault("children", []).append(entry)
    return entry


def set_active_child(registry: dict[str, Any], child_id: str) -> None:
    child = find_child(registry, child_id)
    if not child:
        raise ValueError(f"Unknown child_id: {child_id}")
    if child.get("status") != "active":
        raise ValueError(f"Child is not active: {child_id}")
    registry["active_child_id"] = child_id
    child["updated_at"] = _now()


def archive_child(registry: dict[str, Any], child_id: str) -> dict[str, Any]:
    if child_id == MASTER_CHILD_ID:
        raise ValueError("MASTER_CHILD cannot be archived.")
    child = find_child(registry, child_id)
    if not child:
        raise ValueError(f"Unknown child_id: {child_id}")
    child["status"] = "archived"
    child["updated_at"] = _now()
    if registry.get("active_child_id") == child_id:
        registry["active_child_id"] = MASTER_CHILD_ID
    return child

