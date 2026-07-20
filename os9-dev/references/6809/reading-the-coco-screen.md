# Seeing the CoCo Screen (6809, XRoar)

`nitros9repl.sh` is a *text* channel — it drives a NitrOS-9 shell over a
DriveWire virtual serial port and can never observe a screen. That is why
`gfx-windowing.md` is almost entirely `Manual`: nothing there had ever been
looked at. This file covers the companion tool, `tools/cocoscreen.sh` in the
os9exec repo, which supplies the missing eye, and the traps found while
building it.

Split of responsibilities: **drive text commands over the `/N1` REPL, press
keys and take screenshots with `cocoscreen.sh`.** All confidence tags below
are `Live` — every claim here was measured against a running CoCo3, and
several of them contradict a reasonable-sounding first guess.

## Prerequisite: XRoar needs a window

The REPL is headless by default. Graphics work needs:

```
NITROS9REPL_GUI=1 ./tools/nitros9repl.sh start
```

As of 2026-07-19, `start`/`restart` **automatically** parks the window at
0,0 and hands focus straight back to whatever app was frontmost before
launching XRoar — both happen inside `cmd_start` in `nitros9repl.sh` itself,
with a short retry loop since the window doesn't exist the instant the tmux
pane is created. Don't call `./tools/cocoscreen.sh place 0 0` by hand
anymore; it's redundant. (`Live`)

## The practical GFX2-window recipe (BASIC09)

This is the sequence that actually gets a `RUN GFX2(...)` call's output onto
a screen you can photograph, distilled from getting it wrong first. The full
worked recipe with copy-pasteable commands is at the top of
`test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md` in the
os9exec repo — follow that rather than re-deriving it. The rules below are
*why* each step in it exists.

1. **`SELECT` after `DWSET` is mandatory**, even though nothing about `DWSET`
   suggests it. Without it, a backgrounded procedure's drawing never becomes
   visible on *any* screen — not "hard to find," genuinely never appears in
   the CLEAR cycle. `SELECT` alone still doesn't display anything; see (4).
2. **Hold the window open with `--bg` + `LOOP`/`ENDLOOP`.** A procedure that
   draws and then exits (or reaches `END`) tears its window down before
   there's any chance to screenshot it. `tools/b09run.sh <name> --bg` runs
   the procedure backgrounded with stdout/stderr redirected to `/nil` (a
   backgrounded job's prompts otherwise interleave with the REPL's own
   channel and wreck it — OS-9 spells stderr `>>`, and `>+`/`>-` are append/
   truncate, not `>>>` which silently does nothing despite looking like
   append).
3. **Restart the REPL between background renders.** There is no `kill` on
   this disk (`kill <pid>` returns the shell's own `?`, which then sits on
   the input line and corrupts the *next* scripted command). A stale
   backgrounded job holds its `/wN` open, so the next test's `DWSET` on the
   same path fails silently into the debugger, printing no markers at all.
   `NITROS9REPL_GUI=1 NITROS9REPL_EXTRA_XROAR="-no-ratelimit"
   ./tools/nitros9repl.sh restart` between every render is the reliable
   cleanup — cheap at full speed (`-no-ratelimit`).
4. **Finding the right screen: `cocoscreen.sh cycle N` and look, don't
   guess by color threshold.** `find <RRGGBB> <minpx>` (CLEAR until a color
   appears above a pixel-count threshold) works well for large filled
   areas, but thin line art (a `DRAW` polyline, an unfilled `BOX`) often
   has too few matching pixels to clear a threshold set safely above
   incidental occurrences of the same color elsewhere (`#A44713`, a
   4-color window's `COLOR 3`, also appears in Term's boot text at
   ~1076 px). When in doubt, `cycle 10` or `12` and read the distinct
   frames yourself — screens repeat in a short cycle (typically 3-5
   distinct ones: `/w1`, `/w2`, `Term`, and the graphics window if it's
   reachable at all), so a dozen presses is enough to see every one twice.
