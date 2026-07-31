from pathlib import Path

import pytest

from emporio_agent.db.build_db import build
from emporio_agent.db.repository import Repository

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Base SQLite construída uma única vez, a partir dos CSVs reais do desafio."""
    path = tmp_path_factory.mktemp("db") / "emporio_test.sqlite3"
    build(data_dir=REPO_ROOT / "data", db_path=path)
    return path


@pytest.fixture(scope="session")
def repo(db_path: Path) -> Repository:
    return Repository(db_path)
