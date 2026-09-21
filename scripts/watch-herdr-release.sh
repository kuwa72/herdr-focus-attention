#!/usr/bin/env bash
# Watch for new herdr releases (and local herdr version changes), run the
# plugin's --self-test, and file a GitHub issue when compatibility breaks.
#
# State lives in $XDG_STATE_HOME/herdr-focus-attention-watch/last_seen as
# "release=<tag> local=<version>"; a run is skipped while both are unchanged.
# Requires: gh (authenticated), python3, herdr.
set -u

PLUGIN_REPO="kuwa72/herdr-focus-attention"
HERDR_REPO="herdrdev/herdr"
ISSUE_MARKER="herdr-compat-watch"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/herdr-focus-attention-watch"
STATE_FILE="$STATE_DIR/last_seen"
mkdir -p "$STATE_DIR"

tag="$(gh api "repos/$HERDR_REPO/releases/latest" --jq .tag_name 2>/dev/null || true)"
local_ver="$(herdr --version 2>/dev/null | awk '{print $2}')"
now="release=${tag:-unknown} local=${local_ver:-unknown}"
seen="$(cat "$STATE_FILE" 2>/dev/null || true)"
if [ "$now" = "$seen" ]; then
    exit 0
fi

plugin_py="$(
    for d in "$HOME"/.config/herdr/plugins/github/kuwa72.focus-attention-*/; do
        f="$d/focus_attention.py"
        [ -f "$f" ] && grep -lq -- '--self-test' "$f" && printf '%s\n' "$f"
    done | head -1
)"
# Fall back to a source checkout while the installed copy predates --self-test.
if [ -z "$plugin_py" ]; then
    for repo_py in \
        "$HOME/ghq/github.com/kuwa72/herdr-focus-attention/focus_attention.py" \
        "$(cd "$(dirname "$0")/.." && pwd)/focus_attention.py"; do
        if [ -f "$repo_py" ] && grep -q -- '--self-test' "$repo_py"; then
            plugin_py="$repo_py"
            break
        fi
    done
fi
if [ -z "$plugin_py" ]; then
    echo "watch: focus_attention.py with --self-test not found" >&2
    exit 1
fi

config_dir="$(herdr plugin config-dir kuwa72.focus-attention 2>/dev/null || true)"
[ -n "$config_dir" ] && export HERDR_PLUGIN_CONFIG_DIR="$config_dir"

if output="$(python3 "$plugin_py" --self-test 2>&1)"; then
    printf '%s\n' "$now" >"$STATE_FILE"
    exit 0
fi

open_issues="$(
    gh issue list --repo "$PLUGIN_REPO" --state open \
        --search "$ISSUE_MARKER" --json number --jq 'length' 2>/dev/null || echo 0
)"
if [ "$open_issues" = "0" ]; then
    gh issue create --repo "$PLUGIN_REPO" \
        --title "[$ISSUE_MARKER] self-test failed on herdr ${local_ver:-unknown} (release ${tag:-unknown})" \
        --body "$(printf 'Automated compatibility check failed after a herdr change.\n\n- herdr release: %s\n- local herdr: %s\n- checker: `%s`\n\n```\n%s\n```' \
            "${tag:-unknown}" "${local_ver:-unknown}" "$plugin_py" "$output")" >/dev/null \
        && echo "watch: filed issue in $PLUGIN_REPO" >&2
fi

printf '%s\n' "$now" >"$STATE_FILE"
exit 1
