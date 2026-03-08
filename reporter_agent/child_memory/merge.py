from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _session_event_key(event: dict[str, Any]) -> str:
    role = event.get("role", "")
    msg = event.get("message", "")
    return f"{role}|{msg}"


def preview_child_merge(source_root: Path, target_root: Path) -> dict[str, Any]:
    src_sessions_dir = source_root / "sessions"
    tgt_sessions_dir = target_root / "sessions"
    src_session_files = {p.name for p in src_sessions_dir.glob("*.json")} if src_sessions_dir.exists() else set()
    tgt_session_files = {p.name for p in tgt_sessions_dir.glob("*.json")} if tgt_sessions_dir.exists() else set()

    src_reg = _load_json(source_root / "ingestion_registry.json", {"files": []})
    tgt_reg = _load_json(target_root / "ingestion_registry.json", {"files": []})
    src_hashes = {f.get("content_hash") for f in src_reg.get("files", []) if f.get("content_hash")}
    tgt_hashes = {f.get("content_hash") for f in tgt_reg.get("files", []) if f.get("content_hash")}

    preview = {
        "source_sessions": len(src_session_files),
        "target_sessions": len(tgt_session_files),
        "session_file_overlap": len(src_session_files.intersection(tgt_session_files)),
        "source_registry_items": len(src_hashes),
        "target_registry_items": len(tgt_hashes),
        "registry_new_to_target": len(src_hashes - tgt_hashes),
        "registry_duplicates": len(src_hashes.intersection(tgt_hashes)),
    }
    return preview


def _merge_sessions(source_root: Path, target_root: Path) -> tuple[int, int]:
    src_dir = source_root / "sessions"
    tgt_dir = target_root / "sessions"
    tgt_dir.mkdir(parents=True, exist_ok=True)

    merged_sessions = 0
    merged_events = 0

    if not src_dir.exists():
        return merged_sessions, merged_events

    for src_file in src_dir.glob("*.json"):
        tgt_file = tgt_dir / src_file.name
        src = _load_json(src_file, {"history": []})
        tgt = _load_json(tgt_file, {"history": []})
        src_hist = src.get("history", [])
        tgt_hist = tgt.get("history", [])

        seen = {_session_event_key(e) for e in tgt_hist}
        for ev in src_hist:
            key = _session_event_key(ev)
            if key not in seen:
                tgt_hist.append(ev)
                seen.add(key)
                merged_events += 1
        tgt["history"] = tgt_hist
        _save_json(tgt_file, tgt)
        merged_sessions += 1
    return merged_sessions, merged_events


def _merge_registry(source_root: Path, target_root: Path) -> tuple[int, int]:
    src_path = source_root / "ingestion_registry.json"
    tgt_path = target_root / "ingestion_registry.json"
    src = _load_json(src_path, {"files": []})
    tgt = _load_json(tgt_path, {"files": []})

    existing = {f.get("content_hash") for f in tgt.get("files", []) if f.get("content_hash")}
    added = 0
    duplicates = 0
    for item in src.get("files", []):
        h = item.get("content_hash")
        if h and h in existing:
            duplicates += 1
            continue
        tgt.setdefault("files", []).append(item)
        if h:
            existing.add(h)
        added += 1
    _save_json(tgt_path, tgt)
    return added, duplicates


def _merge_knowledge_base(source_root: Path, target_root: Path) -> int:
    src = _load_json(source_root / "knowledge_base.json", {"slides": [], "generated_at": ""})
    tgt = _load_json(target_root / "knowledge_base.json", {"slides": [], "generated_at": ""})
    seen = {
        f"{s.get('source_file','')}|{s.get('slide_index','')}|{s.get('raw_text','')[:80]}"
        for s in tgt.get("slides", [])
    }
    added = 0
    for s in src.get("slides", []):
        key = f"{s.get('source_file','')}|{s.get('slide_index','')}|{s.get('raw_text','')[:80]}"
        if key in seen:
            continue
        tgt.setdefault("slides", []).append(s)
        seen.add(key)
        added += 1
    if added:
        tgt["generated_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(target_root / "knowledge_base.json", tgt)
    return added


def _merge_template_profile(source_root: Path, target_root: Path, strategy: str) -> str:
    src_path = source_root / "template" / "template_profile.json"
    tgt_path = target_root / "template" / "template_profile.json"
    if not src_path.exists() and not tgt_path.exists():
        return "none"
    if src_path.exists() and not tgt_path.exists():
        _save_json(tgt_path, _load_json(src_path, {}))
        return "source_only"
    if tgt_path.exists() and not src_path.exists():
        return "target_only"

    src = _load_json(src_path, {})
    tgt = _load_json(tgt_path, {})
    if strategy == "master_priority":
        return "kept_target"
    if strategy == "recency_weighted":
        if src_path.stat().st_mtime >= tgt_path.stat().st_mtime:
            _save_json(tgt_path, src)
            return "replaced_with_source_recent"
        return "kept_target_recent"
    if strategy == "quality_weighted":
        src_score = sum(1 for v in src.values() if v)
        tgt_score = sum(1 for v in tgt.values() if v)
        if src_score > tgt_score:
            _save_json(tgt_path, src)
            return "replaced_with_source_quality"
        return "kept_target_quality"

    _save_json(tgt_path, src)
    return "replaced_with_source_default"


def apply_child_merge(source_root: Path, target_root: Path, strategy: str = "union_dedup") -> dict[str, Any]:
    preview = preview_child_merge(source_root, target_root)
    merged_sessions, merged_events = _merge_sessions(source_root, target_root)
    reg_added, reg_dupes = _merge_registry(source_root, target_root)
    kb_added = _merge_knowledge_base(source_root, target_root)
    profile_resolution = _merge_template_profile(source_root, target_root, strategy)

    report = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "preview": preview,
        "result": {
            "sessions_processed": merged_sessions,
            "events_added": merged_events,
            "registry_added": reg_added,
            "registry_duplicates": reg_dupes,
            "knowledge_slides_added": kb_added,
            "template_resolution": profile_resolution,
        },
    }

    report_path = target_root / "child" / "merge_reports" / f"merge_{_now_slug()}.json"
    _save_json(report_path, report)
    report["report_path"] = str(report_path)
    return report

