# herdr-focus-attention

Herdr plugin: jump to the next / previous agent needing attention.

Ranks agents by status priority (`blocked` > `done` > `idle` by default) and,
within the same status, most recent state change first. If the agent you are
already looking at is in the queue, it jumps to the one after (or before) it,
so repeated presses cycle through every agent that needs you. When no agent
needs attention, a toast says so instead of failing silently.

Shell (`focus-attention.sh`) and PowerShell (`focus-attention.ps1`) ports of
the same logic also work as plain `[[keys.command]]` entries; this plugin is
the shareable, configurable form.

## Install

```bash
herdr plugin install kuwa72/herdr-focus-attention
```

Requires Python 3.11+ as `python3` on `PATH` (standard library only).
On Windows 11 the `python3` app-execution alias works; otherwise install
Python from python.org / a store and make sure `python3` resolves.

## Keybinding

Herdr owns keybindings, so bind the actions in `~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "prefix+a"
type = "plugin_action"
command = "kuwa72.focus-attention.next"
description = "直近の入力待ちエージェントへ移動"

[[keys.command]]
key = "prefix+shift+a"
type = "plugin_action"
command = "kuwa72.focus-attention.prev"
description = "直近の入力待ちエージェントへ移動（逆順）"
```

Then apply:

```bash
herdr server reload-config
```

## Configuration

The plugin seeds a `config.toml` in its config dir on first run. Find it with:

```bash
herdr plugin config-dir kuwa72.focus-attention
```

```toml
# Agent statuses that count as "needs attention", highest priority first.
# Statuses not listed are never jumped to.
# Known statuses: blocked, done, working, idle, unknown
priority = ["blocked", "done", "idle"]

# "all" = consider agents in every workspace; "workspace" = active workspace only
scope = "all"
```

Config is read on every invocation; no reload needed.

## Differences from `martin-ro/herdr-next-agent`

- Focuses by `pane_id` (the other plugin passes `terminal_id`, which the
  agent API rejects with `agent_not_found`).
- Sorts same-status agents by most recent state change (`state_change_seq`),
  not by opaque terminal id order.
- Ships a `prev` action for reverse cycling.

## Troubleshooting

```bash
herdr plugin action invoke kuwa72.focus-attention.next
herdr plugin log list --plugin kuwa72.focus-attention
```

## License

0BSD — see [LICENSE](LICENSE).
