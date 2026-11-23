# Architecture of the companion relay

Covers what this fork adds. The wire protocol's authoritative text is the docstring at the top of
`src/companion/relay.py`.

## Flow

```text
FAF lobby server
      | WebSocket (authenticated by the desktop client only)
      v
ServerConnection.processDataFromServer  (src/client/connection.py)
      | 1. real client dispatch
      | 2. relay.on_server_line(line)
      v
CompanionRelay  (src/companion/relay.py)
      | ws:// on one LAN address, port 6900, game_info only
      v
FAF Mobile app (repo faf-mobile-client), read-only viewer
```

`ServerConnection` builds the relay once through `CompanionRelay.create_safe`. Its `disconnected`
signal calls `on_source_offline`.

## Wire summary

| Direction | Message | Meaning |
|---|---|---|
| Phone to relay | `hello` + `token` | Pairing check, must arrive within 10 s |
| Relay to phone | `hello_ok` | Accepted |
| Relay to phone | `source_offline` | Desktop has no live FAF lobby link |
| Relay to phone | `snapshot_begin` / `snapshot_end` + `epoch` | Bracket the full lobby list. The epoch counter is shared, so each phone's snapshot gets its own number |
| Relay to phone | `game_info` | Lobby entry, in a snapshot or streamed live |

Each message is one JSON object, newline-terminated.

## Rules the code enforces

| Rule | How |
|---|---|
| Readiness | Only a full `game_info` batch (`games` list) sets source-ready. Earlier incremental lines are ignored |
| Isolation | Guarded import, wrapped construction and callbacks. An internal error disables the relay only |
| Untrusted input | Pre-auth messages capped at 4096 bytes. Bad JSON or a bad hello cannot trip the kill switch |
| Limits | 4 paired phones, 8 sockets waiting for auth |
| Bind | One LAN address, resolved once. On failure the relay stays off and never falls back to all interfaces |
| Address choice | `FAF_COMPANION_BIND_IP`, else the default route if it is a real adapter, else the first real adapter (192.168.x first). VPN and virtual adapters are filtered by name |

## Settings

Stored in QSettings INI format, user scope, org `ForgedAllianceForever`, app `FA Lobby`.

| Setting | Default | Use |
|---|---|---|
| `companion/enabled` | `false` | Turns the relay on |
| `companion/port` | `6900` | Listen port |
| `companion/token` | generated | 128-bit hex. A missing or shorter than 32-character value is replaced at start |
| env `FAF_COMPANION_ENABLED` | unset | `1`, `true` or `yes` turns the relay on |
| env `FAF_COMPANION_BIND_IP` | unset | Forces the bind address |

## User-facing surface

The fork adds **no desktop window or control**. The user sees:

| Surface | Content |
|---|---|
| `setup_companion.ps1` console | Progress and next steps |
| `~/faf_companion_pairing.txt` | IP, port, token |
| Client log | Relay state. The token is kept out of it |
| Phone Play tab | Waiting, connected and lobby list (owned by `faf-mobile-client`) |

## Security

Trusted-LAN, experimental. The token travels over cleartext `ws://`, so it stops casual access but not
a malicious device on the same Wi-Fi. See `BACKLOG.md` B4 and B7.
