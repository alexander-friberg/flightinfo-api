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


def test_running_the_package_prints_placeholder() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flightboard"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Swedavia Flight Board" in result.stdout
