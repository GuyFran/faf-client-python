# FAF Python Client (fork) — agent guide

## What this is
Fork of the **legacy FAForever Python lobby client** (`FAForever/client`), repo
`GuyFran/faf-client-python`. Upstream is the discontinued desktop lobby client
(the officially supported client is `downlords-faf-client`).

The reason this fork exists lives on branch **`companion-relay`**: it adds a small
**LAN companion relay** so the [FAF Mobile companion app](../faf-mobile-client) can mirror
this desktop client's live open-lobby list to a phone on the same network. The phone never
logs into FAF — this already-authenticated client relays `game_info` over the LAN. Chat and
ratings on the phone talk to FAF directly and don't involve this relay.

## Stack
- Python **3.14+**, PyQt **6.7+** (Qt6 WebSockets/Network used by the relay), scipy + pyqtgraph.
- Deps: `requirements.txt`. Frozen builds via cx_Freeze (`setup.py`).

## Version
**No static version string is checked into this repo — do not add one.** The version is
computed at build/runtime by `src/config/version.py` from `git describe --tags` (or a
git-ignored `RELEASE-VERSION` file written at build time from the `BUILD_VERSION` env var).
As of 2026-09-11 `git describe` reports `0.27.6-<n>-g<sha>` — i.e. the fork sits a few commits
ahead of upstream tag **0.27.6**. There is nothing to hand-bump on a docs pass.

## Status (2026-09-11)
| Item | State |
|------|-------|
| Companion relay (`src/companion/relay.py`) | Done & hardened — failure-isolated, framed JSON, epoch-tagged authoritative snapshots, durable source-ready state, fail-closed bind, connection caps, kill-switch/enable path, lifecycle cleanup |
| Companion tests (`tests/companion/`) | 18 green — `test_relay.py` (14) + `test_relay_integration.py` (4), incl. failure injection |
| One-shot setup (`setup_companion.ps1`) | Done — finds/installs a *working* Python 3.14, installs deps, downloads `faf-uid.exe` into repo-root `natives\` if missing (client resolves `natives\` at the repo root via `fafpath.get_libdir`, not `src\natives`; without it login fails with "Failed to calculate UID"), then launches the client with the relay enabled |
| VS Code tasks (`.vscode/tasks.json`) | Setup & Run, Run, Show pairing info, Companion tests |
| Base lobby client | Upstream legacy client, unchanged apart from the relay hook |

## Companion relay — key facts
- **Off by default.** Enable with env `FAF_COMPANION_ENABLED=1` **or** settings key
  `companion/enabled=true` (QSettings org `ForgedAllianceForever`, app `FA Lobby`); restart required.
- **Wire:** one JSON object per WebSocket text message (also newline-terminated).
  `hello`(token) → `hello_ok`; `source_offline`; `snapshot_begin{epoch}` … `game_info` lines …
  `snapshot_end{epoch}`; then live `game_info` streamed. Only `game_info` ever leaves the PC
  (`FORWARDED_COMMANDS`). Default port **6900**. Full protocol at the top of `relay.py`.
- **Binds a real LAN adapter, not the VPN default route.** With a VPN up the default route goes
  through the tunnel, so the relay filters out VPN/host-only adapters by name and prefers a
  reachable home-LAN address (192.168.x over 10.x). `FAF_COMPANION_BIND_IP` overrides all
  detection when it picks the wrong interface.
- **Source-ready contract:** the phone shows CONNECTED only while this client actually holds a
  live FAF lobby link; before login / after disconnect the phone stays WAITING (never a
  misleading empty "connected").
- **Isolation contract:** nothing in the relay may disturb the real client — import is guarded
  at the call site, construction/start/callbacks are wrapped, cleanup never throws.
- **Security tier: trusted-LAN, experimental.** 128-bit pairing token over cleartext `ws://`;
  guards against casual access, NOT a malicious device on the same Wi-Fi. Pinned `wss://` is the
  planned gate before wider sharing.
- **Pairing:** the relay writes IP / PORT / TOKEN to `~/faf_companion_pairing.txt` (chmod 600
  where supported); enter them on the phone's Play tab. Regenerate via `relay.regenerate_token()`.
- ⚠️ Run on a **physical machine, not a VM** — FAF's anti-smurf UID fingerprints the machine at
  login and VM fingerprints can flag/ban an account. The relay itself is harmless; it's the FAF
  *login* that must come from real hardware.

## Run & test
- Run the client: `python -m src` (or the "FAF Client: Run" VS Code task).
- Tests: `python runtests.py`, or `python -m pytest tests/companion` for just the relay
  ("FAF Client: Companion tests" task).

## Backlog
| Item | Source / Date |
|------|---------------|
| Release gate: full desktop suite under real Python 3.14+/CI | mobile COLLAB §10.5 · 2026-09-11 |
| Release gate: live phone↔desktop e2e (real forked client, not mock) | mobile COLLAB §10.5 · 2026-09-11 |
| Pinned `wss://` + QR pairing before sharing beyond own devices | COMPANION.md · 2026-09-11 |
| Desktop settings UI for companion (enable / show pairing / regenerate) | COMPANION.md documents the interim env-var/settings-key path · 2026-09-11 |

## Read order
1. `AGENTS.md` — this file
2. `COMPANION.md` — setup, enable, pair, troubleshoot (user-facing)
3. `src/companion/relay.py` — the relay + authoritative wire-protocol docstring
4. `tests/companion/` — behaviour and failure-isolation contracts
5. `readme.md` — upstream legacy-client build/run notes (Windows/Linux)
6. Consumer: `../faf-mobile-client` (`RelayClient.kt`, `SnapshotAssembler.kt`) + its `COLLAB_PLAYTAB.md` §9–§10
