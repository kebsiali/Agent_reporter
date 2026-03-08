from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReporterConfig:
    data_dir: Path
    output_dir: Path
    log_level: str


def load_config() -> ReporterConfig:
    data_dir = Path(os.getenv("REPORTER_DATA_DIR", "data"))
    output_dir = Path(os.getenv("REPORTER_OUTPUT_DIR", "output"))
    log_level = os.getenv("REPORTER_LOG_LEVEL", "INFO").upper()
    return ReporterConfig(
        data_dir=data_dir,
        output_dir=output_dir,
        log_level=log_level,
    )

