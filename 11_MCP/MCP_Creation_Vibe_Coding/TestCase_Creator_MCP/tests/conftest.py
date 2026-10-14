import csv
from pathlib import Path

import pytest
from fastmcp import Client

from test_creator_mcp.catalog import CatalogStore, load_catalog
from test_creator_mcp.ranking import Weights
from test_creator_mcp.server import build_server
from test_creator_mcp.settings import DEFAULT_CSV, PACKAGE_DIR, Settings


def make_settings(new_cases: Path, profile: str = "full", max_limit: int = 100) -> Settings:
    return Settings(csv_path=DEFAULT_CSV, new_cases_path=new_cases, ranking_path=PACKAGE_DIR / "ranking.yaml",
                    profile=profile, max_limit=max_limit)


@pytest.fixture(scope="session")
def raw_rows() -> list[dict[str, str]]:
    """The CSV read with the csv module only, to check the server's numbers independently."""
    with DEFAULT_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="session")
def catalog(tmp_path_factory):
    return load_catalog(DEFAULT_CSV, tmp_path_factory.mktemp("none") / "new_test_cases.csv")


@pytest.fixture(scope="session")
def weights() -> Weights:
    return Weights.load(PACKAGE_DIR / "ranking.yaml")


@pytest.fixture(scope="session")
def read_server(tmp_path_factory):
    """A server for read-only tests; its new-cases file stays empty."""
    return build_server(make_settings(tmp_path_factory.mktemp("read") / "new_test_cases.csv"))


@pytest.fixture
async def client(read_server):
    async with Client(read_server) as connected:
        yield connected


@pytest.fixture
def store(tmp_path) -> CatalogStore:
    return CatalogStore(DEFAULT_CSV, tmp_path / "new_test_cases.csv")


@pytest.fixture
async def write_client(tmp_path):
    """A server whose new cases go to a temporary file, never to the data folder."""
    async with Client(build_server(make_settings(tmp_path / "new_test_cases.csv"))) as connected:
        yield connected


async def call(client: Client, tool: str, **arguments) -> dict:
    result = await client.call_tool(tool, arguments)
    return result.structured_content
