import shutil
from pathlib import Path
from uuid import uuid4

from reporter_agent.template.style import load_template_profile, save_template_profile


def test_template_profile_roundtrip() -> None:
    root = Path("data") / "test_tmp" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    p = root / "template_profile.json"
    payload = {
        "template_path": "x.pptx",
        "title_font_name": "Calibri",
        "title_font_size_pt": 32.0,
        "body_font_name": "Arial",
        "body_font_size_pt": 16.0,
    }
    save_template_profile(p, payload)
    loaded = load_template_profile(p)
    assert loaded is not None
    assert loaded["title_font_name"] == "Calibri"
    assert loaded["body_font_size_pt"] == 16.0
    shutil.rmtree(root, ignore_errors=True)
