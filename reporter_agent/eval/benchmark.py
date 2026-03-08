from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter

from ..indexer import load_knowledge_base
from ..planner import build_report_plan
from ..retrieval import semantic_search


@dataclass
class BenchmarkResult:
    kb_path: str
    index_dir: str
    search_query: str
    search_top_k: int
    search_time_s: float
    plan_time_s: float
    total_time_s: float
    plan_slides: int

    def to_dict(self) -> dict:
        return asdict(self)


def run_benchmark(
    kb_path: Path,
    index_dir: Path,
    search_query: str,
    search_top_k: int,
    task_name: str,
    task_desc: str,
    report_type: str,
    semantic_top_k: int,
) -> BenchmarkResult:
    t0 = perf_counter()
    kb = load_knowledge_base(kb_path)

    ts = perf_counter()
    _ = semantic_search(query=search_query, index_dir=index_dir, top_k=search_top_k)
    search_time = perf_counter() - ts

    tp = perf_counter()
    plan = build_report_plan(
        kb=kb,
        task_name=task_name,
        task_description=task_desc,
        report_type=report_type,
        semantic_index_dir=index_dir,
        semantic_top_k=semantic_top_k,
        enable_semantic=True,
    )
    plan_time = perf_counter() - tp
    total = perf_counter() - t0

    return BenchmarkResult(
        kb_path=str(kb_path),
        index_dir=str(index_dir),
        search_query=search_query,
        search_top_k=search_top_k,
        search_time_s=round(search_time, 4),
        plan_time_s=round(plan_time, 4),
        total_time_s=round(total, 4),
        plan_slides=len(plan.slides),
    )


def save_benchmark(result: BenchmarkResult, output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

