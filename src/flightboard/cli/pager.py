"""Long lists, 50 at a time, as the original showed them."""

from collections.abc import Callable, Sequence

from flightboard.cli.io import Console

PAGE_SIZE = 50
PROMPT = "[Enter] next page | [a] show all | [q] back to menu: "


def page[T](
    console: Console,
    items: Sequence[T],
    render: Callable[[int, T], str],
    size: int = PAGE_SIZE,
    empty_message: str = "No flights found.",
) -> None:
    """Show `items` numbered from 1, pausing after each page while more remain.

    Enter shows the next page, `a` shows all the rest, `q` stops; anything else asks again.
    """
    if not items:
        console.write(empty_message)
        return
    shown = 0
    show_all = False
    while shown < len(items):
        end = len(items) if show_all else min(shown + size, len(items))
        for number in range(shown + 1, end + 1):
            console.write(render(number, items[number - 1]))
        shown = end
        if shown == len(items):
            return
        console.write(f"── Showing {shown}/{len(items)} ──  ({len(items) - shown} left)")
        answer = _ask(console)
        if answer == "q":
            return
        show_all = answer == "a"


def _ask(console: Console) -> str:
    while True:
        answer = console.read(PROMPT).strip().lower()
        if answer in ("", "a", "q"):
            return answer
