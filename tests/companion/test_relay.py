"""
Isolation + snapshot-logic tests for the companion relay.

These exercise the pure logic (no real sockets) under a QCoreApplication, so they run in CI
without a display or an Android device. The central guarantee under test: a relay defect can
never raise out of on_server_line — it self-disables instead — so the real FAF client's lobby
dispatch is never disturbed.
"""
import json

import pytest
from PyQt6.QtCore import QCoreApplication

from src.companion.relay import CompanionRelay
from src.config import Settings


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def relay(qapp, monkeypatch):
    monkeypatch.setattr(Settings, "get", staticmethod(lambda key, default=None, type=str: default))
    monkeypatch.setattr(Settings, "set", staticmethod(lambda *a, **k: None))
    r = CompanionRelay()
    r.enabled = True
    r._server = object()          # pretend we're listening
    r._sent = []
    r._broadcast = lambda line: r._sent.append(line)  # capture instead of sending
    return r


def gi(**kw):
    return json.dumps({"command": "game_info", **kw})


def test_forwards_only_game_info(relay):
    relay.on_server_line(json.dumps({"command": "social", "channels": []}))
    relay.on_server_line(json.dumps({"command": "player_info", "players": []}))
    assert relay._sent == []


def test_single_game_recorded_and_forwarded(relay):
    relay.on_server_line(gi(uid=1, state="open", title="x"))
    assert relay._sent and 1 in relay._games


def test_batch_is_authoritative(relay):
    relay._games = {99: "stale"}
    relay.on_server_line(gi(games=[{"uid": 1, "state": "open"}, {"uid": 2, "state": "open"}]))
    assert set(relay._games) == {1, 2}  # the stale entry is gone


def test_closed_state_removes_game(relay):
    relay.on_server_line(gi(uid=1, state="open"))
    relay.on_server_line(gi(uid=1, state="closed"))
    assert 1 not in relay._games


def test_snapshot_entries_carry_command_envelope(relay):
    relay.on_server_line(gi(uid=7, state="open", title="t"))
    assert json.loads(relay._games[7])["command"] == "game_info"


def test_bad_json_is_ignored(relay):
    relay.on_server_line("this is not json")  # must not raise
    assert relay.enabled is True


def test_relay_defect_self_disables_without_raising(relay):
    def boom(_action):
        raise RuntimeError("injected failure")
    relay._record_game_info = boom
    # Must NOT raise — the client's dispatch loop must survive a broken relay.
    relay.on_server_line(gi(uid=1, state="open"))
    assert relay.enabled is False


def test_source_offline_clears_snapshot(relay):
    relay.on_server_line(gi(uid=1, state="open"))
    relay._clients = []          # no phones, just checking cache is cleared
    relay.on_source_offline()
    assert relay._games == {}
