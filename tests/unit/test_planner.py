from reporter_agent.models import ReportKnowledgeBase, SlideRecord
from reporter_agent.planner import build_report_plan


def test_build_report_plan_returns_expected_structure() -> None:
    kb = ReportKnowledgeBase(
        generated_at="2026-03-08T00:00:00+00:00",
        slides=[
            SlideRecord(
                source_file="sample.pptx",
                slide_index=1,
                title="Objective",
                raw_text="Objective reduce calibration error for compressor model",
                section="objective",
                key_phrases=["objective", "calibration", "error"],
            ),
            SlideRecord(
                source_file="sample.pptx",
                slide_index=2,
                title="Results",
                raw_text="Results show 12 percent reduction in error after tuning",
                section="results",
                key_phrases=["results", "reduction", "error", "tuning"],
            ),
        ],
    )

    plan = build_report_plan(
        kb=kb,
        task_name="Calibration run",
        task_description="Need updated calibration report",
        report_type="model_calibration",
    )

    assert plan.task_name == "Calibration run"
    assert len(plan.slides) == 5
    assert plan.slides[0].section == "objective"
    assert all(slide.placeholders for slide in plan.slides)
    assert all(0.0 <= slide.confidence <= 1.0 for slide in plan.slides)
    assert all(slide.confidence_label in {"low", "medium", "high"} for slide in plan.slides)
    assert all(isinstance(slide.evidence_gaps, list) for slide in plan.slides)
