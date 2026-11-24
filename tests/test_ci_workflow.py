"""Checks that the CI workflow keeps the guarantees the docs promise.

The workflow is read as text: a YAML parser would be a new dependency for a handful of checks.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def section(text: str, start: str, end: str | None = None) -> str:
    assert start in text, f"missing {start!r}"
    after = text.split(start, 1)[1]
    if end is None:
        return after
    assert end in after, f"missing {end!r} after {start!r}"
    return after.split(end, 1)[0]


def test_triggers_on_push_and_pull_request(workflow: str) -> None:
    on_block = section(workflow, "\non:", "\njobs:")
    assert re.search(r"^\s+push:", on_block, re.MULTILINE)
    assert re.search(r"^\s+pull_request:", on_block, re.MULTILINE)


def test_checks_job_runs_every_local_check_on_both_python_versions(workflow: str) -> None:
    checks = section(workflow, "\n  checks:", "\n  secrets:")
    assert re.search(r"python-version:\s*\[\s*\"3\.12\",\s*\"3\.13\"\s*\]", checks)
    assert re.search(
        r"astral-sh/setup-uv@\S+\s+with:\s+python-version:\s*\$\{\{\s*matrix\.python-version\s*\}\}",
        checks,
    ), "the matrix version must reach setup-uv, or both legs run the same Python"
    for command in (
        "uv sync --locked",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run mypy",
        "uv run pytest --cov=flightboard --cov-report=term-missing",
    ):
        assert command in checks, command


def test_secrets_job_scans_full_history_with_pinned_verified_gitleaks(workflow: str) -> None:
    secrets_job = section(workflow, "\n  secrets:")
    assert "fetch-depth: 0" in secrets_job
    assert re.search(r"VERSION:\s*\d+\.\d+\.\d+", secrets_job)
    assert re.search(r"SHA256:\s*[0-9a-f]{64}", secrets_job)
    assert re.search(r"curl [^\n]*/v\$\{VERSION\}/\$\{archive\}", secrets_job)
    verify = secrets_job.index('echo "${SHA256}  ${archive}" | sha256sum -c -')
    assert verify < secrets_job.index("tar -xzf"), "verify the download before unpacking it"
    assert re.search(r"gitleaks git .*--log-opts=\"--all\"", secrets_job)


def test_uses_no_secrets_and_keeps_live_tests_excluded(workflow: str) -> None:
    assert "secrets." not in workflow
    pytest_steps = re.findall(r"uv run pytest[^\n]*", workflow)
    assert pytest_steps
    assert not any(re.search(r"\s-m\b", step) for step in pytest_steps), (
        "CI must not override the marker"
    )
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"addopts\s*=.*-m\s*['\"]?not live", pyproject)


def test_every_action_is_pinned_to_a_major_version(workflow: str) -> None:
    refs = re.findall(r"uses:\s*([\w./-]+)@(\S+)", workflow)
    assert refs
    for action, ref in refs:
        assert re.fullmatch(r"v\d+(\.\d+)*|[0-9a-f]{40}", ref), f"{action}@{ref}"


def test_readme_shows_the_ci_badge() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "/actions/workflows/ci.yml/badge.svg" in readme
