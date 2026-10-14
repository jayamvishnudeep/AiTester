"""Settings, read from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
DEFAULT_SKILLS_DIR = PROJECT_DIR / "skills"


@dataclass(frozen=True)
class Settings:
    skills_dir: Path  # the source of truth: one folder per skill, each with a SKILL.md
    profile: str  # "full", or "readonly" to hide the tools that write
    upstream_repo: str  # GitHub owner/name the upstream skills come from
    upstream_branch: str
    upstream_path: str  # folder inside the repository that holds the skills


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    profile = (env.get("TSF_PROFILE") or "full").strip().lower()
    if profile not in ("full", "readonly"):
        raise ValueError(f"TSF_PROFILE must be 'full' or 'readonly', not {profile!r}")
    skills = env.get("TSF_SKILLS_DIR")
    return Settings(
        skills_dir=Path(skills).expanduser().resolve() if skills and skills.strip() else DEFAULT_SKILLS_DIR,
        profile=profile,
        upstream_repo=env.get("TSF_UPSTREAM_REPO") or "PramodDutta/skillmasterclass",
        upstream_branch=env.get("TSF_UPSTREAM_BRANCH") or "main",
        upstream_path=(env.get("TSF_UPSTREAM_PATH") or "skillmasterclass/skills").strip("/"),
    )
