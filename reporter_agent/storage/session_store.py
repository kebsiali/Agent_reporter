from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _session_path(sessions_dir: Path, session_id: str) -> Path:
    return sessions_dir / f"{session_id}.json"


def load_session(sessions_dir: Path, session_id: str) -> dict[str, Any]:
    path = _session_path(sessions_dir, session_id)
    if not path.exists():
        return {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "history": [],
            "report_type": "simulation_request",
            "task_name": "",
            "task_description": "",
            "current_plan": None,
            "accepted_slides": [],
            "rejected_slides": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(sessions_dir: Path, data: dict[str, Any]) -> Path:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _session_path(sessions_dir, data["session_id"])
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def append_history(data: dict[str, Any], role: str, message: str) -> None:
    data.setdefault("history", []).append({"role": role, "message": message})

