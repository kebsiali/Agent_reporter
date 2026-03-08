from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..exporter import export_plan_json, export_plan_markdown, export_plan_pptx
from ..indexer import load_knowledge_base
from ..models import PlannedSlide, ReportPlan
from ..planner import build_report_plan
from ..retrieval import semantic_search
from ..storage import append_history, load_session, save_session


def _plan_from_dict(data: dict[str, Any]) -> ReportPlan:
    slides = [PlannedSlide(**slide) for slide in data.get("slides", [])]
    return ReportPlan(
        task_name=data.get("task_name", ""),
        report_type=data.get("report_type", "simulation_request"),
        created_at=data.get("created_at", ""),
        assumptions=data.get("assumptions", []),
        slides=slides,
    )


def _derive_task_name(message: str) -> str:
    cleaned = re.sub(r"\s+", " ", message.strip())
    words = cleaned.split(" ")
    return " ".join(words[:8]) if words else "New Task"


def _detect_report_type(message: str, default: str) -> str:
    m = message.lower()
    if "literature" in m or "paper" in m:
        return "literature_review"
    if "calibration" in m:
        return "model_calibration"
    if "sensitivity" in m:
        return "model_sensitivity_analysis"
    if "simulation" in m:
        return "simulation_request"
    return default


def _find_slide(plan: ReportPlan, slide_number: int) -> PlannedSlide | None:
    for s in plan.slides:
        if s.slide_number == slide_number:
            return s
    return None


def _reply_missing(plan: ReportPlan) -> str:
    lines = ["Missing information summary:"]
    for s in plan.slides:
        if not s.evidence_gaps:
            continue
        lines.append(f"- Slide {s.slide_number} ({s.section}): " + "; ".join(s.evidence_gaps))
    if len(lines) == 1:
        return "No major evidence gaps detected in the current plan."
    return "\n".join(lines)


def _reply_sources(plan: ReportPlan, slide_number: int) -> str:
    slide = _find_slide(plan, slide_number)
    if not slide:
        return f"Slide {slide_number} not found in current plan."
    if not slide.source_examples:
        return f"No sources stored for slide {slide_number}."
    lines = [f"Sources for slide {slide_number}:"]
    for src in slide.source_examples:
        lines.append(f"- {src}")
    return "\n".join(lines)


def _apply_revision(plan: ReportPlan, slide_number: int, revision_text: str) -> str:
    slide = _find_slide(plan, slide_number)
    if not slide:
        return f"Slide {slide_number} not found in current plan."
    slide.autofill_text = revision_text.strip()
    slide.confidence = 1.0
    slide.confidence_label = "high"
    slide.evidence_gaps = []
    return f"Updated slide {slide_number} draft text."


def _export_current_plan(plan: ReportPlan, out_dir: Path, prefix: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in prefix.lower()).strip("-") or "chat-plan"
    md_path = out_dir / f"{slug}.md"
    json_path = out_dir / f"{slug}.json"
    pptx_path = out_dir / f"{slug}.pptx"
    export_plan_markdown(plan, md_path)
    export_plan_json(plan, json_path)
    export_plan_pptx(plan, pptx_path)
    return f"Exported current plan:\n- {md_path}\n- {json_path}\n- {pptx_path}"


def handle_chat(
    sessions_dir: Path,
    session_id: str,
    kb_path: Path,
    index_dir: Path,
    message: str,
    report_type: str,
    semantic_top_k: int,
) -> tuple[str, Path]:
    state = load_session(sessions_dir=sessions_dir, session_id=session_id)
    append_history(state, "user", message)

    kb = load_knowledge_base(kb_path)
    plan = _plan_from_dict(state["current_plan"]) if state.get("current_plan") else None
    msg = message.strip()
    msg_l = msg.lower()

    revise_match = re.match(r"^revise slide (\d+)\s*:\s*(.+)$", msg, flags=re.IGNORECASE)
    sources_match = re.match(r"^show sources slide (\d+)$", msg, flags=re.IGNORECASE)
    accept_match = re.match(r"^accept slide (\d+)$", msg, flags=re.IGNORECASE)
    reject_match = re.match(r"^reject slide (\d+)\s*:\s*(.+)$", msg, flags=re.IGNORECASE)

    if msg_l.startswith("new task:") or plan is None:
        task_desc = msg.split(":", 1)[1].strip() if ":" in msg else msg
        task_name = _derive_task_name(task_desc)
        inferred_type = _detect_report_type(task_desc, report_type)
        plan = build_report_plan(
            kb=kb,
            task_name=task_name,
            task_description=task_desc,
            report_type=inferred_type,
            semantic_index_dir=index_dir,
            semantic_top_k=semantic_top_k,
            enable_semantic=True,
        )
        state["task_name"] = task_name
        state["task_description"] = task_desc
        state["report_type"] = inferred_type
        state["current_plan"] = plan.to_dict()
        response = (
            f"Created new plan with {len(plan.slides)} slides for `{inferred_type}`.\n"
            "Next commands: `what is missing`, `show sources slide 2`, "
            "`revise slide 3: ...`, `export plan`."
        )
    elif msg_l == "what is missing":
        response = _reply_missing(plan)
    elif sources_match:
        response = _reply_sources(plan, int(sources_match.group(1)))
    elif revise_match:
        response = _apply_revision(plan, int(revise_match.group(1)), revise_match.group(2))
        state["current_plan"] = plan.to_dict()
    elif accept_match:
        n = int(accept_match.group(1))
        accepted = state.setdefault("accepted_slides", [])
        if n not in accepted:
            accepted.append(n)
        response = f"Accepted slide {n}. Saved to session memory."
    elif reject_match:
        n = int(reject_match.group(1))
        rejected = state.setdefault("rejected_slides", [])
        rejected.append({"slide": n, "reason": reject_match.group(2)})
        response = f"Rejected slide {n}. Reason recorded for future tuning."
    elif msg_l == "export plan":
        response = _export_current_plan(
            plan=plan,
            out_dir=sessions_dir / "exports",
            prefix=f"{session_id}-{state.get('task_name') or 'plan'}",
        )
    else:
        hits = semantic_search(query=msg, index_dir=index_dir, top_k=semantic_top_k)
        if not hits:
            response = "No relevant indexed evidence found. Try rephrasing or run `index` again."
        else:
            lines = ["Top relevant evidence:"]
            for h in hits:
                lines.append(
                    f"- [{h.rank}] {h.section} | {h.source_file}#slide-{h.slide_index} | score={h.score:.3f}"
                )
            response = "\n".join(lines)

    append_history(state, "assistant", response)
    session_path = save_session(sessions_dir=sessions_dir, data=state)
    return response, session_path

