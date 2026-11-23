# Status

Source of truth for current state and test results. Last reviewed **2026-11-24** by reading the code;
nothing was built, run or tested in that pass.

**State:** Active, branch `companion-relay`. Version comes from `git describe --tags` (see `AGENTS.md`).

| Area | State |
|---|---|
| Companion relay (`src/companion/relay.py`) | Built: failure isolation, framed JSON, epoch-tagged snapshots, source-ready state, fail-closed bind, connection caps, kill switch |
| Client hook (`src/client/connection.py`) | Built: guarded import, relay fed after the real dispatch, offline signal on disconnect |
| One-shot setup (`setup_companion.ps1`) | Built: working Python 3.14, venv + dependencies, `faf-uid.exe` v4.0.6 in `natives\`, launch with relay on |
| VS Code tasks (`.vscode/tasks.json`) | Setup & Run, Run, Show pairing info, Companion tests (runs `test_relay.py` only) |
| Desktop UI for the relay | None. Enabled by environment variable or settings key |
| Base lobby client | Upstream legacy client, unchanged apart from the relay hook |

## Test results

| Suite | Tests | Last observed result |
|---|---|---|
| `tests/companion/test_relay.py` | 14 | **14 passed**, 2026-11-04, FILESERVER1, `.venv`, Python 3.14.7, PyQt6 6.11.0 |
| `tests/companion/test_relay_integration.py` | 4 | **Crashes the interpreter at collection**, 2026-11-04, same setup (exit `0xC0000409`). See `BACKLOG.md` B1 |
| Full desktop suite | not counted | Not run on this fork |
| GitHub Actions | n/a | `gh run list` showed no run for this branch on 2026-11-24 |
| Live phone to desktop | n/a | Not run against the real forked client |
