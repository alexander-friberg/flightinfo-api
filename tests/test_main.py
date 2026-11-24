"""The composition root: argument parsing, the missing-key path, and an offline session."""

import builtins
import socket
from collections.abc import Iterator

import httpx
import pytest

from flightboard.__main__ import main, parse_args


def test_parse_args_defaults_to_online() -> None:
    assert parse_args([]).offline is False
    assert parse_args(["--offline"]).offline is True


def test_unknown_arguments_are_rejected() -> None:
    with pytest.raises(SystemExit) as raised:
        parse_args(["--nope"])

    assert raised.value.code == 2


def test_missing_key_online_is_a_clear_message_and_exit_code_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SWEDAVIA_API_KEY", raising=False)

    code = main([])

    captured = capsys.readouterr()
    assert code == 2
    assert "SWEDAVIA_API_KEY is not set" in captured.err
    assert "--offline" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def scripted_input(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> list[str]:
    prompts: list[str] = []
    it: Iterator[str] = iter(answers)

    def fake_input(prompt: str = "") -> str:
        prompts.append(prompt)
        return next(it)

    monkeypatch.setattr(builtins, "input", fake_input)
    return prompts


def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline mode tried to open a network connection")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


def test_offline_session_needs_no_key_no_network_and_says_it_is_offline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SWEDAVIA_API_KEY", raising=False)
    no_network(monkeypatch)
    scripted_input(monkeypatch, ["3", "AY808", "2026-11-24", "q"])

    code = main(["--offline"])

    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0].startswith("Swedavia FlightInfo API v2 – Offline sample data")
    assert "[1] → AY808  |  Finnair  (AY)" in out
    assert out.rstrip().endswith("Goodbye.")


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, EOFError])
def test_ctrl_c_or_end_of_input_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    interrupt: type[BaseException],
) -> None:
    def stop(prompt: str = "") -> str:
        raise interrupt

    monkeypatch.setattr(builtins, "input", stop)

    code = main(["--offline"])

    assert code == 0
    assert capsys.readouterr().out.rstrip().endswith("Goodbye.")


class ClosingTransport(httpx.MockTransport):
    """A fake Swedavia that also remembers whether the app closed its HTTP client."""

    def __init__(self) -> None:
        super().__init__(lambda request: httpx.Response(200, json="IsAlive"))
        self.requests_closed = False

    def close(self) -> None:
        self.requests_closed = True


def test_online_wiring_uses_the_cached_client_and_closes_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SWEDAVIA_API_KEY", "fake-key")
    scripted_input(monkeypatch, ["5", "q"])
    transport = ClosingTransport()
    sleeps: list[float] = []

    code = main([], transport=transport, sleep=sleeps.append)

    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0] == "Swedavia FlightInfo API v2 – Python client"
    assert "Ping 5: OK" in out
    assert "5 pings: 5 OK, 0 failed." in out
    assert sleeps == [2.0, 2.0, 2.0, 2.0]
    assert transport.requests_closed


def test_online_client_is_closed_after_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWEDAVIA_API_KEY", "fake-key")

    def stop(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", stop)
    transport = ClosingTransport()

    assert main([], transport=transport) == 0
    assert transport.requests_closed
