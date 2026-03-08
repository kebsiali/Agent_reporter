import json
import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.child_memory import export_child_bundle, import_child_bundle


def _root() -> Path:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_child_bundle_export_import_roundtrip() -> None:
    root = _root()
    project = root / "projectA"
    (project / "sessions").mkdir(parents=True, exist_ok=True)
    (project / "template").mkdir(parents=True, exist_ok=True)
    (project / "sessions" / "s1.json").write_text(json.dumps({"history": []}), encoding="utf-8")
    (project / "ingestion_registry.json").write_text(json.dumps({"files": []}), encoding="utf-8")

    bundle = export_child_bundle(
        child_id="CHILD",
        project_root=project,
        bundle_out_dir=root / "exports",
    )
    assert bundle.exists()

    target = root / "projectB"
    target.mkdir(parents=True, exist_ok=True)
    result = import_child_bundle(
        bundle_zip=bundle,
        project_root=target,
        snapshots_dir=root / "snapshots",
    )
    assert result["status"] == "ok"
    assert (target / "sessions" / "s1.json").exists()

    shutil.rmtree(root, ignore_errors=True)

