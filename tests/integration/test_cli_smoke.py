from reporter_agent.cli import build_parser


def test_cli_has_index_and_plan_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["index", "--source-dir", "C:\\reports", "--kb-out", "data\\knowledge_base.json"]
    )
    assert args.command == "index"

    args = parser.parse_args(
        ["search", "--query", "calibration results", "--index-dir", "data\\index", "--top-k", "3"]
    )
    assert args.command == "search"
    assert args.top_k == 3

    args = parser.parse_args(
        ["chat", "--session-id", "abc", "--message", "new task: do calibration", "--kb", "data\\knowledge_base.json"]
    )
    assert args.command == "chat"
    assert args.session_id == "abc"

    args = parser.parse_args(
        [
            "benchmark",
            "--query",
            "calibration result",
            "--task-name",
            "bench run",
            "--task-desc",
            "test benchmark",
        ]
    )
    assert args.command == "benchmark"
    assert args.search_top_k == 5

    args = parser.parse_args(["doctor"])
    assert args.command == "doctor"

    args = parser.parse_args(["gui", "--host", "127.0.0.1", "--port", "8010"])
    assert args.command == "gui"
    assert args.port == 8010

    args = parser.parse_args(
        [
            "plan",
            "--kb",
            "data\\knowledge_base.json",
            "--task-name",
            "t1",
            "--task-desc",
            "d1",
            "--template-pptx",
            "company_template.pptx",
        ]
    )
    assert args.template_pptx.name == "company_template.pptx"

    args = parser.parse_args(
        ["child-export", "--child-id", "CHILD", "--project-root", "data\\gui_projects\\default_project"]
    )
    assert args.command == "child-export"

    args = parser.parse_args(
        [
            "child-import",
            "--bundle-zip",
            "data\\bundle.zip",
            "--project-root",
            "data\\gui_projects\\default_project",
        ]
    )
    assert args.command == "child-import"
