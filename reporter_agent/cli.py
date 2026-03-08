from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
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
    return parser


def cmd_index(
    source_dir: Path,
    kb_out: Path,
    index_dir: Path,
    embedding_model: str,
    skip_embeddings: bool,
) -> int:
    kb = build_knowledge_base(source_dir)
    save_knowledge_base(kb, kb_out)
    print(f"[OK] Indexed {len(kb.slides)} slides -> {kb_out}")
    if not skip_embeddings and kb.slides:
        index_path, meta_path = build_semantic_index(
            kb=kb,
            index_dir=index_dir,
            embedding_model=embedding_model,
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
    skip_pptx: bool,
) -> int:
    kb = load_knowledge_base(kb_path)
    plan = build_report_plan(
        kb=kb,
        task_name=task_name,
        task_description=task_desc,
        report_type=report_type,
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


def cmd_search(query: str, index_dir: Path, top_k: int) -> int:
    hits = semantic_search(query=query, index_dir=index_dir, top_k=top_k)
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
        )
    if args.command == "plan":
        return cmd_plan(
            kb_path=args.kb,
            task_name=args.task_name,
            task_desc=args.task_desc,
            report_type=args.report_type,
            out_dir=args.out_dir,
            skip_pptx=args.skip_pptx,
        )
    if args.command == "search":
        return cmd_search(query=args.query, index_dir=args.index_dir, top_k=args.top_k)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
