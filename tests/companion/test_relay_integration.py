"""
Connection-level isolation tests.

Prove the core promise at the integration point: a broken companion relay must never interrupt
the real FAF client's per-line lobby dispatch. Uses mocked Qt/API objects — no real sockets.
"""
import json
from unittest import mock

import pytest

import src.client.connection as conn
from src.client.connection import ServerConnection
from src.config import Settings

# NOTE: `qapp` below is pytest-qt's built-in fixture (a real QApplication) — see test_relay.py.


@pytest.fixture
def sc(qapp, monkeypatch):
    # Replace the heavy Qt socket + API accessor so ServerConnection can be built in isolation.
    monkeypatch.setattr(conn, "QWebSocket", mock.MagicMock)
    monkeypatch.setattr(conn, "UserApiAccessor", mock.MagicMock)
    monkeypatch.setattr(Settings, "get", staticmethod(lambda key, default=None, type=str: default))
    monkeypatch.setattr(Settings, "set", staticmethod(lambda *a, **k: None))
    dispatch = mock.MagicMock()
    return ServerConnection("host", 1234, dispatch), dispatch


class FaultyRelay:
    """Every entry point explodes; the client must survive all of them."""
    def on_server_line(self, line):
        raise RuntimeError("injected on_server_line fault")

    def on_source_offline(self):
        raise RuntimeError("injected on_source_offline fault")


def _two_game_lines():
    return (
        json.dumps({"command": "game_info", "uid": 1, "state": "open"})
        + "\n"
        + json.dumps({"command": "game_info", "uid": 2, "state": "open"})
    )


def test_relay_fault_does_not_stop_dispatch(sc):
    connection, dispatch = sc
    connection.companion_relay = FaultyRelay()
    connection.processDataFromServer(_two_game_lines())
    # Both lobby lines must reach the real dispatcher despite the relay raising on the first.
    assert dispatch.call_count == 2
    # And the faulty relay must be disabled so it can't keep interfering.
    assert connection.companion_relay is None


def test_no_relay_still_dispatches(sc):
    connection, dispatch = sc
    connection.companion_relay = None
    connection.processDataFromServer(json.dumps({"command": "game_info", "uid": 1, "state": "open"}))
    assert dispatch.call_count == 1


def test_source_offline_fault_is_swallowed(sc):
    connection, dispatch = sc
    connection.companion_relay = FaultyRelay()
    connection._companion_source_offline()  # must not raise
    assert connection.companion_relay is None


def test_ping_is_answered_not_dispatched(sc):
    connection, dispatch = sc
    connection.companion_relay = FaultyRelay()
    connection.send = mock.MagicMock()
    connection.processDataFromServer(json.dumps({"command": "ping"}))
    connection.send.assert_called_once()          # answered with pong
    assert dispatch.call_count == 0               # ping is not a dispatched command
