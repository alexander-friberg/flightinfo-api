from flightboard.cli.pager import page
from tests.fakes import ScriptedConsole


def render(index: int, item: str) -> str:
    return f"{index}:{item}"


def items(count: int) -> list[str]:
    return [f"f{i}" for i in range(1, count + 1)]


def shown(lines: list[str]) -> list[str]:
    return [line for line in lines if ":" in line and not line.startswith("──")]


def test_first_page_then_counter_and_prompt() -> None:
    script = ScriptedConsole(["q"])

    page(script.console, items(120), render)

    assert shown(script.lines) == [f"{i}:f{i}" for i in range(1, 51)]
    assert script.lines[-1] == "── Showing 50/120 ──  (70 left)"
    assert script.prompts == ["[Enter] next page | [a] show all | [q] back to menu: "]


def test_enter_shows_the_next_page_and_numbering_continues() -> None:
    script = ScriptedConsole(["", ""])

    page(script.console, items(120), render)

    assert shown(script.lines) == [f"{i}:f{i}" for i in range(1, 121)]
    assert "── Showing 50/120 ──  (70 left)" in script.lines
    assert "── Showing 100/120 ──  (20 left)" in script.lines
    assert len(script.prompts) == 2


def test_a_shows_everything_that_is_left_without_asking_again() -> None:
    script = ScriptedConsole(["a"])

    page(script.console, items(170), render)

    assert len(shown(script.lines)) == 170
    assert len(script.prompts) == 1


def test_q_goes_back_after_the_current_page() -> None:
    script = ScriptedConsole(["", "q"])

    page(script.console, items(170), render)

    assert len(shown(script.lines)) == 100
    assert script.unused_answers == []


def test_answers_are_case_and_space_insensitive_and_others_re_prompt() -> None:
    script = ScriptedConsole(["x", " A "])

    page(script.console, items(60), render)

    assert len(shown(script.lines)) == 60
    assert len(script.prompts) == 2


def test_a_short_list_needs_no_prompt() -> None:
    script = ScriptedConsole()

    page(script.console, items(3), render)

    assert shown(script.lines) == ["1:f1", "2:f2", "3:f3"]
    assert script.prompts == []


def test_exactly_one_full_page_needs_no_prompt() -> None:
    script = ScriptedConsole()

    page(script.console, items(50), render)

    assert len(shown(script.lines)) == 50
    assert script.prompts == []


def test_an_empty_list_says_so() -> None:
    script = ScriptedConsole()

    page(script.console, [], render)

    assert script.lines == ["No flights found."]
    assert script.prompts == []


def test_page_size_can_be_changed() -> None:
    script = ScriptedConsole(["q"])

    page(script.console, items(5), render, size=2)

    assert shown(script.lines) == ["1:f1", "2:f2"]
    assert script.lines[-1] == "── Showing 2/5 ──  (3 left)"


def test_the_empty_message_can_be_chosen() -> None:
    script = ScriptedConsole()

    page(script.console, [], render, empty_message="No destinations found.")

    assert script.lines == ["No destinations found."]
