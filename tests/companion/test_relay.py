"""
Isolation + snapshot-logic tests for the companion relay.

These exercise the pure logic (no real sockets) under a QCoreApplication, so they run in CI
without a display or an Android device. The central guarantee under test: a relay defect can
never raise out of on_server_line — it self-disables instead — so the real FAF client's lobby
dispatch is never disturbed. Readiness is authoritative-batch-only (Q3).
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


def batch(*games):
    return gi(games=list(games))


# -- forwarding scope --------------------------------------------------------
def test_forwards_only_game_info(relay):
    relay.on_server_line(json.dumps({"command": "social", "channels": []}))
    relay.on_server_line(json.dumps({"command": "player_info", "players": []}))
    assert relay._sent == []


def test_bad_json_is_ignored_without_disabling(relay):
    relay.on_server_line("this is not json")  # unparseable → skipped, relay stays up
    assert relay.enabled is True


# -- readiness is authoritative-batch-only (Q3) ------------------------------
def test_source_ready_starts_false(relay):
    assert relay._source_ready is False


def test_single_update_before_batch_is_ignored(relay):
    # No baseline yet: a lone incremental must NOT set ready, store, or broadcast.
    relay.on_server_line(gi(uid=1, state="open"))
    assert relay._source_ready is False
    assert relay._games == {}
    assert relay._sent == []


def test_batch_sets_source_ready(relay):
    relay.on_server_line(batch({"uid": 1, "state": "open"}))
    assert relay._source_ready is True


def test_update_after_batch_is_stored_and_streamed(relay):
    relay.on_server_line(batch())          # empty batch → ready, empty baseline
    relay._sent.clear()
    relay.on_server_line(gi(uid=2, state="open"))
    assert 2 in relay._games
    assert relay._sent  # streamed to phones


# -- snapshot content --------------------------------------------------------
def test_batch_is_authoritative(relay):
    relay._games = {99: "stale"}
    relay.on_server_line(batch({"uid": 1, "state": "open"}, {"uid": 2, "state": "open"}))
    assert set(relay._games) == {1, 2}  # the stale entry is gone


def test_closed_state_removes_game(relay):
    relay.on_server_line(batch({"uid": 1, "state": "open"}))
    relay.on_server_line(gi(uid=1, state="closed"))
    assert 1 not in relay._games


def test_snapshot_entries_carry_command_envelope(relay):
    relay.on_server_line(batch({"uid": 7, "state": "open", "title": "t"}))
    assert json.loads(relay._games[7])["command"] == "game_info"


# -- isolation + source lifecycle -------------------------------------------
def test_relay_defect_self_disables_without_raising(relay):
    def boom(*_a, **_k):
        raise RuntimeError("injected failure")
    relay._record_game_info = boom
    # A batch reaches _record_game_info; the injected fault must NOT raise out — it self-disables.
    relay.on_server_line(batch({"uid": 1, "state": "open"}))
    assert relay.enabled is False


def test_source_offline_clears_snapshot_and_ready(relay):
    relay.on_server_line(batch({"uid": 1, "state": "open"}))
    relay._clients = []          # no phones; just checking cache + flag reset
    relay.on_source_offline()
    assert relay._games == {}
    assert relay._source_ready is False
