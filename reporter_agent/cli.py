from __future__ import annotations

import argparse
from pathlib import Path

from .chat import handle_chat
from .config import load_config
from .eval import run_benchmark, save_benchmark
from .exporter import export_plan_json, export_plan_markdown, export_plan_pptx
from .indexer import build_knowledge_base, load_knowledge_base, save_knowledge_base
from .logging_utils import configure_logging
from .planner import build_report_plan
from .retrieval import build_semantic_index, semantic_search


def build_parser() -> argparse.ArgumentParser:
    cfg = load_config()
    parser = argparse.ArgumentParser(
        prog="reporter-agent",
        description="Local-first PPT report planner using historical slide content.",
    )
    parser.add_argument(
        "--log-level",
        default=cfg.log_level,
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index pptx files into local knowledge base")
    p_index.add_argument("--source-dir", required=True, type=Path, help="Folder with old PPTX files")
    p_index.add_argument(
        "--kb-out",
        type=Path,
        default=cfg.data_dir / "knowledge_base.json",
        help="Output KB JSON path",
    )
    p_index.add_argument(
        "--index-dir",
        type=Path,
        default=cfg.data_dir / "index",
        help="Directory for semantic vector index files",
    )
    p_index.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name for semantic index",
    )
    p_index.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip building semantic embedding index",
    )
    p_index.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    p_index.add_argument(
        "--device",
        default=None,
        help="Embedding device (e.g. cuda, cpu). Default lets backend choose.",
    )
    p_index.add_argument(
        "--no-embedding-cache",
        action="store_true",
        help="Disable local embedding cache during indexing",
    )

    p_plan = sub.add_parser("plan", help="Generate new report plan from local KB")
    p_plan.add_argument("--kb", required=True, type=Path, help="Knowledge base json path")
    p_plan.add_argument("--task-name", required=True, help="Short task title")
    p_plan.add_argument("--task-desc", required=True, help="Task description/context")
    p_plan.add_argument(
        "--report-type",
        default="simulation_request",
        choices=[
            "simulation_request",
            "literature_review",
            "model_calibration",
            "model_sensitivity_analysis",
        ],
        help="Template type",
    )
    p_plan.add_argument("--out-dir", type=Path, default=cfg.output_dir, help="Output folder")
    p_plan.add_argument(
        "--index-dir",
        type=Path,
        default=cfg.data_dir / "index",
        help="Directory containing semantic index files for planning",
    )
    p_plan.add_argument(
        "--semantic-top-k",
        type=int,
        default=4,
        help="Number of semantic matches considered per section",
    )
    p_plan.add_argument(
        "--no-semantic",
        action="store_true",
        help="Disable semantic retrieval during plan generation",
    )
    p_plan.add_argument(
        "--skip-pptx",
        action="store_true",
        help="Skip draft pptx export",
    )

    p_search = sub.add_parser("search", help="Semantic search over indexed slides")
    p_search.add_argument("--query", required=True, help="Search query")
    p_search.add_argument(
        "--index-dir",
        type=Path,
        default=cfg.data_dir / "index",
        help="Directory containing semantic index files",
    )
    p_search.add_argument("--top-k", type=int, default=5, help="Number of matches")
    p_search.add_argument(
        "--device",
        default=None,
        help="Embedding device for query encoding (e.g. cuda, cpu)",
    )

    p_chat = sub.add_parser("chat", help="Session-based chat with report planning memory")
    p_chat.add_argument("--session-id", required=True, help="Session identifier")
    p_chat.add_argument("--message", required=True, help="User message for the assistant")
    p_chat.add_argument("--kb", type=Path, default=cfg.data_dir / "knowledge_base.json")
    p_chat.add_argument("--index-dir", type=Path, default=cfg.data_dir / "index")
    p_chat.add_argument("--sessions-dir", type=Path, default=cfg.data_dir / "sessions")
    p_chat.add_argument(
        "--report-type",
        default="simulation_request",
        choices=[
            "simulation_request",
            "literature_review",
            "model_calibration",
            "model_sensitivity_analysis",
        ],
    )
    p_chat.add_argument("--semantic-top-k", type=int, default=5)

    p_bench = sub.add_parser("benchmark", help="Run local performance benchmark")
    p_bench.add_argument("--kb", type=Path, default=cfg.data_dir / "knowledge_base.json")
    p_bench.add_argument("--index-dir", type=Path, default=cfg.data_dir / "index")
    p_bench.add_argument("--query", required=True, help="Search query for benchmark")
    p_bench.add_argument("--search-top-k", type=int, default=5)
    p_bench.add_argument("--task-name", required=True)
    p_bench.add_argument("--task-desc", required=True)
    p_bench.add_argument(
        "--report-type",
        default="simulation_request",
        choices=[
            "simulation_request",
            "literature_review",
            "model_calibration",
            "model_sensitivity_analysis",
        ],
    )
    p_bench.add_argument("--semantic-top-k", type=int, default=4)
    p_bench.add_argument("--out-json", type=Path, default=cfg.output_dir / "benchmark.json")
    return parser


