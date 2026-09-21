#!/usr/bin/env python3
"""Focus the next/previous agent needing attention.

Ranks agents from `herdr agent list` by a configurable status priority
(default: blocked > done > idle) and, within the same status, most recent
state change first. The first press jumps to the highest-priority agent;
while focus stays on the last jumped-to agent, repeated presses step
forward (or backward, with --prev) through the queue, so cycling reaches
every agent needing attention.
Requires Python 3.11+ (standard library only).
"""

import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

DEFAULT_CONFIG_TEXT = """\
# Agent statuses that count as "needs attention", highest priority first.
# Statuses not listed are never jumped to.
# Known statuses: blocked, done, working, idle, unknown
priority = ["blocked", "done", "idle"]

# "all" = consider agents in every workspace; "workspace" = active workspace only
scope = "all"
"""

DEFAULTS = {
    "priority": ["blocked", "done", "idle"],
    "scope": "all",
}

# Older than this, a recorded jump target no longer counts as mid-cycle:
# the user may have settled on that pane for unrelated work.
CYCLE_TTL_SECONDS = 600


def herdr_bin():
    # HERDR_BIN_PATH may carry a " (deleted)" suffix after an in-place update.
    bin_path = os.environ.get("HERDR_BIN_PATH", "").removesuffix(" (deleted)")
    if bin_path and Path(bin_path).is_file():
        return bin_path
    return shutil.which("herdr") or str(Path.home() / ".local" / "bin" / "herdr")


def load_config():
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if not config_dir:
        return dict(DEFAULTS)
    path = Path(config_dir) / "config.toml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG_TEXT)
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"focus-attention: ignoring invalid {path}: {e}", file=sys.stderr)
        raw = {}
    config = dict(DEFAULTS)
    if isinstance(raw.get("priority"), list):
        config["priority"] = [s for s in raw["priority"] if isinstance(s, str)]
    if raw.get("scope") in ("all", "workspace"):
        config["scope"] = raw["scope"]
    return config


def run_herdr(*args):
    result = subprocess.run(
        [herdr_bin(), *args], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(
            f"focus-attention: herdr {' '.join(args)} failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout


def state_path():
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / "state.json"
    base = Path(
        os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    )
    return base / "herdr-focus-attention" / "state.json"


def load_state():
    try:
        raw = json.loads(state_path().read_text())
    except (OSError, json.JSONDecodeError):
        return None
    pane_id = raw.get("pane_id")
    unix_ms = raw.get("unix_ms")
    if not isinstance(pane_id, str) or not isinstance(unix_ms, (int, float)):
        return None
    if time.time() - unix_ms / 1000 > CYCLE_TTL_SECONDS:
        return None
    return pane_id


def save_state(pane_id):
    path = state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"pane_id": pane_id, "unix_ms": int(time.time() * 1000)})
        )
    except OSError:
        pass


def notify(message):
    subprocess.run(
        [herdr_bin(), "notification", "show", message, "--sound", "none"],
        capture_output=True,
        timeout=10,
    )


def self_test():
    """Check herdr CLI compatibility without focusing anything. Exit-code oriented."""
    problems = []
    herdr = herdr_bin()

    def run(*args):
        try:
            return subprocess.run(
                [herdr, *args], capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            problems.append(f"herdr {' '.join(args)} failed to run: {e}")
            return None

    if not (Path(herdr).is_file() or shutil.which("herdr")):
        problems.append(f"herdr binary not found: {herdr}")

    r = run("agent", "list")
    if r is not None:
        if r.returncode != 0:
            problems.append(f"agent list failed: {r.stderr.strip()}")
        else:
            try:
                agents = json.loads(r.stdout)["result"]["agents"]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                problems.append(f"agent list: unexpected JSON shape: {e}")
            else:
                required = {
                    "agent_status",
                    "state_change_seq",
                    "focused",
                    "pane_id",
                    "workspace_id",
                }
                for a in agents:
                    missing = required - set(a)
                    if missing:
                        problems.append(
                            f"agent list: missing fields {sorted(missing)}"
                        )
                        break

    for args, needle in [(("agent",), "focus"), (("notification",), "show")]:
        r = run(*args)
        if r is not None and needle not in r.stdout + r.stderr:
            problems.append(f"herdr {' '.join(args)}: '{needle}' not found")

    for p in problems:
        print(f"focus-attention self-test: {p}", file=sys.stderr)
    if not problems:
        print("focus-attention self-test: ok")
    return 1 if problems else 0


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        sys.exit(self_test())
    prev = "--prev" in args
    states = [a for a in args if not a.startswith("-")] or None

    config = load_config()
    priority = states if states else config["priority"]

    agents = json.loads(run_herdr("agent", "list"))["result"]["agents"]

    if states is None and config["scope"] == "workspace":
        workspace = os.environ.get("HERDR_ACTIVE_WORKSPACE_ID") or os.environ.get(
            "HERDR_WORKSPACE_ID"
        )
        if workspace:
            agents = [a for a in agents if a.get("workspace_id") == workspace]

    ranked = sorted(
        (a for a in agents if a.get("agent_status") in priority),
        key=lambda a: (
            priority.index(a["agent_status"]),
            -(a.get("state_change_seq") or 0),
        ),
    )
    if not ranked:
        # Best-effort toast so an empty queue is distinguishable from a broken keybinding.
        notify("No agent needs attention")
        return

    focused_idx = next(
        (i for i, a in enumerate(ranked) if a.get("focused")), None
    )
    continuing = (
        focused_idx is not None
        and load_state() == ranked[focused_idx].get("pane_id")
    )
    if continuing:
        step = -1 if prev else 1
        target = ranked[(focused_idx + step) % len(ranked)]
    else:
        target = ranked[0]

    pane_id = target.get("pane_id")
    if not pane_id:
        print("focus-attention: ranked agent has no pane_id", file=sys.stderr)
        sys.exit(1)

    if focused_idx is not None and ranked[focused_idx].get("pane_id") == pane_id:
        notify("Already on the most urgent agent")
    else:
        run_herdr("agent", "focus", pane_id)
    save_state(pane_id)


if __name__ == "__main__":
    main()
