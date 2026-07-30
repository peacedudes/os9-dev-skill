# Seeing the CoCo Screen (6809, XRoar)

A DriveWire text channel drives a NitrOS-9 shell but can never observe a
screen. Verifying graphics work therefore needs a second channel:
host-side screenshots and
keystroke injection against XRoar's own window. Split the roles — drive text
commands over the serial REPL, press keys and capture the screen host-side.
Everything below is `Live` (NitrOS-9) against a running CoCo3, **except the
windint opcode table**, which is `Source` — read out of NitrOS-9's own
`windefs.as`, not exercised opcode by opcode.

## CLEAR is the host backtick

The CoCo `CLEAR` key cycles between the screens of active windows, and is how
you bring a background window's screen to the front. Under XRoar it is the
**host backtick** (macOS virtual keycode 50).

On a stock EOU disk the cycle has 4 screens; `procs` shows shells on Term
(pid 2), W1 (5), W2 (6) and N1 (7) — N1 being the serial REPL, which has no
screen of its own.

**A window with no live process on it never joins the CLEAR cycle.** Only
screens belonging to a running process are reachable this way. It still
*displays*, though, and a lone block on it is not a cursor — don't read "there
is a cursor" as "there is a shell".

## Creating a graphics window

`wcreate /w7 -s=5 0 0 40 24 0 1 1` succeeds — type 5 is a 640×192 2-color,
80-column screen, so a 40-column window occupies its left half (screen-type
table: `gfx-windowing.md`).

- `/w1` is already taken by EOU: error 184 "Window already defined".
- Type 8 with an 80x24 geometry fails with **error 189 "Illegal
  Coordinates"** — type 8 is a 320×192 **40-column** screen, so 80 columns
  does not fit. A geometry error, not the memory or screen-table exhaustion
  it first looks like.
- A shell started on such a window with `shell i=/w7&` **did not survive** —
  it died on its own with the same error 189, leaving the window present but
  with no process on it. Symptom: the screen shows what looks like a prompt
  cursor but typing only clicks and never echoes, because nothing is reading
  the keyboard.

## Getting GFX2 output onto a screen you can see

1. **`SELECT` after `DWSET` is mandatory**, even though nothing about `DWSET`
   suggests it. Without it, a backgrounded procedure's drawing never becomes
   visible on *any* screen — not "hard to find", genuinely never in the CLEAR
   cycle. `SELECT` alone still doesn't display anything; a CLEAR press is
   still needed.
2. **Hold the window open.** A procedure that draws and then exits (or reaches
   `END`) tears its window down before there is anything to look at. Run it
   backgrounded with a `LOOP`/`ENDLOOP`, stdout and stderr redirected to
   `/nil` — a backgrounded job's prompts otherwise interleave with the REPL's
   own channel and wreck it. (OS-9 spells stderr `>>`; `>+`/`>-` are
   append/truncate, and `>>>` silently does nothing despite looking like
   append.)
3. **Clean up between renders.** A stale backgrounded job holds its `/wN`
   open, so the next test's `DWSET` on the same path fails silently into the
   debugger, printing no markers at all. There is no `kill` on the EOU disk
   (`kill <pid>` returns the shell's own `?`, which then sits on the input
   line and corrupts the *next* scripted command), so a full restart is the
   reliable cleanup.
4. **Pick a foreground color that isn't also your background register.**
   `DWSET(path,format,xcor,ycor,width,length,fg,bg,border)`'s `bg` assigns a
   palette register as the window's background. Drawing afterward with `COLOR`
   set to that same register is invisible — not an error, just nothing
   rendered. A general trap, not specific to any one call, and consistent with
   GFX2's total lack of argument validation.
5. **Validate a new call's arity in the foreground first.** `PRINT` markers
   between each `RUN GFX2(...)` call, run un-backgrounded, surface
   parameter-count errors immediately instead of swallowing them into `/nil`.
6. **Find the right screen by looking, not by color threshold.** Cycling until
   a color appears above a pixel-count threshold works for large filled areas,
   but thin line art often has too few matching pixels to clear a threshold
   set safely above incidental occurrences elsewhere (`#A44713`, a 4-color
   window's `COLOR 3`, also appears in Term's boot text at ~1076 px). Screens
   repeat in a short cycle — typically 3-5 distinct ones — so a dozen presses
   is enough to see every one twice.

## windint escape codes — look them up, don't guess

Graphics primitives are `$1B`-prefixed codes written to a window path, easiest
from a shell via `display`. Take the opcodes from `source/lib/alib/windefs.as`
in the NitrOS-9 tree (secondary cross-check only — see the note on NitrOS-9
source provenance). **The table below is `Source`, not `Live`** — the opcodes
were read from that file; only the ones appearing in the worked examples here
have actually been sent to a window.

Guessing costs real time: `$1b22` is `WOWSet` (overlay window set), **not**
SELECT, which is `$1b21`. A SELECT experiment built on the wrong opcode
produces a confident and entirely bogus conclusion.

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

## Host-side observation

Capturing XRoar's window renders through XRoar's own video path, so every GIME
mode, palette and window comes out correct with no host-side video decoding.
Scope the capture to the emulator window rather than the desktop. XRoar's
window ID changes on every restart, so always re-query it; XRoar also
publishes auxiliary windows, and the emulator display is the one named exactly
`XRoar` (~720x572). Capture needs no focus and does not raise the window.
md5-diffing successive captures is a cheap "did anything change?" check, and
the reliable way to prove a keystroke had *no* effect.

Keystroke injection is the opposite: **XRoar must be frontmost or injected
keys are silently dropped** — an unfocused key press leaves the screen
byte-identical, and the same key works immediately once focused. So injection
always steals focus. XRoar maps host keys **by position**, so the US-layout
key at that location is what the CoCo sees. On macOS, high-level AppleScript
key injection does not work: both `key code` and `keystroke` reach the process
but arrive as the *wrong key*. A HID-level `CGEvent` keyDown/keyUp pair posted
directly to the process does work.

**XRoar's `-gdb` target is a dead end**: connecting to port 65520 wedges the
emulator — no RSP reply, no output even at `-debug-gdb -1`, unresponsive to
SIGTERM, port left bound, needs `kill -9`. Confirmed on XRoar 1.11 / macOS
arm64. It would only have exposed the CPU's 64K logical space anyway, not the
GIME's physical video buffer.
