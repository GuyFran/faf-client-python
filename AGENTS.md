# FAF Python Client (fork) — agent guide

**Authority order:** `~/.claude/CLAUDE.md` (global) → `Documents\Projects\AGENTS.md` → this file. There
is no project `CLAUDE.md`.
**Owner and commit identity:** GuyFran — guynemerp@free.fr. Older commits (2026-09-01/02) are authored
"Guy Dev"; leave history as is.
**Branch:** `companion-relay`, pushed to `origin` = `GuyFran/faf-client-python`. `develop` tracks the
upstream base. Never push to `FAForever/client`.

## What this is
Fork of the **legacy FAForever Python lobby client** (`FAForever/client`), which upstream has
discontinued in favour of `downlords-faf-client`.

The fork adds a small **LAN companion relay**, so the FAF Mobile app (repo `faf-mobile-client`) can
mirror this client's live open-lobby list. The phone never logs into FAF. Its chat and ratings talk to
FAF directly and don't involve the relay.

**State:** Active. Current detail and test results: [docs/STATUS.md](docs/STATUS.md).

## Stack
Python **3.14+**, PyQt6 (**6.11.0** pinned, Qt WebSockets and Network used by the relay), scipy,
pyqtgraph. Dependencies in `requirements.txt`. Frozen builds through cx_Freeze (`setup.py`).

## Version
**No static version string is checked in. Do not add one.** `src/config/version.py` computes it from
`git describe --tags`, or from a git-ignored `RELEASE-VERSION` file written at build time from
`BUILD_VERSION`. The fork sits on upstream tag **0.27.6** plus its own commits. Run `git describe --tags`
for the current value.

**Conflict with the global rule, open for the owner** ([O1](docs/BACKLOG.md)): the global rule wants a
hand-bumped constant. A static fork version would diverge from upstream and bypass `version.py`, so
nothing is bumped. To honour the commit-prefix rule, commits since 2026-11-24 start with the value the
commit will have in `git describe`, without the hash (e.g. `0.27.6-17 docs: …`).

## Must not break
- **Relay off by default.** On with env `FAF_COMPANION_ENABLED=1` or setting `companion/enabled=true`,
  then restart.
- **Isolation:** nothing in the relay may disturb the real client.
- **Only `game_info` leaves the PC** (`FORWARDED_COMMANDS`).
- **Source-ready:** the phone shows connected only while this client holds a live FAF lobby link.
- **Security tier:** trusted-LAN, experimental. Cleartext `ws://` with a 128-bit pairing token.
- ⚠️ **Log into FAF from a physical machine, never a VM.** The anti-smurf UID fingerprints the machine
  and a VM fingerprint can flag or ban the account. Do not launch and log in as a verification step.

## Run & test
Use the repo's `.venv\Scripts\python.exe`.

| Task | Command |
|---|---|
| Setup and run | `.\setup_companion.ps1` |
| Run | `python -m src` (set `FAF_COMPANION_ENABLED=1` for the relay) |
| Relay tests | `python -m pytest tests/companion/test_relay.py -q` |
| Full suite | `python runtests.py` (`tests/companion` currently crashes at collection, [B1](docs/BACKLOG.md)) |
| Frozen build | `setup.py` through cx_Freeze, needs `BUILD_VERSION` |
| CI | `.github/workflows/checks.yml`, `release.yml` (upstream's) |

## Read order
1. `AGENTS.md` — this file
2. [docs/STATUS.md](docs/STATUS.md) — current state and test results
3. [docs/BACKLOG.md](docs/BACKLOG.md) — open, owner decisions, done
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — relay flow, rules, settings, user-facing surface
5. [COMPANION.md](COMPANION.md) — user guide. Stays at the root because the relay's log message names it
6. `src/companion/relay.py` — authoritative wire protocol
7. `tests/companion/` — behaviour and isolation contracts
8. [docs/CHANGELOG.md](docs/CHANGELOG.md) — fork history
9. Consumer: the `AGENTS.md` of the separate `faf-mobile-client` repo

Upstream's `readme.md`, `changelog.md` and `.github/*.md` describe the legacy client and are left
unedited to keep upstream merges clean.
