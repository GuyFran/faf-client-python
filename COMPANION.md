# FAF Mobile Companion Relay

This fork adds a small **LAN relay** to the desktop client so the [FAF Mobile companion app]
can show the live open-lobby list on your phone. The phone never logs into FAF — this client
(already authenticated, already receiving `game_info`) mirrors the lobby list to the phone over
your home network. Chat and ratings on the phone talk to FAF directly and don't involve this.

**Security tier: trusted-LAN, experimental.** The pairing token travels over cleartext `ws://`,
which protects against casual access but NOT against a malicious device on the same Wi-Fi.
Don't enable it on networks you don't trust. (Pinned `wss://` is planned before wider sharing.)

> ⚠️ **Run this client on your PHYSICAL computer, not a VM.** FAF's anti-smurf check
> fingerprints the machine at login, and VM hardware fingerprints can flag (even auto-ban)
> an account. The relay itself is harmless anywhere — it's the FAF *login* that must come
> from real hardware.

## Quick start (Windows)

```powershell
git clone -b companion-relay https://github.com/GuyFran/faf-client-python.git faf-client-python
cd faf-client-python
.\setup_companion.ps1
```

The script installs Python 3.14 + dependencies on first run, then launches the client with
the relay enabled. Log into FAF, then pair the phone with the values from
`$HOME\faf_companion_pairing.txt`.

## Enable it (off by default)

Pick either:

- **Environment variable** (easiest): start the client with `FAF_COMPANION_ENABLED=1` set.
  - Windows (PowerShell): `$env:FAF_COMPANION_ENABLED = "1"` then launch the client from
    that shell.
- **Settings key**: set `companion/enabled` to `true` in the client's settings store
  (QSettings, org `ForgedAllianceForever`, app `FA Lobby`), then restart the client.

A restart is required either way — the relay starts with the client.

## Pair your phone

1. Start the (enabled) client and log into FAF.
2. Open **`faf_companion_pairing.txt` in your home folder** — the relay writes your
   `IP`, `PORT` (default 6900) and 128-bit `TOKEN` there (file is chmod 600 where supported).
3. On the phone: **Play tab → enter that IP / port / token → Save & Connect.**

The phone shows *Waiting for PC* until the client is logged into the FAF lobby, then the
open-lobby list appears and live-updates.

## Troubleshooting

- **Phone says "Can't reach PC relay"** — same Wi-Fi? Client running and enabled? Windows
  Firewall may prompt for port 6900 on first run. If the log says the relay bound `127.0.0.1`,
  the PC had no LAN address when the client started — restart it with the network up.
- **Phone stuck "pairing"** — token mismatch. Re-open the pairing file (the token changes only
  if regenerated) and re-enter it via the Play tab's *Edit connection* (gear icon).
- **Regenerate the token**: from a Python console inside the client process (or a future
  settings UI): `relay.regenerate_token()` — this rewrites the pairing file and disconnects
  all paired phones.
- The relay **cannot break the client**: any internal relay error disables the relay only;
  your normal FAF session is untouched (this is covered by tests in `tests/companion/`).

## What goes over the wire

Only lobby `game_info` (open games + player names per team). No chat, no private messages,
no tokens beyond the pairing handshake. Protocol details are documented at the top of
`src/companion/relay.py`.
