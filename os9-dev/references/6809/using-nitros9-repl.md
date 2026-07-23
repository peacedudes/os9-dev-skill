# Driving a live NitrOS-9 (6809) system: the nitros9repl.sh harness

**Status: `Live`.** The 6809 target has a real,
scriptable test harness — the same class of tool as `os9exec`'s
`tools/os9repl.sh` on 68k. 6809 claims can and should be verified against
it rather than marked UNVERIFIED.

**Seeing the screen:** this harness is text-only and cannot observe a display.
For screenshots, keystroke injection, and graphics work, see the companion
`6809/reading-the-coco-screen.md` (`tools/cocoscreen.sh`) — it needs the
emulator started with a window: `NITROS9REPL_GUI=1 ./tools/nitros9repl.sh start`.

## What it is

`tools/nitros9repl.sh` (in the os9exec repo) boots a NitrOS-9 EOU system
on an emulated CoCo3 (XRoar) and gives a prompt-gated `send` interface to
a real shell, plus `connect` for a human. The transport is DriveWire:
XRoar's "becker port" tunnels the DriveWire protocol over TCP to a server
(`drivewire-cli` from drpitre/drivewire, branch `virtual-serial`), whose
virtual serial channel `/N1` carries the shell; the server re-exposes the
channel as a local TCP port.

```sh
./tools/nitros9repl.sh start        # unattended boot to a {N1|NN}path: prompt (~40 s)
./tools/nitros9repl.sh send mdir    # one command, prompt-gated, new output only
./tools/nitros9repl.sh snap / peek  # inspect the channel pane
./tools/nitros9repl.sh server      # inspect the DriveWire protocol log (hex dumps)
./tools/nitros9repl.sh stop        # kills server + XRoar, in the *normal* headless case
```

Prerequisites and paths are documented in the script header. If `start`
times out: XRoar occasionally boots into a stuck state ("bad data read" +
frozen, ~100% CPU) — a plain `restart` clears it; don't debug the first
occurrence.

## Getting a real, visible screen — two separate shells exist on one boot

The `{N1|NN}` prompt `send`/`key` drive is a **virtual DriveWire serial
channel**, not the emulated machine's actual video display — there is a
**second, independent shell running on the real local console** the whole
time (`Term!NN`, visible only if XRoar has a real window). `Live`:
`NITROS9REPL_EXTRA_XROAR="-ui macosx" ./tools/nitros9repl.sh start`
overrides the hardcoded `-ui null` (XRoar takes the last `-ui` flag, so
this works despite `-ui null` still appearing earlier in the invocation)
and opens a real window — useful for actually seeing graphics render, not
just decoding text-mode screen memory. Once open, host `screencapture
-R<x,y,w,h>` (get bounds via `osascript -e 'tell application "System
Events" to tell process "xroar" to get {position, size} of window 1'`)
captures a real image. **Commands sent via `send`/`key` never reach this
console** — to type into the actual visible shell, send real keystrokes
to the XRoar app itself (`osascript -e 'tell application "XRoar" to
activate'` then `tell application "System Events" to keystroke "..." &
return`).

**Two real gotchas with this mode, `Live`:**
- **Remember `-no-ratelimit` too if you add `-ui macosx`** — they're
  independent flags. Adding only `-ui macosx` leaves the CPU throttled at
  real 6809 speed with no visible indication why things feel slow;
  combine both in `NITROS9REPL_EXTRA_XROAR` if the test doesn't care
  about real-time pacing (most don't — see the full-speed policy in the
  Benchmarking gotcha below).
- **`stop` does not reliably kill XRoar when it was started this way** —
  confirmed live: after `stop`, the XRoar GUI process was still running
  (`ps aux | grep xroar` showed it alive) with its window still open.
  `stop` tears down the script's own tmux/nc control layer, which isn't
  guaranteed to cascade to a process started with an overridden `-ui`.
  Check `ps aux | grep -i xroar` after `stop` if you used this mode, and
  `kill` the PID directly if it's still there — don't assume the window
  is gone.

## Loading a BASIC09 program from a host-authored file (`Live`, end-to-end)

