from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone

from .models import PlannedSlide, ReportKnowledgeBase, ReportPlan, SlideRecord


DEFAULT_STRUCTURES: dict[str, list[tuple[str, str]]] = {
    "simulation_request": [
        ("objective", "Objective and Scope"),
        ("methodology", "Method and Assumptions"),
        ("results", "Core Results"),
        ("sensitivity", "Sensitivity or Scenario Comparison"),
        ("conclusion", "Conclusion and Recommendation"),
    ],
    "literature_review": [
        ("objective", "Review Objective"),
        ("literature_review", "Relevant Literature Summary"),
        ("results", "Comparison Matrix"),
        ("conclusion", "Takeaways and Gaps"),
    ],
    "model_calibration": [
        ("objective", "Calibration Objective"),
        ("calibration", "Calibration Setup"),
        ("results", "Fit Quality Results"),
        ("sensitivity", "Parameter Sensitivity"),
        ("conclusion", "Calibration Recommendation"),
    ],
    "model_sensitivity_analysis": [
        ("objective", "Analysis Objective"),
        ("methodology", "Sweep Design"),
        ("sensitivity", "Sensitivity Results"),
        ("results", "Impact Ranking"),
        ("conclusion", "Actionable Decisions"),
    ],
}


GENERIC_MISSING_INFO_GUIDANCE = {
    "objective": [
        "Clarify exact business question and decision deadline.",
        "Capture constraints: model version, scenario bounds, and acceptance criteria.",
    ],
    "methodology": [
        "List solver/model settings from run configuration files.",
        "Record assumptions and exclusions from request notes.",
    ],
    "calibration": [
        "Collect reference dataset and calibration target metrics.",
        "Add before/after error values (RMSE, MAE, or domain KPI).",
    ],
    "sensitivity": [
        "Provide parameter ranges and step sizes used in sweeps.",
        "Attach ranked sensitivity metrics and top drivers.",
    ],
    "results": [
        "Add quantitative outputs (tables/charts) from latest simulation run.",
        "Include baseline vs variant comparison values.",
    ],
    "conclusion": [
        "State recommended action tied to numeric evidence.",
        "List unresolved risks and next validation step.",
    ],
    "literature_review": [
        "List paper/source IDs and evaluation criteria.",
        "Summarize relevance to your current model and known limitations.",
    ],
    "general": [
        "Add concrete data points and source references.",
    ],
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower()))


def _score_match(task_tokens: set[str], slide: SlideRecord) -> int:
    slide_tokens = set(slide.key_phrases) | _tokenize(f"{slide.title} {slide.raw_text[:300]}")
    return len(task_tokens.intersection(slide_tokens))


def _get_structure(report_type: str) -> list[tuple[str, str]]:
    if report_type in DEFAULT_STRUCTURES:
        return DEFAULT_STRUCTURES[report_type]
    return DEFAULT_STRUCTURES["simulation_request"]


def _top_examples(
    kb: ReportKnowledgeBase, task_tokens: set[str], section: str, n: int = 2
) -> list[SlideRecord]:
    candidates = [s for s in kb.slides if s.section == section]
    if not candidates:
        candidates = [s for s in kb.slides if s.section == "general"]
    scored = sorted(candidates, key=lambda s: _score_match(task_tokens, s), reverse=True)
    return scored[:n]


def _synthesize_text(examples: list[SlideRecord]) -> str:
    if not examples:
        return ""
    snippets = []
    for s in examples:
        first_lines = [line for line in s.raw_text.splitlines() if line.strip()][:3]
        if first_lines:
            snippets.append(" ".join(first_lines))
    return "\n".join(snippets[:2]).strip()


def _infer_placeholders(section: str) -> list[str]:
    placeholders = {
        "objective": [
            "[[FILL: exact business objective]]",
            "[[FILL: scope boundaries and exclusions]]",
        ],
        "methodology": [
            "[[FILL: model version / configuration ID]]",
            "[[FILL: assumptions list]]",
        ],
        "calibration": [
            "[[FILL: target dataset name]]",
            "[[FILL: calibration metric values before/after]]",
        ],
        "sensitivity": [
            "[[FILL: varied parameters and ranges]]",
            "[[FILL: sensitivity ranking table]]",
        ],
        "results": [
            "[[FILL: key result numbers]]",
            "[[FILL: chart/table references]]",
        ],
        "conclusion": [
            "[[FILL: recommendation]]",
            "[[FILL: risk/next-step statement]]",
        ],
        "literature_review": [
            "[[FILL: source list and publication years]]",
            "[[FILL: relevance and limitations summary]]",
        ],
    }
    return placeholders.get(section, ["[[FILL: content]]"])


def build_report_plan(
    kb: ReportKnowledgeBase,
    task_name: str,
    task_description: str,
    report_type: str,
) -> ReportPlan:
    structure = _get_structure(report_type)
    task_tokens = _tokenize(f"{task_name} {task_description}")

    slides: list[PlannedSlide] = []
    coverage_counter = defaultdict(int)

    for i, (section, default_title) in enumerate(structure, start=1):
        examples = _top_examples(kb, task_tokens, section)
        autofill_text = _synthesize_text(examples)
        source_examples = [f"{e.source_file}#slide-{e.slide_index}" for e in examples]
        coverage_counter[section] += len(examples)

        missing_guidance = GENERIC_MISSING_INFO_GUIDANCE.get(
            section, GENERIC_MISSING_INFO_GUIDANCE["general"]
        )
        placeholders = _infer_placeholders(section)

        if not autofill_text:
            autofill_text = "[[AUTO-FILL-UNAVAILABLE: no close historical example found]]"

        slides.append(
            PlannedSlide(
                slide_number=i,
                title=default_title,
                section=section,
                objective=f"Deliver the {section.replace('_', ' ')} part of the report.",
                autofill_text=autofill_text,
                placeholders=placeholders,
                missing_info_guidance=missing_guidance,
                source_examples=source_examples,
            )
        )

    assumptions = [
        f"Report type '{report_type}' mapped to default structure with {len(structure)} slides.",
        "Auto-fill content is derived only from local indexed PPT text.",
        "Placeholders must be replaced with project-specific evidence before sharing.",
    ]

    return ReportPlan(
        task_name=task_name,
        report_type=report_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        assumptions=assumptions,
        slides=slides,
    )

