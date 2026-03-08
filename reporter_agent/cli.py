from __future__ import annotations

import argparse
from pathlib import Path

from .exporter import export_plan_json, export_plan_markdown, export_plan_pptx
from .indexer import build_knowledge_base, load_knowledge_base, save_knowledge_base
from .planner import build_report_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporter-agent",
        description="Local-first PPT report planner using historical slide content.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index pptx files into local knowledge base")
    p_index.add_argument("--source-dir", required=True, type=Path, help="Folder with old PPTX files")
    p_index.add_argument(
        "--kb-out",
        type=Path,
        default=Path("data/knowledge_base.json"),
        help="Output KB JSON path",
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
    p_plan.add_argument("--out-dir", type=Path, default=Path("output"), help="Output folder")
    p_plan.add_argument(
        "--skip-pptx",
        action="store_true",
        help="Skip draft pptx export",
    )
    return parser


def cmd_index(source_dir: Path, kb_out: Path) -> int:
    kb = build_knowledge_base(source_dir)
    save_knowledge_base(kb, kb_out)
    print(f"[OK] Indexed {len(kb.slides)} slides -> {kb_out}")
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


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "index":
        return cmd_index(args.source_dir, args.kb_out)
    if args.command == "plan":
        return cmd_plan(
            kb_path=args.kb,
            task_name=args.task_name,
            task_desc=args.task_desc,
            report_type=args.report_type,
            out_dir=args.out_dir,
            skip_pptx=args.skip_pptx,
        )
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

