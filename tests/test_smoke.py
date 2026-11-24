import importlib
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "flightboard",
        "flightboard.domain",
        "flightboard.api",
        "flightboard.services",
        "flightboard.cli",
        "flightboard.data",
    ],
)
def test_package_layers_import(module: str) -> None:
    importlib.import_module(module)


def test_the_package_runs_as_a_program() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flightboard", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--offline" in result.stdout
