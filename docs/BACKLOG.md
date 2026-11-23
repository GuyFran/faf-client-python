# Backlog

## Open

| Id | Item | State | Source / date |
|---|---|---|---|
| B1 | `test_relay_integration.py` crashes pytest at collection (`0xC0000409`): importing `src.client.connection` runs `src/client/__init__.py`, which builds `ClientWindow()` before a QApplication exists. Make the import lazy or create the app first, then widen the VS Code test task to `tests/companion` | todo | docs pass, 2026-11-04 |
| B2 | Release gate: full desktop suite under Python 3.14+ and CI (no Actions run listed for this branch) | todo | mobile COLLAB §10.5, 2026-09-11; rechecked 2026-11-24 |
| B3 | Release gate: live phone to desktop test with the real forked client, not a mock | todo | mobile COLLAB §10.5, 2026-09-11 |
| B4 | Pinned `wss://` and QR pairing before sharing beyond the owner's devices | todo | `COMPANION.md`, 2026-09-11 |
| B5 | Desktop settings UI: enable, show pairing, regenerate token (`regenerate_token()` has no caller yet) | todo | `COMPANION.md`, 2026-09-11; code review 2026-11-24 |
| B6 | No heartbeat to phones: a phone that vanishes without closing can hold one of the 4 slots until TCP notices | todo, from code reading | docs pass, 2026-11-24 |
| B7 | On Windows, `os.chmod(path, 0o600)` does not restrict the pairing file to its owner; protection is only the user profile's permissions | todo, from code reading | docs pass, 2026-11-24 |
| B8 | LAN address is resolved once at start, so a network change needs a client restart | known limit | docs pass, 2026-11-24 |

## Owner decisions

| Id | Decision | Date raised |
|---|---|---|
| O1 | Version rule: the global rule wants a bumped `x.x.x` constant; this fork takes its version from upstream tags through `git describe`. See `AGENTS.md` | 2026-11-04 |

## Done

| Item | Date |
|---|---|
| LAN adapter bind (skips the VPN default route), `FAF_COMPANION_BIND_IP` override | 2026-09-02 (`78b268a0`) |
| `setup_companion.ps1`, `faf-uid.exe` in repo-root `natives\` | 2026-09-02 |
| Relay hardening (isolation, framing, snapshots, caps, kill switch) | 2026-09-01 / 02 |
