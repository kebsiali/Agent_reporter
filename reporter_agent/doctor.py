from __future__ import annotations

from pathlib import Path


def run_doctor(kb_path: Path, index_dir: Path) -> list[str]:
    checks: list[str] = []

    # Dependency checks
    for pkg, import_name in [
        ("python-pptx", "pptx"),
        ("sentence-transformers", "sentence_transformers"),
        ("faiss-cpu", "faiss"),
        ("numpy", "numpy"),
    ]:
        try:
            __import__(import_name)
            checks.append(f"[OK] Dependency available: {pkg}")
        except Exception:  # noqa: BLE001
            checks.append(f"[WARN] Missing dependency: {pkg}")

    # Filesystem checks
    if kb_path.exists():
        checks.append(f"[OK] Knowledge base found: {kb_path}")
    else:
        checks.append(f"[WARN] Knowledge base not found: {kb_path}")

    index_file = index_dir / "semantic.index"
    meta_file = index_dir / "semantic_meta.json"
    if index_file.exists() and meta_file.exists():
        checks.append(f"[OK] Semantic index files found in: {index_dir}")
    else:
        checks.append(f"[WARN] Semantic index files missing in: {index_dir}")

    return checks

