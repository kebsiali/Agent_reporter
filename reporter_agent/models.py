from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SlideRecord:
    source_file: str
    slide_index: int
    title: str
    raw_text: str
    section: str
    key_phrases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportKnowledgeBase:
    generated_at: str
    slides: list[SlideRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "slides": [s.to_dict() for s in self.slides],
        }


@dataclass
class PlannedSlide:
    slide_number: int
    title: str
    section: str
    objective: str
    confidence: float
    confidence_label: str
    autofill_text: str
    placeholders: list[str]
    evidence_gaps: list[str]
    missing_info_guidance: list[str]
    source_examples: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportPlan:
    task_name: str
    report_type: str
    created_at: str
    assumptions: list[str]
    slides: list[PlannedSlide]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "report_type": self.report_type,
            "created_at": self.created_at,
            "assumptions": self.assumptions,
            "slides": [s.to_dict() for s in self.slides],
        }