5. **Pick a foreground color that isn't also your background register.**
   `DWSET(path,format,xcor,ycor,width,length,fg,bg,border)`'s `bg`
   parameter assigns a palette register as the window's own background.
   Drawing afterward with `COLOR` set to that *same* register number is
   invisible — not an error, just nothing rendered, because foreground now
   equals background. This bit a `PATTERN` test that used `COLOR 1` when
   `DWSET`'s `bg` argument was also `1`; switching to an unused register
   (`COLOR 3`) fixed it instantly. This is a general trap, not unique to
   `PATTERN` — it silently defeats *any* drawing call, and there's no error
   to point at it (consistent with GFX2's general lack of argument
   validation).
6. **A `wcreate`d window with no live process on it never joins the CLEAR
   cycle.** Only screens belonging to a running process are reachable this
   way. This is also why Level-1 `GFX` (which has no `path` argument at
   all, and so always draws to whatever the calling process's own default
   output happens to be) couldn't be visually verified as of 2026-07-19 —
   see `gfx-windowing.md`'s `MODE` entry.
7. **Validate a new call's arity in the foreground first.** `PRINT` markers
   between each `RUN GFX2(...)` call, run un-backgrounded, need no CLEAR
   presses (so no focus stealing) and surface parameter-count errors
   immediately instead of silently swallowing them into `/nil`. Only
   background a call once its arity is confirmed accepted.

**One more trap, specific to `b09run.sh`'s script-writing step:** `build` is
driven by raw keystrokes with nothing to confirm they landed. If the channel
was busy mid-send, the script file ends up empty, and BASIC09 then "runs" a
no-op and prints a perfectly healthy-looking banner — indistinguishable from
a passing test that drew nothing. `b09run.sh` now verifies the script was
actually written (`list <script>` and grep for the `run` line) before
invoking it and refuses to proceed otherwise; if driving the editor by hand
outside that tool, do the same check.

## Reading the screen

`./tools/cocoscreen.sh shot [file]` captures via
`screencapture -x -o -l <CGWindowID>`.

- Scoped to XRoar's window only — never the desktop, so nothing else on
  screen is exposed. (`Live`)
- Renders through XRoar's own video path, so every GIME mode, palette and
  window is correct with **no video decoding on the host side**. (`Live`)
- Needs no focus and does not raise the window. (`Live`)
- **XRoar's window ID changes on every restart** — always re-query. XRoar also
  publishes auxiliary windows; the emulator display is the one whose
  `kCGWindowName` is exactly `XRoar` (~720x572). (`Live`)
- md5-diffing successive captures is a cheap "did anything change?" check, and
  is the reliable way to prove a keystroke had *no* effect. (`Live`)

## Pressing keys

`./tools/cocoscreen.sh key <name>...` / `type <string>` / `clear`.

- **AppleScript System Events does not work.** Both `key code` and `keystroke`
  reach the process but arrive as the *wrong key* — every attempt landed as a
  stray `p` in the guest. Do not use it for key injection. (`Live`)
- A HID-level `CGEvent` keyDown/keyUp pair posted with `postToPid` **does**
  work. (`Live`)
- **XRoar must be FRONTMOST or injected keys are silently dropped.** Measured:
  an unfocused `clear` left the screen byte-identical; the same key worked
  immediately once focused. Key injection therefore always steals focus —
  don't run it while a human is typing elsewhere. (`Live`)
- XRoar maps host keys **by position**, so the US-layout key at that location
  is what the CoCo sees.
- Verified end-to-end: `type "dir"` then `key enter` put `dir` on the Term
  prompt, ran it, and the screenshot showed the directory listing. (`Live`)

