from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def find_by_hash(registry: dict[str, Any], content_hash: str) -> dict[str, Any] | None:
    for item in registry.get("files", []):
        if item.get("content_hash") == content_hash:
            return item
    return None


def register_ingested_file(
    registry: dict[str, Any],
    file_name: str,
    stored_path: str,
    content_hash: str,
    status: str,
) -> dict[str, Any]:
    existing = find_by_hash(registry, content_hash)
    if existing:
        existing["latest_ingested_at"] = _now()
        existing["status"] = status
        return existing

    entry = {
        "file_name": file_name,
        "stored_path": stored_path,
        "content_hash": content_hash,
        "first_ingested_at": _now(),
        "latest_ingested_at": _now(),
        "status": status,
    }
    registry.setdefault("files", []).append(entry)
    return entry


def list_ingested_ppts(registry: dict[str, Any]) -> list[dict[str, Any]]:
    files = [f for f in registry.get("files", []) if f.get("file_name", "").lower().endswith((".ppt", ".pptx"))]
    return sorted(files, key=lambda x: x.get("latest_ingested_at", ""), reverse=True)

