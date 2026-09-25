#!/usr/bin/env python3
"""E2E check for pi-centered.

Runs the real `pi` binary in a pseudo-terminal of a fixed size, emulates the screen
with pyte, and checks where text lands. No model calls: every scenario resumes a
fixed session (fixture.md as the assistant reply) in an isolated agent dir, with
only this extension loaded.

Core invariant per screen: every non-blank row stays inside the centered column,
except the rows of the one wide diagram that is allowed to break out.

Artifacts (overwritten each run): e2e/artifacts/<scenario>/{screen-*.txt,pty.log,
session.jsonl,settings.json} and e2e/artifacts/report.json.
Run via e2e/run.sh (sets up pyte).
"""

from __future__ import annotations

import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import sys
import tempfile
import termios
import time
import uuid

import pyte

HERE = os.path.dirname(os.path.abspath(__file__))
EXTENSION = os.path.join(HERE, "..", "src", "index.ts")
FIXTURE = open(os.path.join(HERE, "fixture.md")).read()
ARTIFACTS = os.path.join(HERE, "artifacts")
PAD_X = 1  # Pi's default outputPad: assistant text starts one cell inside the column
WIDE_DIAGRAM = "Request received"


# ---------------------------------------------------------------- pi driver


class Pi:
    def __init__(self, out_dir: str, agent_dir: str, session: str, cols: int, rows: int, env: dict):
        self.out_dir, self.cols, self.rows = out_dir, cols, rows
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.log = open(os.path.join(out_dir, "pty.log"), "wb")
        child_env = {k: v for k, v in os.environ.items() if k != "PI_CENTERED_WIDTH" and not k.startswith("HERDR")}
        child_env.update({"PI_CODING_AGENT_DIR": agent_dir, "TERM": "xterm-256color", **env})
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
            os.chdir(os.path.dirname(session))
            args = ["pi", "-ne", "-e", EXTENSION, "-ns", "-np", "--offline", "--session", session]
            os.execvpe("pi", args, child_env)
        # Answer terminal queries (device attributes, cursor position) like a real terminal.
        self.screen.write_process_input = lambda data: os.write(self.fd, data.encode())

    def pump(self, seconds: float):
        end = time.time() + seconds
        while (left := end - time.time()) > 0:
            ready, _, _ = select.select([self.fd], [], [], left)
            if not ready:
                continue
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                return
            if not data:
                return
            self.log.write(data)
            self.stream.feed(data)

    def wait_for(self, predicate, timeout: float = 30) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.25)
            if predicate(self.lines()):
                self.pump(0.75)  # let the frame settle
                return True
        return False

    def lines(self) -> list[str]:
        return list(self.screen.display)

    def send(self, text: str):
        for ch in text:  # type like a person so the editor/autocomplete see each key
            os.write(self.fd, ch.encode())
            self.pump(0.02)

    def save(self, name: str):
        with open(os.path.join(self.out_dir, f"screen-{name}.txt"), "w") as f:
            f.write("\n".join(line.rstrip() for line in self.lines()) + "\n")

    def close(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
            self.pump(0.5)
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        self.log.close()


# ---------------------------------------------------------------- setup


def make_agent_dir(root: str, tui_mode: str, mermaid: str) -> str:
    agent = os.path.join(root, "agent")
    os.makedirs(agent, exist_ok=True)
    settings = {"tuiMode": tui_mode, "quietStartup": True, "markdown": {"mermaid": mermaid}}
    with open(os.path.join(agent, "settings.json"), "w") as f:
        json.dump(settings, f, indent=2)
    return agent


def make_session(root: str) -> str:
    work = os.path.join(root, "work")
    os.makedirs(work, exist_ok=True)
    now_ms = int(time.time() * 1000)
    iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    usage = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 0,
             "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}}
    entries = [
        {"type": "session", "version": 3, "id": str(uuid.uuid4()), "timestamp": iso, "cwd": work},
        {"type": "message", "id": "a0000001", "parentId": None, "timestamp": iso,
         "message": {"role": "user", "content": "Explain the delivery pipeline.", "timestamp": now_ms}},
        {"type": "message", "id": "a0000002", "parentId": "a0000001", "timestamp": iso,
         "message": {"role": "assistant", "content": [{"type": "text", "text": FIXTURE}],
                     "api": "anthropic-messages", "provider": "anthropic", "model": "claude-sonnet-4-5",
                     "usage": usage, "stopReason": "stop", "timestamp": now_ms}},
    ]
    path = os.path.join(work, "session.jsonl")
    with open(path, "w") as f:
        f.write("".join(json.dumps(e) + "\n" for e in entries))
    return path


# ---------------------------------------------------------------- checks


def column_of(cols: int, max_width: int) -> tuple[int, int]:
    """[left, right) cells of the centered column, as the extension computes it."""
    if not max_width or cols <= max_width:
        return 0, cols
    left = (cols - max_width) // 2
    return left, left + max_width


def escaping_rows(lines: list[str], cols: int, max_width: int) -> list[tuple[int, int, int, str]]:
    left, right = column_of(cols, max_width)
    out = []
    for i, line in enumerate(lines):
        body = line[: cols - 1].rstrip()  # last column may hold the fullscreen scrollbar
        if not body.strip():
            continue
        first = len(body) - len(body.lstrip())
        last = len(body) - 1
        if first < left or last >= right:
            out.append((i, first, last, body.strip()[:60]))
    return out


def start_col(lines: list[str], needle: str) -> int | None:
    for line in lines:
        if needle in line:
            return len(line) - len(line.lstrip())
    return None


def check_layout(lines, cols, max_width, *, expect_breakout: bool, diagrams_on: bool = True) -> list[str]:
    """Return failure messages (empty = pass)."""
    errors = []
    text = "\n".join(lines)
    left, _ = column_of(cols, max_width)
    for marker in ("ALPHA paragraph", "BRAVO paragraph", "CHARLIE paragraph"):
        col = start_col(lines, marker)
        if col is None:
            errors.append(f"{marker!r} not on screen")
        elif col != left + PAD_X:
            errors.append(f"{marker!r} starts at col {col}, expected {left + PAD_X}")
    if diagrams_on and "│ SmallStart" not in text:
        errors.append("narrow diagram not rendered as box art")
    if not diagrams_on and "│ SmallStart" in text:
        errors.append("narrow diagram rendered although Pi's mermaid mode is off")
    for nested in ("Nested one", "Example one"):
        if f"│ {nested}" in text:
            errors.append(f"nested/example diagram {nested!r} was rendered; Pi leaves it as source")
        if f"[{nested}]" not in text:
            errors.append(f"source of {nested!r} missing")

    escapes = escaping_rows(lines, cols, max_width)
    wide_rows = [i for i, line in enumerate(lines) if f"│ {WIDE_DIAGRAM}" in line]
    if expect_breakout:
        if not wide_rows:
            errors.append("wide diagram not rendered as box art")
        else:
            box = {wide_rows[0] - 1, wide_rows[0], wide_rows[0] + 1}  # ┌ │ └
            stray = [e for e in escapes if e[0] not in box]
            if stray:
                errors.append(f"rows outside the column (not the wide diagram): {stray}")
            if len(escapes) != 3:
                errors.append(f"expected exactly 3 breakout rows, got {len(escapes)}: {escapes}")
            dia_col = start_col(lines, f"│ {WIDE_DIAGRAM}")
            diagram_width = max(e[2] - e[1] + 1 for e in escapes) if escapes else 0
            expected = min(left, cols - (diagram_width + 2 * PAD_X)) + PAD_X
            if dia_col != expected:
                errors.append(f"wide diagram starts at col {dia_col}, expected {expected}")
    else:
        if f"│ {WIDE_DIAGRAM}" in text:
            errors.append("wide diagram rendered although breakout should not happen here")
        if escapes:
            errors.append(f"rows outside the column: {escapes}")
    return errors


# ---------------------------------------------------------------- scenarios


def ready(lines):
    return any("CHARLIE paragraph" in line for line in lines)


def at_width(cols, max_width):
    left, _ = column_of(cols, max_width)
    return lambda lines: start_col(lines, "ALPHA paragraph") == left + PAD_X


def scenario(name, *, cols=260, rows=110, tui="fullscreen", mermaid="streaming", env=None, root=None):
    out = os.path.join(ARTIFACTS, name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    root = root or tempfile.mkdtemp(prefix=f"mw-{name}-")
    agent = make_agent_dir(root, tui, mermaid)
    session = make_session(root)
    shutil.copy(session, os.path.join(out, "session.jsonl"))
    shutil.copy(os.path.join(agent, "settings.json"), os.path.join(out, "settings.json"))
    return Pi(out, agent, session, cols, rows, env or {}), root, agent


def run_layout(name, *, max_width, expect_breakout, **kw):
    diagrams_on = kw.get("mermaid", "streaming") != "off"
    pi, _, _ = scenario(name, env={"PI_CENTERED_WIDTH": str(max_width)}, **kw)
    try:
        if not pi.wait_for(ready):
            pi.save("timeout")
            return ["pi never showed the fixture"]
        pi.save("final")
        return check_layout(pi.lines(), pi.cols, max_width, expect_breakout=expect_breakout, diagrams_on=diagrams_on)
    finally:
        pi.close()


def run_live_change_and_reload():
    errors = []
    pi, root, agent = scenario("live-70-then-reload")
    config = os.path.join(agent, "pi-centered.json")
    try:
        if not pi.wait_for(ready):
            pi.save("timeout")
            return ["pi never showed the fixture"], root
        pi.save("1-default-110")
        errors += [f"default: {e}" for e in check_layout(pi.lines(), pi.cols, 110, expect_breakout=True)]

        pi.send("/maxwidth 70\r")
        if not pi.wait_for(at_width(pi.cols, 70), timeout=10):
            errors.append("/maxwidth 70 did not move the column")
        pi.save("2-after-maxwidth-70")
        errors += [f"after /maxwidth 70: {e}" for e in check_layout(pi.lines(), pi.cols, 70, expect_breakout=True)]
        try:
            saved = json.load(open(config)).get("maxWidth")
        except Exception as exc:  # noqa: BLE001
            saved = f"unreadable ({exc})"
        if saved != 70:
            errors.append(f"pi-centered.json holds {saved!r}, expected 70")

        pi.send("/reload\r")
        pi.pump(4)
        pi.wait_for(ready, timeout=20)
        pi.save("3-after-reload")
        errors += [f"after /reload: {e}" for e in check_layout(pi.lines(), pi.cols, 70, expect_breakout=True)]
    finally:
        pi.close()
    return errors, root


def run_restart_uses_saved(root):
    """Same agent dir (saved 70), bad env var: expect a warning and the saved width."""
    out = os.path.join(ARTIFACTS, "restart-saved-bad-env")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    agent = os.path.join(root, "agent")
    session = make_session(root)
    pi = Pi(out, agent, session, 260, 110, {"PI_CENTERED_WIDTH": "abc"})
    try:
        if not pi.wait_for(ready):
            pi.save("timeout")
            return ["pi never showed the fixture"]
        pi.wait_for(lambda lines: any("ignored" in line for line in lines), timeout=5)
        pi.save("final")
        errors = check_layout(pi.lines(), pi.cols, 70, expect_breakout=True)
        if not any('PI_CENTERED_WIDTH="abc" ignored' in line for line in pi.lines()):
            errors.append("no warning about the invalid PI_CENTERED_WIDTH")
        return errors
    finally:
        pi.close()


def main() -> int:
    if not shutil.which("pi"):
        print("pi not found on PATH", file=sys.stderr)
        return 2
    os.makedirs(ARTIFACTS, exist_ok=True)
    results: dict[str, list[str]] = {}

    results["fullscreen-100"] = run_layout("fullscreen-100", max_width=100, expect_breakout=True)
    results["regular-100"] = run_layout("regular-100", max_width=100, expect_breakout=True, tui="regular")
    results["mermaid-off-100"] = run_layout("mermaid-off-100", max_width=100, expect_breakout=False, mermaid="off")
    results["narrow-terminal-90"] = run_layout("narrow-terminal-90", max_width=100, expect_breakout=False, cols=90)
    errors, root = run_live_change_and_reload()
    results["live-70-then-reload"] = errors
    results["restart-saved-bad-env"] = run_restart_uses_saved(root)

    with open(os.path.join(ARTIFACTS, "report.json"), "w") as f:
        json.dump({"pi": shutil.which("pi"), "results": results}, f, indent=2)
    failed = 0
    for name, errs in results.items():
        print(f"{'PASS' if not errs else 'FAIL'}  {name}")
        for e in errs:
            print(f"      - {e}")
        failed += bool(errs)
    print(f"\nArtifacts: {ARTIFACTS}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