**Shell-quoting trap that mimics a hardware fault:** the focus step is an
`osascript -e '...'`. A `\` line-continuation *inside single quotes* is passed
to AppleScript literally and is a syntax error there — it is not a shell
continuation. Written that way (and with errors swallowed) focus silently
never happens and **every keystroke is dropped**, which looks exactly like
flaky emulator input. Keep the `osascript -e '...'` on one line, and let it
fail loudly. Symptom to check first when keys stop landing:
`osascript -e 'tell application "System Events" to name of first process whose frontmost is true'`
— if that is not XRoar, the fault is host-side, not in the guest.

## CLEAR is the host backtick

The CoCo `CLEAR` key cycles between the screens of active windows, and is how
you bring a background window's screen to the front. Under XRoar it is the
**host backtick** (macOS virtual keycode 50). (`Live`)

On the stock EOU test disk the cycle has 4 screens; `procs` shows shells on
Term (pid 2), W1 (5), W2 (6) and N1 (7) — N1 being the serial REPL, which has
no screen of its own. (`Live`)

## windint escape codes — look them up, don't guess

Graphics primitives are `$1B`-prefixed codes written to a window path, easiest
from a shell via `display`. **Get the opcodes from
`source/lib/alib/windefs.as` in the NitrOS-9 tree** (secondary cross-check
only — see the sibling note on NitrOS-9 source provenance).

Guessing here cost real time: `$1b22` is `WOWSet` (overlay window set), *not*
SELECT, which is `$1b21`. A "SELECT" experiment built on that wrong opcode
produced a confident but entirely bogus conclusion about SELECT's behavior.

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `$1b21` | `WSelect` | `$1b40` | `WSetDPtr` set draw pointer |
| `$1b20` | `WDWSet` device window set | `$1b42` | `WPoint` |
| `$1b22` | `WOWSet` overlay window set | `$1b44` | `WLine` |
| `$1b32` | `WFColor` foreground color | `$1b48` | `WBox` |
| `$1b33` | `WBColor` background color | `$1b4a` | `WBar` (filled) |
| `$1b31` | `WPalette` | `$1b50` | `WCircle` |
| `$1b39` | `WGCSet` graphics cursor | `$1b51` | `WEllipse` |

Coordinates are **16-bit big-endian pairs**. Example — box then ellipse on an
already-created graphics window:

```
display 1b 32 02 1b 40 00 20 00 20 1b 48 00 c0 00 a0 >/w7
display 1b 40 00 70 00 60 1b 51 00 50 00 30 >/w7
```

## Creating a graphics window

`wcreate /w7 -s=5 0 0 40 24 0 1 1` — type 5 is 320x192 4-color — succeeds.
(`Live`)

- `/w1` is already taken by EOU: error 184 "Window already defined". (`Live`)
- Type 8 (640x192) with an 80x24 geometry fails with **error 189 "Illegal
  Coordinates"** — a geometry error, not the memory or screen-table
  exhaustion it first looks like. (`Live`)
- A shell started on such a window with `shell i=/w7&` **did not survive** —
  it died on its own with the same error 189, leaving the window present but
  with no process on it. Symptom to recognize: the screen shows what looks
  like a prompt cursor but typing only clicks and never echoes, because
  nothing is reading the keyboard. Getting a shell to persist on a graphics
  window is unfinished work. (`Live`)

## Gotchas that cost time

- A window with no live process still *displays*; a lone block on it is not
  a cursor. Do not read "there is a cursor" as "there is a shell". (`Live`)
- If `nitros9repl.sh send` starts replaying stale output, its `nc` client has
  died and commands are going nowhere — check
  `tmux capture-pane -t nitros9repl:chan` directly and restart the REPL.
  Silent no-ops here are easy to misread as the *guest* failing. (`Live`)
- XRoar's `-gdb` target is a **dead end**: connecting to port 65520 wedges the
  emulator (no RSP reply, no output even at `-debug-gdb -1`, unresponsive to
  SIGTERM, port left bound — needs `kill -9`). Confirmed on XRoar 1.11 /
  macOS arm64. It would only have exposed the CPU's 64K logical space anyway,
  not the GIME's physical video buffer. (`Live`)
