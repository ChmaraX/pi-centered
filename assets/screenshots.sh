#!/usr/bin/env bash
# Regenerates assets/screenshot.png and assets/wide-diagram.png with VHS.
# Needs: vhs, pi on PATH. Replays fixed replies (no model calls) with only
# pi-centered loaded, in a throwaway agent dir that borrows your theme and login.
set -euo pipefail
cd "$(dirname "$0")/.."
export REPO="$PWD" DEMO="$(mktemp -d)" PI_CENTERED_WIDTH="${PI_CENTERED_WIDTH:-100}"
trap 'rm -rf "$DEMO"' EXIT
REAL="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
export PI_CODING_AGENT_DIR="$DEMO/agent"
mkdir -p "$PI_CODING_AGENT_DIR" "$DEMO/acme-api"
[ -e "$REAL/auth.json" ] && ln -s "$REAL/auth.json" "$PI_CODING_AGENT_DIR/auth.json"
[ -d "$REAL/themes" ] && ln -s "$REAL/themes" "$PI_CODING_AGENT_DIR/themes"
python3 - "$REAL/settings.json" "$PI_CODING_AGENT_DIR/settings.json" <<'PY'
import json, sys
try: real = json.load(open(sys.argv[1]))
except Exception: real = {}
keep = {k: real[k] for k in ("theme", "defaultProvider", "defaultModel", "defaultThinkingLevel") if k in real}
json.dump({**keep, "tuiMode": "fullscreen", "quietStartup": True,
           "warnings": {"anthropicExtraUsage": False}}, open(sys.argv[2], "w"), indent=2)
PY
python3 assets/make-session.py "Why didn't the password reset email arrive for this subscriber?" assets/demo-text.md "$DEMO/acme-api/text.jsonl"
python3 assets/make-session.py "Draw the delivery pipeline." assets/demo-diagram.md "$DEMO/acme-api/diagram.jsonl"

# One tape per screenshot: VHS only saves the first Screenshot of a tape.
shot() { # <session> <regex that means "fully rendered"> <output png>
  cat > "$DEMO/shot.tape" <<TAPE
Output "$DEMO/shot.gif"
Source "assets/frame.tape"
Hide
Type "cd $DEMO/acme-api && HOME=$DEMO pi --offline -ne -ns -np -e $REPO/src/index.ts --session $1"
Enter
Wait+Screen@30s /$2/
Sleep 2s
Show
Sleep 1s
Screenshot "$3"
Sleep 500ms
TAPE
  vhs "$DEMO/shot.tape" >/dev/null
  echo "wrote $3"
}
shot text.jsonl "Three things" assets/screenshot.png
shot diagram.jsonl "Record delivery" assets/wide-diagram.png