The 6809 disk image is a real IDE image, not an `os9exec` host-native
directory, so the 68k REPL's trick of editing a file on the host and
`flip -m`-ing it straight into place (see `common/using-os9exec-repl.md`)
doesn't apply — there is no host-side file to touch. The equivalent that
works here is an OS-9-native heredoc, driven entirely through the REPL:

**Not the only way in — for a short program, driving BASIC09's own
interactive editor directly is often less work than the heredoc below.**
`Live`: `key "e <name>" Enter` drops into the `E:` prompt exactly as
`common/using-os9exec-repl.md` documents generically for the 68k REPL
(`B:e test → edit mode, * / E: prompt`, leading space means insert,
`q` returns to `B:`) — the same editor, same behavior, on 6809. Use
`key` (not `send`, see the prompt-gate gotcha below) for every line once
inside. This avoids `tee`/`LOAD`'s comment-placement footgun entirely
since there's no raw source file to comment-lead. Reach for the heredoc
route below instead when the program is long enough that per-line `key`
calls become the bottleneck, or when you already have host-side source
text to paste in bulk.

```
tools/nitros9repl.sh key "tee >progname" Enter
tools/nitros9repl.sh key "PROCEDURE progname" Enter
tools/nitros9repl.sh key " DIM x: INTEGER" Enter
tools/nitros9repl.sh key " x = 42" Enter
tools/nitros9repl.sh key " PRINT x" Enter
tools/nitros9repl.sh key Escape        # EOF for tee, not a shell-exit here — see below
```

`Escape` here terminates `tee`'s *own* read (consumed by `tee`, one
level down from the shell's own prompt read), not the `/N1` shell
itself — `Live`: the shell prompt reappears normally afterward,
no `restart` needed. This is a one-shot EOF consumed by whichever
process is reading `/n1` at that moment, the same as the "Escape is
SCF's EOF character" gotcha below, just landing on `tee` instead of the
shell. Then, inside `basic09`: `LOAD progname` compiles the text
directly, same as the 68k `LOAD` recipe.

**Critical gotcha, `Live`: don't lead the file with a
comment.** A comment (`!`) as the literal first line of the file, before
`PROCEDURE`, makes `LOAD` fail the *entire file* with `Error #043 --
Unknown Procedure` on 6809 — silently fine on 68k, but fatal here. See
`basic09/gotchas.md` for the full writeup (it isn't scoped to just the
first procedure; nothing in the file loads). Put `PROCEDURE` on line 1;
move any file-level comment after it if you want one at all.

## Running a multi-process test on this disk (all `Live`, 2026-07-20)

