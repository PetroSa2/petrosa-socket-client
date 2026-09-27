"""Guards against copied database guidance in socket-client documentation."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
STALE_DB_GUIDANCE = re.compile(
    r"(?i)DB_ADAPTER=mysql|MYSQL_URI|mysql_adapter|MySQLAdapter|via MySQL"
)


def test_non_archive_docs_have_no_database_guidance() -> None:
    files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    assert files
    offenders = [
        str(path.relative_to(ROOT))
        for path in files
        if STALE_DB_GUIDANCE.search(path.read_text())
    ]
    assert offenders == []


def test_packaging_has_no_database_extras() -> None:
    for name in ("pyproject.toml", "requirements.txt"):
        line = next(
            line
            for line in (ROOT / name).read_text().splitlines()
            if "petrosa-otel" in line
        )
        assert not re.search(r"\[(?:[^]]*(?:mysql|mongodb|all)[^]]*)\]", line, re.I)


def test_tmp_path_negative_case(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("socket-client publishes to NATS; no database connection.\n")
    assert not STALE_DB_GUIDANCE.search(clean.read_text())


def test_no_db_driver_installed() -> None:
    for driver in ("pymysql", "pymongo"):
        if importlib.util.find_spec(driver) is not None:
            pytest.skip(f"dev dependency provides {driver}")
    assert importlib.util.find_spec("pymysql") is None
    assert importlib.util.find_spec("pymongo") is None
