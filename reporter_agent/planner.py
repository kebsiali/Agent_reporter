from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .models import PlannedSlide, ReportKnowledgeBase, ReportPlan, SlideRecord
from .retrieval import semantic_search


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


def _synthesize_from_semantic_hits(hit_lines: list[str]) -> str:
    if not hit_lines:
        return ""
    return "\n".join(hit_lines[:2]).strip()


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


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _keyword_confidence(task_tokens: set[str], examples: list[SlideRecord]) -> float:
    if not examples:
        return 0.0
    best = max(_score_match(task_tokens, s) for s in examples)
    return min(1.0, best / 8.0)


def _detect_evidence_gaps(section: str, text: str, task_description: str) -> list[str]:
    haystack = f"{text}\n{task_description}".lower()
    gaps: list[str] = []
    has_number = bool(re.search(r"\b\d+(\.\d+)?%?\b", haystack))

    if section in {"results", "calibration", "sensitivity"} and not has_number:
        gaps.append("No quantitative values detected.")
    if section == "results" and "baseline" not in haystack and "vs" not in haystack:
        gaps.append("Missing baseline-versus-variant comparison.")
    if section == "methodology" and "assumption" not in haystack:
        gaps.append("Assumptions are not explicitly stated.")
    if section == "calibration" and "dataset" not in haystack and "reference" not in haystack:
        gaps.append("Calibration reference dataset is not identified.")
    if section == "sensitivity" and "range" not in haystack and "sweep" not in haystack:
        gaps.append("Parameter range/sweep definition is missing.")
    if section == "conclusion" and "recommend" not in haystack:
        gaps.append("Recommendation statement is missing.")

    return gaps


def _gap_guidance(gaps: list[str]) -> list[str]:
    mapping = {
        "No quantitative values detected.": "Pull numeric KPIs from latest run outputs and add units.",
        "Missing baseline-versus-variant comparison.": "Add baseline case and at least one variant with delta.",
        "Assumptions are not explicitly stated.": "Copy assumptions from solver config and scope notes.",
        "Calibration reference dataset is not identified.": "Add dataset/source ID and time window used for fitting.",
        "Parameter range/sweep definition is missing.": "List min/max/step for each varied parameter.",
        "Recommendation statement is missing.": "State one explicit decision recommendation with rationale.",
    }
    return [mapping[g] for g in gaps if g in mapping]


def build_report_plan(
    kb: ReportKnowledgeBase,
    task_name: str,
    task_description: str,
    report_type: str,
    semantic_index_dir: Path | None = None,
    semantic_top_k: int = 4,
    enable_semantic: bool = True,
) -> ReportPlan:
    structure = _get_structure(report_type)
    task_tokens = _tokenize(f"{task_name} {task_description}")

    slides: list[PlannedSlide] = []

    for i, (section, default_title) in enumerate(structure, start=1):
        examples = _top_examples(kb, task_tokens, section)
        keyword_autofill = _synthesize_text(examples)
        source_examples = [f"{e.source_file}#slide-{e.slide_index}" for e in examples]
        confidence = _keyword_confidence(task_tokens, examples)

        semantic_lines: list[str] = []
        if enable_semantic and semantic_index_dir is not None:
            try:
                query = f"{task_name}. {task_description}. section: {section}"
                hits = semantic_search(query=query, index_dir=semantic_index_dir, top_k=semantic_top_k)
                for h in hits:
                    if h.section == section or h.section == "general":
                        semantic_lines.append(h.excerpt)
                        source_examples.append(f"{h.source_file}#slide-{h.slide_index}")
                if hits:
                    confidence = max(confidence, max(0.0, min(1.0, (hits[0].score + 1.0) / 2.0)))
            except Exception:  # noqa: BLE001
                # Graceful fallback: planning continues with keyword mode only.
                pass

        semantic_autofill = _synthesize_from_semantic_hits(semantic_lines)
        autofill_text = semantic_autofill or keyword_autofill

        missing_guidance = GENERIC_MISSING_INFO_GUIDANCE.get(
            section, GENERIC_MISSING_INFO_GUIDANCE["general"]
        )
        placeholders = _infer_placeholders(section)

        if not autofill_text:
            autofill_text = "[[AUTO-FILL-UNAVAILABLE: no close historical example found]]"
            confidence = 0.0

        evidence_gaps = _detect_evidence_gaps(section, autofill_text, task_description)
        if evidence_gaps:
            missing_guidance = missing_guidance + _gap_guidance(evidence_gaps)
            if "No quantitative values detected." in evidence_gaps:
                if "[[FILL: key result numbers]]" not in placeholders:
                    placeholders.append("[[FILL: key result numbers]]")
            if "Missing baseline-versus-variant comparison." in evidence_gaps:
                placeholders.append("[[FILL: baseline vs variant values]]")

        slides.append(
            PlannedSlide(
                slide_number=i,
                title=default_title,
                section=section,
                objective=f"Deliver the {section.replace('_', ' ')} part of the report.",
                confidence=round(confidence, 3),
                confidence_label=_confidence_label(confidence),
                autofill_text=autofill_text,
                placeholders=placeholders,
                evidence_gaps=evidence_gaps,
                missing_info_guidance=missing_guidance,
                source_examples=sorted(set(source_examples)),
            )
        )

    assumptions = [
        f"Report type '{report_type}' mapped to default structure with {len(structure)} slides.",
        "Auto-fill content is derived only from local indexed PPT text and optional local semantic retrieval.",
        "Placeholders must be replaced with project-specific evidence before sharing.",
    ]

    return ReportPlan(
        task_name=task_name,
        report_type=report_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        assumptions=assumptions,
        slides=slides,
    )
