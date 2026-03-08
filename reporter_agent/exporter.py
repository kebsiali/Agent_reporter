from __future__ import annotations

import json
from pathlib import Path

from .models import ReportPlan


def export_plan_json(plan: ReportPlan, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")


def export_plan_markdown(plan: ReportPlan, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Report Plan: {plan.task_name}")
    lines.append("")
    lines.append(f"- Report type: `{plan.report_type}`")
    lines.append(f"- Generated at: `{plan.created_at}`")
    lines.append("")
    lines.append("## Assumptions")
    for a in plan.assumptions:
        lines.append(f"- {a}")
    lines.append("")

    for s in plan.slides:
        lines.append(f"## Slide {s.slide_number}: {s.title} ({s.section})")
        lines.append(f"Objective: {s.objective}")
        lines.append("")
        lines.append("Auto-fill draft:")
        lines.append("")
        lines.append(s.autofill_text)
        lines.append("")
        lines.append("Placeholders:")
        for p in s.placeholders:
            lines.append(f"- {p}")
        lines.append("")
        lines.append("Missing info guidance:")
        for g in s.missing_info_guidance:
            lines.append(f"- {g}")
        lines.append("")
        lines.append("Source examples:")
        if s.source_examples:
            for src in s.source_examples:
                lines.append(f"- {src}")
        else:
            lines.append("- None")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_plan_pptx(plan: ReportPlan, output_path: Path) -> None:
    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "python-pptx is required for PPT export. Install with: python -m pip install python-pptx"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    for planned in plan.slides:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = f"{planned.slide_number}. {planned.title}"
        body = slide.shapes.placeholders[1].text_frame
        body.clear()

        p = body.paragraphs[0]
        p.text = f"Section: {planned.section}"
        p.level = 0

        p = body.add_paragraph()
        p.text = "Draft:"
        p.level = 0

        p = body.add_paragraph()
        p.text = planned.autofill_text[:1200]
        p.level = 1

        p = body.add_paragraph()
        p.text = "Fill these:"
        p.level = 0
        for placeholder in planned.placeholders:
            p = body.add_paragraph()
            p.text = placeholder
            p.level = 1

        left = Inches(0.5)
        top = Inches(6.4)
        width = Inches(12.3)
        height = Inches(0.5)
        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_box.text_frame.text = "Missing info guidance: " + "; ".join(
            planned.missing_info_guidance
        )

    prs.save(str(output_path))
