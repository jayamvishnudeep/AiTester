"""Settings, read from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
DEFAULT_CSV = PROJECT_DIR / "data" / "vwo_5000_test_cases.csv"


@dataclass(frozen=True)
class Settings:
    csv_path: Path  # the test case library; read only
    new_cases_path: Path  # where create_test_case appends; the library file is never edited
    ranking_path: Path  # the scoring weights for the top lists and suites
    profile: str  # "full", or "readonly" to hide the tools that write
    max_limit: int  # the most test cases one call returns


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    csv_path = _path(env.get("TC_MCP_CSV")) or DEFAULT_CSV
    profile = (env.get("TC_MCP_PROFILE") or "full").strip().lower()
    if profile not in ("full", "readonly"):
        raise ValueError(f"TC_MCP_PROFILE must be 'full' or 'readonly', not {profile!r}")
    return Settings(
        csv_path=csv_path,
        new_cases_path=_path(env.get("TC_MCP_NEW_CASES")) or csv_path.with_name("new_test_cases.csv"),
        ranking_path=_path(env.get("TC_MCP_RANKING")) or PACKAGE_DIR / "ranking.yaml",
        profile=profile,
        max_limit=max(1, int(env.get("TC_MCP_MAX_LIMIT") or 100)),
    )


def _path(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value and value.strip() else None
