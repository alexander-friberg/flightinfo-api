"""Terminal input and output, passed in rather than called directly, so the UI is testable."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Console:
    """`read(prompt)` returns one line the user typed; `write(text)` shows one line.

    The app passes `input` and `print`; tests pass a script of answers and a list to collect
    the output.
    """

    read: Callable[[str], str]
    write: Callable[[str], None]
