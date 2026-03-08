from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .migration import migrate_manifest
from .schema import CURRENT_SCHEMA_VERSION


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def export_child_bundle(
    child_id: str,
    project_root: Path,
    bundle_out_dir: Path,
    app_version: str = "0.1.0",
) -> Path:
    bundle_out_dir.mkdir(parents=True, exist_ok=True)
    staging = bundle_out_dir / f"{child_id}_bundle_{_now_slug()}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    memory_dir = staging / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    tracked = {
        "sessions": project_root / "sessions",
        "ingestion_registry": project_root / "ingestion_registry.json",
        "template_profile": project_root / "template" / "template_profile.json",
        "knowledge_base": project_root / "knowledge_base.json",
        "index_meta": project_root / "index" / "semantic_meta.json",
    }
    _copy_if_exists(tracked["sessions"], memory_dir / "sessions")
    _copy_if_exists(tracked["ingestion_registry"], memory_dir / "ingestion_registry.json")
    _copy_if_exists(tracked["template_profile"], memory_dir / "template_profile.json")
    _copy_if_exists(tracked["knowledge_base"], memory_dir / "knowledge_base.json")
    _copy_if_exists(tracked["index_meta"], memory_dir / "semantic_meta.json")

    checksums: dict[str, str] = {}
    for p in staging.rglob("*"):
        if p.is_file():
            rel = p.relative_to(staging).as_posix()
            checksums[rel] = _sha256_file(p)

    manifest = {
        "child_id": child_id,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app_version": app_version,
        "source_project_root": str(project_root),
        "files_count": len(checksums),
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (staging / "checksums.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")

    zip_path = bundle_out_dir / f"{child_id}_bundle_{_now_slug()}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in staging.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(staging).as_posix())

    shutil.rmtree(staging, ignore_errors=True)
    return zip_path


def _snapshot_project(project_root: Path, snapshots_dir: Path) -> Path:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = snapshots_dir / f"snapshot_{_now_slug()}"
    if snap_dir.exists():
        shutil.rmtree(snap_dir, ignore_errors=True)
    shutil.copytree(project_root, snap_dir, dirs_exist_ok=True)
    return snap_dir


def import_child_bundle(
    bundle_zip: Path,
    project_root: Path,
    snapshots_dir: Path,
) -> dict[str, Any]:
    if not bundle_zip.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_zip}")

    snapshot = _snapshot_project(project_root, snapshots_dir)
    extract_dir = snapshots_dir / f"import_extract_{_now_slug()}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(bundle_zip, "r") as zf:
        zf.extractall(extract_dir)

    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("Invalid CHILD bundle: manifest.json missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = migrate_manifest(manifest)

    memory_dir = extract_dir / "memory"
    if (memory_dir / "sessions").exists():
        _copy_if_exists(memory_dir / "sessions", project_root / "sessions")
    for src, dst in [
        (memory_dir / "ingestion_registry.json", project_root / "ingestion_registry.json"),
        (memory_dir / "template_profile.json", project_root / "template" / "template_profile.json"),
        (memory_dir / "knowledge_base.json", project_root / "knowledge_base.json"),
        (memory_dir / "semantic_meta.json", project_root / "index" / "semantic_meta.json"),
    ]:
        _copy_if_exists(src, dst)

    shutil.rmtree(extract_dir, ignore_errors=True)
    return {
        "status": "ok",
        "child_id": manifest.get("child_id"),
        "schema_version": manifest.get("schema_version"),
        "snapshot_path": str(snapshot),
        "project_root": str(project_root),
    }