def cmd_index(
    source_dir: Path,
    kb_out: Path,
    index_dir: Path,
    embedding_model: str,
    skip_embeddings: bool,
    batch_size: int,
    device: str | None,
    no_embedding_cache: bool,
) -> int:
    kb = build_knowledge_base(source_dir)
    save_knowledge_base(kb, kb_out)
    print(f"[OK] Indexed {len(kb.slides)} slides -> {kb_out}")
    if not skip_embeddings and kb.slides:
        index_path, meta_path = build_semantic_index(
            kb=kb,
            index_dir=index_dir,
            embedding_model=embedding_model,
            batch_size=batch_size,
            device=device,
            use_embedding_cache=not no_embedding_cache,
        )
        print(f"[OK] Semantic index: {index_path}")
        print(f"[OK] Semantic metadata: {meta_path}")
    return 0


def cmd_plan(
    kb_path: Path,
    task_name: str,
    task_desc: str,
    report_type: str,
    out_dir: Path,
    index_dir: Path,
    semantic_top_k: int,
    no_semantic: bool,
    skip_pptx: bool,
) -> int:
    kb = load_knowledge_base(kb_path)
    plan = build_report_plan(
        kb=kb,
        task_name=task_name,
        task_description=task_desc,
        report_type=report_type,
        semantic_index_dir=index_dir,
        semantic_top_k=semantic_top_k,
        enable_semantic=not no_semantic,
    )
    slug = (
        "".join(c if c.isalnum() else "-" for c in task_name.lower()).strip("-")
        or "report-plan"
    )
    md_path = out_dir / f"{slug}.md"
    json_path = out_dir / f"{slug}.json"
    pptx_path = out_dir / f"{slug}.pptx"

    export_plan_markdown(plan, md_path)
    export_plan_json(plan, json_path)
    if not skip_pptx:
        export_plan_pptx(plan, pptx_path)

    print(f"[OK] Markdown: {md_path}")
    print(f"[OK] JSON: {json_path}")
    if not skip_pptx:
        print(f"[OK] PPTX: {pptx_path}")
    return 0


def cmd_search(query: str, index_dir: Path, top_k: int, device: str | None) -> int:
    hits = semantic_search(query=query, index_dir=index_dir, top_k=top_k, device=device)
    if not hits:
        print("[INFO] No matches found.")
        return 0

    for h in hits:
        print(
            f"[{h.rank}] score={h.score:.4f} | {h.section} | {h.title} | "
            f"{h.source_file}#slide-{h.slide_index}"
        )
        print(f"      {h.excerpt}")
    return 0


def cmd_chat(
    session_id: str,
    message: str,
    kb_path: Path,
    index_dir: Path,
    sessions_dir: Path,
    report_type: str,
    semantic_top_k: int,
) -> int:
    response, session_path = handle_chat(
        sessions_dir=sessions_dir,
        session_id=session_id,
        kb_path=kb_path,
        index_dir=index_dir,
        message=message,
        report_type=report_type,
        semantic_top_k=semantic_top_k,
    )
    print(response)
    print(f"[OK] Session saved: {session_path}")
    return 0


def cmd_benchmark(
    kb_path: Path,
    index_dir: Path,
    query: str,
    search_top_k: int,
    task_name: str,
    task_desc: str,
    report_type: str,
    semantic_top_k: int,
    out_json: Path,
) -> int:
    result = run_benchmark(
        kb_path=kb_path,
        index_dir=index_dir,
        search_query=query,
        search_top_k=search_top_k,
        task_name=task_name,
        task_desc=task_desc,
        report_type=report_type,
        semantic_top_k=semantic_top_k,
    )
    save_benchmark(result, out_json)
    print(f"[OK] Benchmark saved: {out_json}")
    print(
        f"search={result.search_time_s:.4f}s | plan={result.plan_time_s:.4f}s | "
        f"total={result.total_time_s:.4f}s | slides={result.plan_slides}"
    )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.log_level)
    if args.command == "index":
        return cmd_index(
            source_dir=args.source_dir,
            kb_out=args.kb_out,
            index_dir=args.index_dir,
            embedding_model=args.embedding_model,
            skip_embeddings=args.skip_embeddings,
            batch_size=args.batch_size,
            device=args.device,
            no_embedding_cache=args.no_embedding_cache,
        )
    if args.command == "plan":
        return cmd_plan(
            kb_path=args.kb,
            task_name=args.task_name,
            task_desc=args.task_desc,
            report_type=args.report_type,
            out_dir=args.out_dir,
            index_dir=args.index_dir,
            semantic_top_k=args.semantic_top_k,
            no_semantic=args.no_semantic,
            skip_pptx=args.skip_pptx,
        )
    if args.command == "search":
        return cmd_search(query=args.query, index_dir=args.index_dir, top_k=args.top_k, device=args.device)
    if args.command == "chat":
        return cmd_chat(
            session_id=args.session_id,
            message=args.message,
            kb_path=args.kb,
            index_dir=args.index_dir,
            sessions_dir=args.sessions_dir,
            report_type=args.report_type,
            semantic_top_k=args.semantic_top_k,
        )
    if args.command == "benchmark":
        return cmd_benchmark(
            kb_path=args.kb,
            index_dir=args.index_dir,
            query=args.query,
            search_top_k=args.search_top_k,
            task_name=args.task_name,
            task_desc=args.task_desc,
            report_type=args.report_type,
            semantic_top_k=args.semantic_top_k,
            out_json=args.out_json,
        )
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
