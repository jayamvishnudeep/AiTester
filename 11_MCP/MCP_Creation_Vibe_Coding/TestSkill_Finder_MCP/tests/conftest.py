import shutil
from pathlib import Path

import pytest
from fastmcp import Client

from test_skill_finder_mcp.catalog import load_catalog
from test_skill_finder_mcp.server import build_server
from test_skill_finder_mcp.settings import DEFAULT_SKILLS_DIR, Settings


def make_settings(skills_dir: Path, profile: str = "full") -> Settings:
    return Settings(skills_dir=skills_dir, profile=profile, upstream_repo="PramodDutta/skillmasterclass",
                    upstream_branch="main", upstream_path="skillmasterclass/skills")


@pytest.fixture(scope="session")
def catalog():
    """The real skills folder, read once."""
    return load_catalog(DEFAULT_SKILLS_DIR)


@pytest.fixture(scope="session")
def read_server():
    """A server on the real skills folder, for tests that only read."""
    return build_server(make_settings(DEFAULT_SKILLS_DIR))


@pytest.fixture
async def client(read_server):
    async with Client(read_server) as connected:
        yield connected


@pytest.fixture
def skills_dir(tmp_path) -> Path:
    """A copy of the skills folder that tests may change."""
    return Path(shutil.copytree(DEFAULT_SKILLS_DIR, tmp_path / "skills"))


@pytest.fixture
async def write_client(skills_dir):
    """A server on the copy, so creating skills never touches the real folder."""
    async with Client(build_server(make_settings(skills_dir))) as connected:
        yield connected


async def call(client: Client, tool: str, **arguments) -> dict:
    result = await client.call_tool(tool, arguments)
    return result.structured_content