- **★ A `What?` flood is BASIC09's DEBUGGER spinning on EOF, not the shell and
  not lost data.** `Live`, reproduced on demand and traced 2026-07-21. When a
  BASIC09 program launched as `basic09 <script` hits an **uncaught runtime
  error**, it `BREAK`s into the interactive debugger (the `D:` prompt — that is
  what prints `What?`, on any command it doesn't recognise). Because the
  program's stdin is the redirected script file, now at EOF, the debugger reads
  past EOF endlessly and emits `What?` on every empty read: an unbounded
  `D:What?` flood that hangs the job and leaves its output file unwritten —
  reading exactly like the filesystem dropping every write. Proven minimally: an
  `x=1/0` program run with stdin = terminal drops to `D:` and **blocks** (one
  prompt, responds to `q`); the same program run with `<file` **floods**. In a
  multi-process roster the specific trigger was `Error #237 (RAM Full)` at
  `SHELL "sleep"` inside a nap procedure — several `#32k` BASIC09 workers plus
  the `#32k` shell running the procedure file, all forking `SHELL` at once, ran
  the CoCo3 out of memory. **Takeaways:** (a) `What?` means "look for an
  uncaught error that dropped a program into `D:`", not channel trouble; (b)
  give any BASIC09 program you drive non-interactively an `ON ERROR` so a fault
  reports instead of spinning; (c) watch total memory when backgrounding several
  `#32k` jobs that each `SHELL`-fork — stagger the launches or shrink the
  footprint. Earlier versions of this bullet blamed "channel corruption from
  rapid `key`" and "a backgrounded child inheriting the parent's stdin"; both
  were tested and are false — do not reintroduce them.
- **`SHELL` DOES exist in 6809 BASIC09 and really forks.** `Live`:
  `SHELL "echo MARKER"` printed its output from inside a `RUN` procedure.
  Some 68k-era documentation implies it is 68k-only; it is not. It costs a
  process fork per call, which on a 2MHz 6809 is expensive — roughly a quarter
  of a call per second in a tight loop. A burst of writes to `/nil` is far
  cheaper but does NOT yield long enough to let another process interleave, so
  it is not a substitute when the point is to open a scheduling window.
- **Editing the disk host-side: ToolShed cannot read the `.ide` container.**
  The OS-9 partition starts at byte **323,584** inside `68IDE.ide` (verified:
  an RBF LSN0 with volume name "NitrOS-9 EOU 6809"). `dd` the partition out,
  run `os9 copy` against the raw partition, `dd` it back with `conv=notrunc` —
  about 1.8s round trip for 128MB. XRoar must be stopped throughout.
- **Clone the image per run rather than mutating the shared one.** On APFS
  `cp -c` clones the 134MB image in ~5ms with no disk cost. A clone directory
  needs `68IDE.ide` and `hdblba.rom` (XRoar loads the cart ROM relative to its
  own cwd); `-rompath` is absolute. `NITROS9REPL_DISKDIR` points the harness at
  it. **Verify with `lsof` which image XRoar actually has open** — `stop` does
  not reliably kill XRoar, and a survivor gets reused by the next `start`,
  silently writing to whatever disk *it* was booted on.
- **`-no-ratelimit` boots this disk in about 4 seconds**, not the ~40 the
  throttled default takes. A whole multi-process scenario can run in 7-11s.
- **`tmux clear-history -t <session>:chan` before a command** makes `send`
  output readable; `peek` dumps the entire scrollback and is useless for
  polling for a completion marker.

## Gotchas an agent must know (all `Live`)

- **`send`'s prompt-gate doesn't recognize a sub-program's own prompt**
  (the same class of issue documented for the 68k `os9repl.sh` inside
  BASIC09). `Live`, with three different sub-programs: `debug
  <modulename>` drops into the Interactive Debugger's `DB:` prompt,
  `help <topic>` drops into a `Topic:` follow-up prompt after printing its
  text, and BASIC09's own `e <name>` editor drops into its `E:` prompt —
  `send` will sit at `[TIMEOUT]` in all three cases even though the
  command actually worked and its output is sitting right there in the
  timeout dump. This is a general pattern, not a fixed list: any
  sub-program with its own read loop will do this. Switch to `key` for
  further interaction once inside any of them, and a bare `key Enter` is
  enough to exit `help`'s `Topic:` prompt back to the shell.
- **Escape ($1B) is SCF's default end-of-file character.** A program
  reading `/n1` that receives one reads EOF; the `/n1` shell exits
  normally on it. Nothing respawns that shell (startup launches it once),
  so recovery is a full `restart`. `connect` filters Esc/arrow keys for
  this reason; a deliberate EOF is `key Escape`.
- **OS-9 wants CR line endings on input** — the harness handles this
  (tmux Enter → bare CR). If bypassing the script with your own `nc`,
  send `\r`, not `\n`.
- **The guest does not echo input on `/N1`**, and prompts have no trailing
  newline — any pipeline that displays channel output must be unbuffered
  (the script uses a perl `sysread` loop; `tr` line-buffers and holds the
  prompt back).
- **One client per channel**: connecting displaces the previous client
  (the guest shell is unaffected; backlogged output replays to the new
  client). The script's `send`/`key` auto-recreate their bridge pane.
- **Guest time is already correct at boot** — the disk's `clock2_dw`
  fetches time from the DriveWire server (OP_TIME). Do not run `setime`
  (it errors, and isn't needed) — this supersedes the older
  "set date first" rule for these sessions.
- **The EOU Shell+ prompt is `{N1|NN}path:`** (e.g. `{N1|07}/DD:`), where
  NN is the shell's process number.
- **`start` boots straight to a shell with no login — that identity owns
  nothing.** `Live`, 2026-07-19: there is no `claude` account on this
  disk (`list /dd/sys/password` shows only an unnamed UID-0 entry and
  `USER1`-`USER4`, no passwords set). Any file created/left over from a
  never-logged-in session is owned by that default identity, and a
  later session touching it non-destructively (read-only) is usually
  fine but write/delete fails `E$FNA`(214) if you're not that same
  identity. **Run `login USER1` as the first command of every session**
  that will create, delete, or modify files — cheap (`login USER1` +
  Enter, no password prompt) and avoids an entire class of confusing
  "no permission" failures on files from earlier sessions. Don't build
  tests around a fixture file's assumed ownership across sessions;
  either log in consistently or have the test create its own fixture.
  Separately, and not yet root-caused: the pre-existing `CLAUDE`
  directory on this disk has refused brand-new file creates
  (`E$CEF`/218 "already exists", even for names confirmed absent)
  despite the disk having 170,000+ free sectors and the identical
  create working fine at the disk root — plausibly `CLAUDE`'s own
  directory-extension needs owner permission the logged-in user lacks;
  work around by creating new fixtures at the disk root instead of
  inside `CLAUDE`.
- **After a long CPU-bound guest computation (e.g. a multi-second/minute
  BASIC09 loop), the next `key`/`send` command can land corrupted or be
  silently dropped entirely.** `Live`: immediately
  after a ~5000-iteration transcendental-math loop finished, the next
  `key "e <name>" Enter` produced a burst of `What?`/`Error #043 --
  Unknown Procedure` (characters arriving split into bogus fragments),
  and a later attempt produced nothing at all — the channel had gone
  fully unresponsive to input (even a plain `dir` got no response),
  requiring a full `restart` to recover. Root cause not confirmed —
  plausibly the guest's adaptive SERREAD polling rate (see below) having
  throttled down during the long input-idle stretch and not catching up
  cleanly. **Trigger condition may be broader than "long computation"
  specifically** — a separate session hit the same delayed/bundled-output
  symptom (a `LIST` and an editor's exit confirmation both arriving late,
  attached to a later unrelated command's response) after nothing more
  than normal editing and several back-to-back `key` calls in quick
  succession, no long computation involved. `Flag` (`Manual`): consistent
  with either "long computation" or "several rapid `key` calls" as the
  real trigger, not yet distinguished.
  **Deliberate reproduction attempt, 2026-07-23 — NEITHER trigger
  reproduced it; read this before spending a session re-running the same
  experiment.** Both stated triggers were driven on purpose: (a) 26+
  consecutive `key` calls with no computation, twice (authoring two
  BASIC09 procedures line-by-line with no pauses) — channel stayed clean
  both times; (b) a genuine 5000-iteration `SIN`/`COS` loop, 237 s of
  guest compute, then three immediate probes including the exact
  `key "e <name>" Enter` the original report says failed — all three
  clean (workspace `DIR` correct, editor opened, `q` returned to `B:`).
  So the symptom is real (two independent sessions saw it) but is **not**
  reliably produced by either stated condition, and the trigger stays
  undistinguished — now with the cheap experiments already spent. Do not
  read this as "fixed": one non-reproduction cannot refute two
  observations, and the cause may be timing- or build-dependent. Keep the
  mitigation below; it costs one command.
  **Practical mitigation**: after
  any long-running guest computation, or after a burst of rapid `key`
  calls, send one cheap probe command (e.g. `dir`) and confirm it
  actually produced fresh output before trusting further `key`/`send`
  calls; if a probe comes back stale/unchanged or garbled, don't keep
  retrying blind — go straight to `restart` (matches the general "2-3
  attempts, then stop" rule elsewhere in this skill).
- **"Unresponsive" is usually just slow — calibrate before diagnosing.**
  `Live`, 2026-07-23: a 5000-iteration `SIN`/`COS` BASIC09 loop takes
  **237 seconds** of guest time. A 30-second wait looks exactly like a
  wedged channel, and a session acting on that misreading will `restart`
  a perfectly healthy harness and lose its workspace. Budget guest
  compute in minutes; poll for a sentinel the program prints
  (`until tmux capture-pane -p -t nitros9repl:2 | grep -q DONE`) rather
  than sleeping a guessed interval.
- **Two echo behaviours that look like character loss but are not.**
  `Live`: `LOAD <file>` at the `B:` prompt echoes the **procedure name it
  loaded**, not the command line — so `LOAD burn.b09` shows as `B:burn`,
  which reads exactly like a mangled send. And the DriveWire server pane
  (window 0) shows repeating `->43` / `<-0000` — `OP_SERREAD` polls — the
  whole time, *including while the guest is busy computing*. **Do not read
  SERREAD polling as "a process is parked at a prompt waiting for input"**
  (this session did, and drew the wrong conclusion from it): the poller
  runs regardless of what the guest is doing, so it distinguishes nothing.
- **The disk image (`.ide` file) persists fully across `restart`** — it's
  a real file being edited in place, not reset to a pristine snapshot
  each time. Useful (source files you've authored survive a `restart`
  used for unrelated recovery), but also a trap: leftover files from a
  previous attempt (a stale 0-byte output file, an old test source) will
  still be there and can make a fresh attempt look like it silently
  failed when it's actually just seeing old state. `del` anything you're
  about to regenerate before trusting `dir`/`fsize` on it, or use a fresh
  name each attempt.
- **`tee >file` failing (`Error #218 - File Already Exists`) doesn't stop
  the shell from accepting more input — and that's a trap.** If you don't
  verify the `tee` actually opened (use `send`, which blocks until either
  a real prompt reappears or times out — a `tee` that's genuinely
  waiting for stdin will *not* return a prompt, so a fast return means it
  failed) before blindly typing the rest of a file with `key`, every
  subsequent line gets typed as a literal shell command instead of file
  content — each one fails individually (`Error #215`/`#216`, or `WHAT?`
  for a bare tab-indented line), and a final `key Escape` meant as
  `tee`'s EOF instead hits the **plain shell**, which also treats Escape
  as EOF and exits — killing the `/n1` shell entirely and forcing a full
  `restart`. Always `del` a stale file (or use a fresh name) and confirm
  `tee >file` actually opened before typing further lines blind.
- **`dir` with more than one wildcard argument only shows the last one**
  — `dir hello*.a other*` silently drops the first pattern's results
  rather than concatenating both. Check one glob at a time if you need to
  confirm multiple files exist.
- **This NitrOS-9 shell's `grep` doesn't support `-e` for multiple
  patterns** (unlike GNU grep) — `grep -e pat1 -e pat2 file` errors
  `grep: can't open -e`, treating it as a filename. Run separate `grep`
  calls per pattern instead.
- **Bash quoting: a literal `$` in a `key`/`send` argument needs
  escaping.** Typing OS-9 syscall names (`I$WritLn`) or hex literals
  (`PRINT $FFFF`) through `./tools/nitros9repl.sh key "..."` inside a
  double-quoted bash string triggers bash's own variable expansion —
  `$WritLn`/`$FFFF` look like unset shell variables and silently vanish,
  so the guest receives `I` or a bare `PRINT` with no argument, no error
  either side of the pipe. Escape as `\$` inside double quotes (e.g. `key
  "OS9 I\$WritLn" Enter`), or single-quote the whole argument.
- **Benchmarking gotcha: don't trust a single timed run.** Real-hardware
  timing on this harness has shown high run-to-run variance unrelated to
  anything in BASIC09 itself — almost certainly host system load (XRoar
  is a real-time CPU emulator sharing the host's actual cores). Run any
  timing-sensitive benchmark at least 2-3 times and average, discarding
  outliers, the same discipline used for `basic09c` native-benchmark
  timing. **Default to full speed unless a test specifically depends on
  real-time pacing** (the 68k sibling REPL's `os9exec -r` flag is the
  same policy, see `common/using-os9exec-repl.md`) — `NITROS9REPL_EXTRA_XROAR`
  (env var, e.g. `NITROS9REPL_EXTRA_XROAR=-no-ratelimit`) passes extra
  flags straight to XRoar for an unthrottled/full-speed run. Note the
  default headless flags (`-ui null -ao null`) may already run at or near
  full speed with no audio clock to sync against, so `-no-ratelimit`
  isn't guaranteed to change much; measure, don't assume. Only skip
  full-speed mode for a test that genuinely needs realistic timing (e.g.
  measuring how far behind a slow reader falls against a real-time
  producer cadence).

## `rma` hangs indefinitely — don't use it, use `asm` instead

**`Live`, reproduced 6+ times across independent
`restart`s, root-cause investigation done, conclusively a real bug — not
a REPL artifact.** Invoking the Relocating Macro Assembler (`rma`, or its
`rma.6809`/`rma.6309` aliases — byte-identical copies of the same module,
not distinct builds) on this disk/XRoar setup never returns. Ruled out,
each independently:
- **Not a syntax mistake.** Fetched RMA's own official help text
  (`level2/sys/rma.hp` in the `nitros9project/nitros9` GitHub source,
  via `gh search code`/`gh api`) — `rma hello.a -o=hello2` and bare
  `rma hello.a` (syntax-check-only) both match the documented syntax
  exactly. Confirms `-o=path` takes no space; `-l` (listing) has no
  argument at all and goes to stdout, redirect with plain shell `>`, not
  a flag value — `-l=file.lst` was never
  valid syntax, but removing it made no difference to the hang.
- **Not source-size- or `USE`-dependent.** Hangs identically on a tiny
  10-line source with zero `USE` directives (raw `SWI2`+`FCB` syscall
  bytes, no DEFS file) and on a `USE os9defs.a`-heavy source.
- **Not an output-flag issue.** Hangs with `-o=name`, with no `-o` flag
  at all (pure syntax-check mode, no file ever written), identically.
- **Not insufficient memory.** The `#<size>k` shell execution-memory
  modifier (documented in `common/os9-tools-and-shell.md`, `Live` on 68k
  for undersized BASIC09 programs) doesn't even reach the
  hang — `rma <file> #8k`/`#64k` in any position on the command line
  gives an immediate `WHAT?` from the shell itself, before `rma` starts
  at all. (This is itself a minor, separate, unexplained oddity: `dir
  #32k` accepts the same modifier syntax fine, so it's specific to `rma`
  somehow, not a Shell+-wide problem — not investigated further.)
- **Definitively not host-side plumbing.** Ran `rma` via the wrapper's
  own `send` (proper `ensure_chan`/`wait_prompt` gating, not a raw tmux
  bypass) and polled the actual `nc` process and its TCP socket directly
  via `ps`/`lsof` every 1-2 seconds for 8+ continuous minutes: the
  connection stayed `ESTABLISHED` the entire time, zero drops, zero
  state changes. XRoar's own process showed sustained non-zero CPU
  (~12%) throughout — the emulated CPU is genuinely doing *something*
  the whole time, not frozen or crashed. The guest shell simply never
  produces a new prompt. This is a pure guest-side hang (in `rma` itself,
  in this specific disk image, or in an XRoar 6809-core emulation edge
  case `rma`'s own algorithm happens to trigger) — not a dead connection,
  not a REPL bug, not a timing race.

**Use `asm`** (a separate, smaller, non-relocating assembler also on this
disk) for ordinary single-file MOD/EMOD assembly instead — `Live`, fast
(under a few seconds) and correct (`00000 error(s)`, correct byte count,
on a real test program). This blocks testing the RLINK/PSECT/VSECT
multi-file build path, which requires `rma`. If a `send`/`key` command
sits at `[TIMEOUT]` right after an `rma` invocation, that's this bug —
don't retry it hoping for a different result, and don't assume the
channel itself is broken (see the `pane_current_command` gotcha below —
a *different*, false-lead detour this same investigation ran into before
the clean 8-minute measurement above ruled it out).

**Possible workaround for future work, not yet tried**: modern NitrOS-9
itself no longer builds with the vintage Microware `rma`/`rlink` binaries
at all — the project's own `rules.mak` (in `nitros9project/nitros9` on
GitHub) uses `lwasm` (a modern, open-source, actively maintained 6809/6309
cross-assembler) as RMA's drop-in replacement for building the OS from
source. If RMA-equivalent (relocatable, multi-file PSECT/VSECT) output is
ever needed without waiting on a root-cause for the
hang, cross-assembling with `lwasm` on the host and injecting the result
into the disk image (via ToolShed, same technique as
`feature-xroar-autoboot-and-drivewire-fixes`) would sidestep the guest
binary entirely — untried, but a real, concrete option.

**Injecting large files (bigger than `tee`/`key` can type line-by-line),
`Live`**: this project's ToolShed build
(`os9/nitros9/tools/toolshed/build/unix/os9/os9`) can extract the RBF
filesystem straight out of the XRoar `.ide` container and inject/read
files host-side, with XRoar stopped — used successfully to get two real
third-party source files (25KB/90KB) onto the disk image directly,
something the REPL's own `tee`/`key` route can't handle at that size.
**Real ToolShed bug found this way**: `os9 copy -r` (rewrite-if-exists)
updates a file's *declared size* correctly but can leave some of its
*data blocks* holding stale bytes from whatever previously occupied
those segments — `fstat` reports the right size, but `list`/actual
content can be wrong. Confirmed by overwriting a file in place with `-r`
and finding its opening bytes replaced by unrelated leftover content.
Fix: `del` the old file, then a fresh `copy` (not `-r` in place) —
re-verified byte-for-byte correct afterward. Not filed upstream; worth
remembering if a future session hits "my source doesn't match what I
wrote" after a ToolShed `-r` overwrite.

## `pane_current_command` reporting `zsh` is NOT proof the channel died

**Hard-won lesson.**
When a `send`/`key` call times out, `tmux list-panes -t <session>:chan -F
'#{pane_current_command}'` often reports `zsh` instead of the expected
`nc`/`perl` pipeline — this looks exactly like "the bridge process died and
fell back to an interactive shell," and chasing that theory (killing and
recreating the `chan` window, or a full `restart`) can burn a lot of time
for nothing. **Check for real**: `ps -o pid,ppid,command -A | awk -v
p=<chan_pane_pid> '$2==p'` — if `nc` and `perl` show up as actual *children*
of that shell PID, the bridge is alive and connected regardless of what
`pane_current_command` claims (tmux's heuristic for "current command" on a
piped compound command apparently reports the outer shell, not the deepest
pipeline stage, even while both children are running fine). A genuinely
dead channel looks different: no `nc`/`perl` children at all under that
pane's PID. Don't use `pane_current_command` alone as a liveness check for
this harness's `chan` window.

## DriveWire server-side facts (for anyone touching the protocol)

Found by implementing the server against the spec and testing live —
both are easy to get wrong:

- **OP_DWINIT ($5A) must be answered with a NON-ZERO byte.** The NitrOS-9
  driver treats zero/no response as a DW3 server and silently disables all
  DW4 extensions including the virtual-serial poller — symptom: channel
  opens, guest output flows, but zero OP_SERREAD ($43) polls ever arrive,
  so host→guest input is never fetched.
- **EOU boots emit ~20 bare `$64 $00` pairs** (OP_SERWRITEM naming a
  never-opened channel, with no count byte). A server that reads a count
  there desyncs and swallows the guest's SERINIT. Consume exactly 2 bytes
  for a SERWRITEM addressed to an unopened channel (matches DW4/pyDriveWire
  field behavior).

Guest-side driver architecture (`Source`, `Live`):
`scdwv.dr` is the SCF driver (SERINIT with the port number at open;
FASTWRITE = $80 + port for output); the SERREAD polling loop lives in the
`dwio` subroutine module's VIRQ handler at 3/6/40-tick adaptive rates —
which is why the DWINIT response gates whether polling happens at all.
`/N1` = wire channel 1 (1-based on the wire; channel 0 unused).

The authoritative protocol spec is `DriveWire Specification.md` in the
drpitre/drivewire repo itself.
