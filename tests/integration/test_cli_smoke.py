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
