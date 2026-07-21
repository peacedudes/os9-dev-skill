# Bootstrapping a NitrOS-9/XRoar REPL harness

For building your *own* text-driven harness against a 6809 NitrOS-9 system
under XRoar — not this repo's exact tooling specifically. Operating a
harness once it exists: `using-nitros9-repl.md`. Adding screenshot/keystroke
capability on top: `reading-the-coco-screen.md`.

## Why 6809 is harder than 68k here

XRoar is a **real CoCo3 hardware emulator running real ROM firmware** —
unlike os9exec (68k), there's no software-CPU-plus-kernel shortcut; you
need a genuine machine. And XRoar's console is a **video+keyboard GUI**,
not stdio — a plain PTY/pipe harness (the pattern that works directly for
os9exec) has nothing to attach to. A text-channel bridge is mandatory.

## Requirements

1. **XRoar** — install/build separately; not bundled with any OS-9 project.
2. **A CoCo3 ROM image.** Copyright wall, not technical: proprietary
   (Tandy-derived), cannot be redistributed. Must be sourced independently;
   there's no free substitute for a genuine boot.
3. **A NitrOS-9 disk image**, IDE format, bootable to a shell. NitrOS-9
   itself is open source (buildable from `nitros9project/nitros9` on
   GitHub) — but flag the same copyright caution for any *bundled*
   third-party or Microware-derived software the image carries.
4. **A text-channel bridge**, because there's no stdio console to pipe to.
   Two established shapes:
   - **DriveWire over XRoar's built-in becker port** (no extra cart
     needed): `-cart-becker -becker-port <port>`. Requires (a) a DriveWire
     server on that port — any DW3/DW4-compliant implementation, see the
     protocol contract below — and (b) the guest's own boot sequence
     opening a shell on the resulting virtual serial channel (a NitrOS-9
     startup-script line, independent of which server you pair it with).
   - A real serial port / PTY passthrough, if the host and emulator
     support it — not detailed here, not what this project uses.

## Launch invocation shape

```
xroar -rompath <romdir> -machine coco3 -tv-input rgb -machine-cart ide \
  -cart-rom <idecart>.rom -load-hd0 <disk>.ide \
  -cart-becker -becker-port <port> -type 'DOS 0\r\r' \
  [-ui null -ao null | -ui <real-backend>]
```

`-ui null -ao null` = headless, no window, no audio — fine for text-only
REPL work. Give a *real* `-ui` backend for a window (mandatory for any
graphics/screenshot capability). **XRoar takes the last `-ui` flag given**
— useful for overriding a hardcoded default from an outer wrapper rather
than needing to fork it.

## Harness shape

Same gated-send / raw-key-fallback pattern as any OS-9 REPL (see the 68k
sibling doc), but transport is TCP to the DriveWire-exposed channel, not a
PTY to the emulator process.

## Running multiple instances concurrently

XRoar edits the `.ide` disk image **in place** — the guest's own writes land
back in the host file. Two harnesses booting the same image therefore corrupt
each other's disk, and their DriveWire servers fight over one becker port. To
run sessions side by side (`Source`, verified against this repo's
`tools/nitros9repl.sh`; the in-place-mutation reason is inherent to XRoar's IDE
emulation), give each instance three distinct things:

1. **Its own disk clone** — a directory holding a copy of the golden master's
   `<disk>.ide` plus the IDE cart ROM (`hdblba.rom` here); point the harness at
   it (`NITROS9REPL_DISKDIR=<clone>`). A clone is cheap insurance even for a
   read-only-*looking* session — a single stray guest write would otherwise
   mutate the shared boot disk permanently.
2. **A unique session name** (`NITROS9REPL_SESSION=<name>`) so the tmux panes
   don't collide.
3. **Unique ports** — both the becker port (`NITROS9REPL_BECKER_PORT`) and the
   text channel (`NITROS9REPL_CHAN_PORT`); two servers on one port is the
   classic "port already in use" or silent-host→guest-input failure.

Miss any one and the instances interfere in a way that mimics a flaky guest,
not a collision. (The system CoCo3 ROMs live in the absolute `-rompath` and are
read-only, so they need not be cloned — only the writable `.ide` does.)

## DriveWire protocol contract (inherent to the protocol, not this repo)

Get straight if implementing a server from scratch — both bit real
projects before:

- **OP_DWINIT ($5A) must be answered with a non-zero byte.** A zero/absent
  reply makes the NitrOS-9 driver treat the server as legacy DW3 and
  silently disable all DW4 extensions, including the SERREAD poller.
  Symptom: the channel opens and guest→host output flows fine, but
  host→guest input never arrives — no error on either side.
- **A SERWRITEM ($64) addressed to an unopened channel is followed by
  exactly 2 more bytes, with no count byte.** A server that expects a
  count field there desyncs and swallows the guest's next real message.
  A stock EOU-style boot emits roughly 20 of these during startup.

## NitrOS-9/SCF gotchas (inherent to the OS, not this repo)

- OS-9 wants **CR-only** line endings on input, not CRLF/LF.
- **The guest does not echo input** on a virtual serial channel — don't
  assume echo when deciding what was "sent" vs. displayed.
- **Escape ($1B) is SCF's default end-of-file character.** A raw ESC
  arriving as *data* (not intended as EOF) makes whatever's reading the
  channel exit — including the login shell, which nothing auto-respawns.
  Filter Escape out of anything meant to be typed as literal content.
- **Gated send goes silent inside any sub-program with its own prompt**
  (BASIC09 `B:`/`E:`, `debug`'s prompt, `help`'s follow-up `Topic:`) —
  same category as the 68k side, same fix: raw keys, poll for the
  expected prompt.

## Adding screen observation (separate capability layer)

The text-channel harness above cannot see a display at all — it's a
serial-port abstraction. Seeing pixels needs a real windowed `-ui`
(not `-ui null`) plus host-level screenshot + keystroke injection of that
specific window. Two gotchas that generalize past any one platform's API:

- **High-level keystroke-injection APIs can deliver the wrong key.**
  (Measured on macOS: AppleScript `keystroke`/`key code` reach the
  process but arrive as a stray wrong character.) A lower-level synthetic
  HID/event API posted directly to the emulator's process — not routed
  through the window manager's own key-dispatch — may be required
  instead.
- **The emulator's window commonly must be frontmost/focused for
  injected keys to register at all.** An injection into an unfocused
  window can be silently dropped with no error and no visible symptom
  beyond "the screenshot never changes."
