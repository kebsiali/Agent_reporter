import json
import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.chat import handle_chat


def _write_kb(path):
    payload = {
        "generated_at": "2026-03-08T00:00:00+00:00",
        "slides": [
            {
                "source_file": "a.pptx",
                "slide_index": 1,
                "title": "Objective",
                "raw_text": "Objective and scope for calibration task",
                "section": "objective",
                "key_phrases": ["objective", "scope", "calibration"],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _test_root() -> Path:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_chat_creates_session_and_plan() -> None:
    root = _test_root()
    kb_path = root / "kb.json"
    _write_kb(kb_path)

    response, session_path = handle_chat(
        sessions_dir=root / "sessions",
        session_id="s1",
        kb_path=kb_path,
        index_dir=root / "index",
        message="new task: calibration update for compressor map",
        report_type="simulation_request",
        semantic_top_k=3,
    )

    assert "Created new plan" in response
    assert session_path.exists()
    shutil.rmtree(root, ignore_errors=True)


def test_chat_revise_slide() -> None:
    root = _test_root()
    kb_path = root / "kb.json"
    _write_kb(kb_path)
    sessions_dir = root / "sessions"

    handle_chat(
        sessions_dir=sessions_dir,
        session_id="s2",
        kb_path=kb_path,
        index_dir=root / "index",
        message="new task: sensitivity analysis for turbine model",
        report_type="model_sensitivity_analysis",
        semantic_top_k=3,
    )

    response, _ = handle_chat(
        sessions_dir=sessions_dir,
        session_id="s2",
        kb_path=kb_path,
        index_dir=root / "index",
        message="revise slide 1: Updated objective from user edits",
        report_type="model_sensitivity_analysis",
        semantic_top_k=3,
    )
    assert "Updated slide 1" in response
    shutil.rmtree(root, ignore_errors=True)
