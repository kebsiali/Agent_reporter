from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .extractor import extract_slide_records
from .models import ReportKnowledgeBase


def find_pptx_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.pptx"))


def build_knowledge_base(source_dir: Path) -> ReportKnowledgeBase:
    slides = []
    for pptx_path in find_pptx_files(source_dir):
        try:
            slides.extend(extract_slide_records(pptx_path))
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Skipping {pptx_path}: {exc}")
    return ReportKnowledgeBase(
        generated_at=datetime.now(timezone.utc).isoformat(),
        slides=slides,
    )


def build_knowledge_base_with_diagnostics(source_dir: Path) -> tuple[ReportKnowledgeBase, dict[str, Any]]:
    slides = []
    scanned = 0
    skipped_files: list[dict[str, str]] = []

    for pptx_path in find_pptx_files(source_dir):
        scanned += 1
        try:
            extracted = extract_slide_records(pptx_path)
            slides.extend(extracted)
            if not extracted:
                skipped_files.append(
                    {"file": str(pptx_path), "reason": "No extractable slide text found."}
                )
        except Exception as exc:  # noqa: BLE001
            skipped_files.append({"file": str(pptx_path), "reason": str(exc)})

    kb = ReportKnowledgeBase(
        generated_at=datetime.now(timezone.utc).isoformat(),
        slides=slides,
    )
    diagnostics = {
        "generated_at": kb.generated_at,
        "source_dir": str(source_dir),
        "files_scanned": scanned,
        "slides_indexed": len(slides),
        "files_skipped_count": len(skipped_files),
        "skipped_files": skipped_files,
    }
    return kb, diagnostics


def save_knowledge_base(kb: ReportKnowledgeBase, output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(kb.to_dict(), indent=2), encoding="utf-8")


def save_diagnostics(report: dict[str, Any], output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")


def load_knowledge_base(kb_json: Path) -> ReportKnowledgeBase:
    data = json.loads(kb_json.read_text(encoding="utf-8"))
    slides = data.get("slides", [])
    from .models import SlideRecord

    return ReportKnowledgeBase(
        generated_at=data.get("generated_at", ""),
        slides=[SlideRecord(**s) for s in slides],
    )
