# Driving a live NitrOS-9 (6809) system

Operating a text-driven harness against NitrOS-9 on an emulated CoCo3. The
68k equivalent (os9exec) is `common/using-os9exec-repl.md`; seeing the actual
display is `6809/reading-the-coco-screen.md`.

## Why 6809 needs a bridge

XRoar is a real CoCo3 hardware emulator running real ROM firmware — no
software-CPU-plus-kernel shortcut — and its console is a video+keyboard GUI,
not stdio. A plain PTY/pipe harness has nothing to attach to, so a text-channel
bridge is mandatory. The established one is **DriveWire over XRoar's built-in
becker port** (`-cart-becker -becker-port <port>`), which tunnels the DriveWire
protocol over TCP to a DW4 server, one of whose virtual serial channels carries
a shell.

The guest supplies the channel, so a stock DW4 server needs no patching:
`inetd` reads `/DD/SYS/inetd.conf`, opens `/N` and sends `tcp listen <port>`;
on a connection the server announces `<id> <port> <address>`, inetd opens a
second `/N`, sends `tcp join <id>`, dups it onto stdin/stdout/stderr and forks
the configured program. That vocabulary — `tcp connect|listen|join|kill` — is
NitrOS-9's own `lib/net.as`. Conf line is `port[ options],program,params`;
the options (`telnet auth protect banner`) are server-side and may be ignored,
which suits a harness — no telnet negotiation to strip.

**Spawn `login`, not `shell`** (ownership — see Session facts). It prompts
`User name?: `, and `Password: ` only when that user's password field is
non-empty. Answer on *every* connection: inetd forks a fresh login per
connection.

**The guest picks the port, but the socket is bound host-side.** It comes from
the disk's `inetd.conf`, so concurrent harness runs need *different* ports and
each run's disk clone must be edited to match — pointing a client at a port the
guest never asked for just hangs, with nothing listening and no error.

Prerequisites, each obtained separately: XRoar; a **CoCo3 ROM image**
(proprietary, Tandy-derived, not redistributable); a bootable NitrOS-9 IDE
disk image (NitrOS-9 itself is open source, but bundled third-party software
may not be); a DriveWire server.

Launch shape:

```
xroar -rompath <romdir> -machine coco3 -tv-input rgb -machine-cart ide \
  -cart-rom <idecart>.rom -load-hd0 <disk>.ide \
  -cart-becker -becker-port <port> -type 'DOS 0\r\r' \
  [-ui null -ao null | -ui <real-backend>]
```

`-ui null -ao null` is headless — fine for text-only work; a real `-ui`
backend is mandatory for graphics or screenshots. **XRoar takes the last
`-ui` flag given**, so a later one overrides an earlier hardcoded default.
`-no-ratelimit` runs unthrottled: a disk that takes ~40 s to boot throttled
boots in about 4. Default to full speed unless a test genuinely depends on
real-time pacing.

Two shells exist on one boot: the DriveWire channel shell (what the harness
drives) and a **second, independent shell on the real local console**
(`Term!NN`), visible only if XRoar has a window. Commands sent over the
channel never reach the console shell; typing into that one means sending real
keystrokes to the XRoar application.

## Harness shape and its gotchas

Same gated-send / raw-key-fallback pattern as the 68k side, but the transport
is TCP to the DriveWire-exposed channel rather than a PTY.

- **The prompt-gate doesn't recognize a sub-program's own prompt.** `Live` (NitrOS-9),
  with three: `debug <module>` drops to `DB:`, `help <topic>` to a `Topic:`
  follow-up, BASIC09's `e <name>` to `E:`. The gated send sits at timeout in
  all three even though the command worked and its output is right there.
  General pattern, not a fixed list — any sub-program with its own read loop
  does it. Switch to raw keys once inside; a bare Enter exits `help`'s
  `Topic:`.
- **Escape ($1B) is SCF's default end-of-file character.** A program reading
  the channel that receives one reads EOF, and the shell exits normally on it.
  Under inetd that is cheap to recover from — reconnecting forks a new shell —
  but it still destroys the session's state. Filter Escape out of anything
  meant as literal content; a deliberate EOF is a raw Escape key.
- **OS-9 wants CR line endings on input**, not CRLF/LF.
- **Prompts have no trailing newline**, so any pipeline displaying channel
  output must be unbuffered — line-buffering holds the prompt back and the
  harness never sees it.
- **inetd turns guest echo (PD.EKO) and auto-LF (PD.ALF) on**, so the guest
  echoes input and ends lines CR LF. Suppress *local* echo, and collapse CR LF
  to one newline — drop LF then map CR to NL, which is chunk-safe; a plain
  CR→NL translation double-spaces everything. A shell parked on a channel by
  the boot script instead has neither flag set.
- **Each connection is a separate session**: disconnecting ends that shell,
  reconnecting forks a new one (new pid, cwd back at the root), nothing is
  replayed. Don't rely on a session surviving a dropped client.
- **The listen port does not exist until the guest has booted far enough to
  run inetd**, so a client started with the emulator is refused; retry.
- **A channel with nothing joined to it parses guest output as `tcp`/`dw`
  command text** and answers `FAIL`. That is what a shell parked on a bare
  channel looks like against a DW4 server.
- **Guest time is already correct at boot** if the disk's `clock2_dw` fetches
  it from the DriveWire server (OP_TIME). Don't run `setime`.
- **A literal `$` in a shell-quoted harness argument needs escaping.** Typing
  syscall names (`I$WritLn`) or hex literals (`PRINT $FFFF`) inside a
  double-quoted bash string triggers bash's own expansion and they silently
  vanish — the guest receives `I` or a bare `PRINT`, with no error on either
  side. Escape as `\$`, or single-quote the whole argument.

## Session facts

- **An unauthenticated session owns nothing.** Files it leaves are owned by the
  boot identity (user 0), and a later session's write or delete fails `E$FNA`
  (214) unless it is that same identity. Authenticate every connection via
  inetd's `login`, or run `login USER1` as the first command. `Live` (NitrOS-9): with
  login, `procs` shows User Number 1 and `dir -e` shows new files owned by 1.
  Don't build tests around a fixture's assumed ownership across sessions.
- **`.login` is 68k-only** (`Live`; on 68k it sets `PATH`/`TERM`/`chx`/`chd` —
  `common/using-os9exec-repl.md`). Nothing on 6809 reads one: not `login`, not
  any shell on the disk. Per-user setup is the `SYS/password` fields instead —
  `name,password,uid,priority,execdir,datadir,program`. `datadir` is the
  login-time working directory, `execdir` is command search, and **`program`
  is the per-user startup hook**: normally `SHELL`, but point it at a procedure
  file and that runs on every login. `.` in either directory field means
  inherit. `login` also prints `SYS/MOTD`.
- **No `.login` means no `PATH`, so `chx` elsewhere strips you of every
  utility.** `Live` (2026-07-25). Fork lookups resolve against the execution
  directory (`common/using-os9exec-repl.md`, "Fork lookups use chx, not
  PATH"), and on 6809 nothing sets `PATH` for a logged-in account. So the
  moment you `chx` to your own directory — running programs off a
  DriveWire-mounted image, say — `procs`, `runb` and the rest become
  unreachable, and the failure reads as "my disk is broken" rather than "my
  search path moved". Two fixes: `load procs`/`load runb` **before** the
  `chx`, since a resident module is found in the module directory ahead of
  any directory search; or `setenv PATH` yourself. The `load` route is the
  one to use in anything you ship — it depends on the module being present,
  not on where the host system happens to keep it.

- **The `.ide` disk image persists across restarts** — it's a real file edited
  in place, not a pristine snapshot. Source files survive a restart, but so do
  stale outputs from a failed attempt, which make a fresh run look like it
  silently failed. `del` anything you're about to regenerate, or use a fresh
  name each attempt.
- **XRoar edits the `.ide` image in place**, so two harnesses booting the same
  image corrupt each other and their servers fight over one becker port.
  Concurrent sessions need a private disk clone, a unique session name, and
  unique ports. On APFS `cp -c` clones a 134 MB image in ~5 ms. **Verify with
  `lsof` which image XRoar actually has open** — a survivor process from a
  previous run gets reused and silently writes to whatever disk *it* booted.
- **"Unresponsive" is usually just slow.** `Live` (NitrOS-9): a 5000-iteration `SIN`/`COS`
  BASIC09 loop takes **237 seconds** of guest time. A 30-second wait looks
  exactly like a wedged channel, and restarting on that misreading loses the
  workspace. Budget guest compute in minutes and poll for a sentinel the
  program prints rather than sleeping a guessed interval.
- **Two echo behaviours that look like character loss but aren't.** `Live` (NitrOS-9):
  `LOAD <file>` at `B:` echoes the **procedure name it loaded**, not the
  command line — `LOAD burn.b09` shows as `B:burn`. And the DriveWire server
  shows repeating `OP_SERREAD` polls the whole time, *including while the
  guest is busy computing* — polling is not evidence that a process is parked
  at a prompt.
- **After a long CPU-bound computation, or a burst of rapid sends, the next
  command can land corrupted or be dropped.** `Live` (NitrOS-9) in two independent
  sessions; deliberate attempts to reproduce it from either condition alone
  failed, so the trigger is not established. Mitigation costs one command:
  send a cheap probe (`dir`), confirm fresh output, and go straight to restart
  if it comes back stale or garbled rather than retrying blind.
- **Benchmarking: don't trust a single timed run.** XRoar is a real-time CPU
  emulator sharing host cores, so run-to-run variance tracks host load. Run
  timing-sensitive benchmarks 2–3 times and average.

## Authoring a BASIC09 program on the disk

The disk is a real IDE image, not a host-native directory, so the 68k trick of
editing host-side and `flip -m`-ing into place doesn't apply — there is no
host file to touch. Two routes:

**BASIC09's own editor**, usually least work for a short program: raw-key `e
<name>` Enter drops into `E:` (leading space means insert, `q` returns to
`B:`) — same editor and behavior as 68k.

**An OS-9-native heredoc**, better once per-line sends become the bottleneck:

```
key "tee >progname" Enter
key "PROCEDURE progname" Enter
key " DIM x: INTEGER" Enter
key " PRINT x" Enter
key Escape        # EOF for tee, consumed by tee — not a shell exit
```

Then `LOAD progname` inside `basic09` compiles the text directly. The Escape
is consumed by whichever process is reading the channel at that moment; the
shell prompt reappears normally afterward.

- **Don't lead the file with a comment.** A `!` comment as the literal first
  line, before `PROCEDURE`, makes `LOAD` fail the *entire file* with `Error
  #043 -- Unknown Procedure` on 6809 — silently fine on 68k. Put `PROCEDURE`
  on line 1. Full writeup: `basic09/gotchas.md`.
- **A failed `tee >file` doesn't stop the shell accepting input, and that's a
  trap.** If `tee` fails (`Error #218 - File Already Exists`) and you type the
  rest of the file blind, every line runs as a shell command, and the final
  Escape meant as `tee`'s EOF hits the **shell**, which also treats it as EOF
  and exits — killing the session shell. Confirm `tee >file` actually opened
  first: a gated send blocks on a real `tee`, so a fast return means it failed.
- **Injecting files too large to type**: ToolShed can extract the RBF
  filesystem straight out of the `.ide` container and inject files host-side,
  with XRoar stopped. **ToolShed bug**: `os9 copy -r` (rewrite-in-place)
  updates a file's declared size but can leave data blocks holding stale bytes
  — `fstat` reports the right size while the content is wrong. `del` then copy
  fresh instead of `-r`.
- Host-side editing generally: the OS-9 partition starts at byte **323,584**
  inside a `68IDE.ide` container (`Live` (NitrOS-9) — an RBF LSN0 with volume name
  "NitrOS-9 EOU 6809"), which ToolShed cannot read directly. `dd` the
  partition out, run `os9 copy` against the raw partition, `dd` it back with
  `conv=notrunc`. XRoar must be stopped throughout.

## Running multi-process tests

- **A `What?` flood is BASIC09's debugger spinning on EOF** — not the shell,
  not lost data. `Live` (NitrOS-9): a program launched as `basic09 <script` that hits an
  **uncaught runtime error** breaks into the interactive debugger, whose stdin
  is the redirected script file, now at EOF. It reads past EOF endlessly and
  emits `What?` on every empty read, hanging the job with its output file
  unwritten — which reads exactly like the filesystem dropping every write.
  The same program with stdin on a terminal drops to `D:` and blocks properly.
  So: `What?` means "find the uncaught error", and any program driven
  non-interactively wants an `ON ERROR` so a fault reports instead of spinning.
- **`SHELL` exists in 6809 BASIC09 and really forks** — some 68k-era
  documentation implies it is 68k-only. It costs a process fork per call,
  roughly a quarter of a call per second on a 2 MHz 6809. A burst of writes to
  `/nil` is far cheaper but does **not** yield long enough to let another
  process interleave, so it's no substitute when the point is a scheduling
  window.
- Watch total memory when backgrounding several `#32k` jobs that each fork
  `SHELL`: `Error #237 (RAM Full)` on a CoCo3 is easy to reach. Stagger the
  launches or shrink the footprint.

## Syscalls that end the session, despite benign-looking names

Most dangerous calls announce themselves (`F$Boot` reboots; `F$IRQ` installs a
real hardware vector). These three do not, and each costs a restart:

- **`F$AProc` / `F$NProc`** — scheduler-internal. `F$NProc` does not *return*;
  it dispatches the next process, so execution never comes back to your code.
- **`F$IOQu`** — queues the caller on an I/O event with no timeout. Nothing
  wakes it if the event never arrives, and the shell never reprompts.
- **`F$SSvc`** — patches the *live* system-call dispatch table. A wrong entry
  corrupts the running kernel rather than failing the call.

Register details for all of them: `6809/syscalls-and-module-format.md`. Test
these only where losing the session is acceptable, or from a forked child so
the blast radius is the child rather than your shell.

## `rma` hangs indefinitely — use `asm`

`Live` (NitrOS-9), reproduced 6+ times across independent restarts: invoking the
Relocating Macro Assembler (`rma`, or its `rma.6809`/`rma.6309` aliases —
byte-identical copies of one module) on this disk/XRoar setup never returns.
Not a syntax error, not source-size- or `USE`-dependent, not an output-flag
issue, and not host-side plumbing — the TCP connection stays established
throughout and XRoar shows sustained CPU, so the emulated CPU is genuinely
doing something; the guest shell simply never produces a new prompt. A pure
guest-side hang.

**Use `asm`** — a separate, smaller, non-relocating assembler on the same disk
— for ordinary single-file MOD/EMOD assembly. This blocks the
RLINK/PSECT/VSECT multi-file build path, which requires `rma`. Modern NitrOS-9
no longer builds with the vintage `rma`/`rlink` binaries at all; its own build
rules use **lwasm**, a maintained open-source 6809/6309 cross-assembler, as
RMA's drop-in replacement. Cross-assembling with lwasm on the host and
injecting the result sidesteps the guest binary entirely.

Related shell facts found alongside: `rma <file> #8k` gives an immediate
`WHAT?` from the shell before `rma` starts, though `dir #32k` accepts the same
modifier — the `#<size>k` execution-memory modifier is rejected for `rma`
specifically. `dir` with more than one wildcard argument shows only the last
one rather than concatenating. This NitrOS-9 `grep` has no `-e` (it treats the
flag as a filename); run one pattern per call.

## DriveWire protocol contract

Both of these are easy to get wrong and both have bitten real projects:

- **OP_DWINIT ($5A) must be answered with a NON-ZERO byte.** The NitrOS-9
  driver treats zero or no response as a DW3 server and silently disables all
  DW4 extensions including the virtual-serial poller. Symptom: the channel
  opens and guest→host output flows fine, but no OP_SERREAD ($43) polls ever
  arrive, so host→guest input is never fetched — no error on either side.
- **A SERWRITEM ($64) addressed to an unopened channel is followed by exactly
  2 more bytes, with no count byte.** A server that expects a count field
  desyncs and swallows the guest's next real message (its SERINIT). An
  EOU-style boot emits ~20 of these during startup.

Guest-side driver architecture (`Source`, `Live` (NitrOS-9)): `scdwv.dr` is the SCF
driver (SERINIT carries the port number at open; FASTWRITE = $80 + port for
output); the SERREAD polling loop lives in the `dwio` subroutine module's VIRQ
handler at 3/6/40-tick adaptive rates — which is why the DWINIT response gates
whether polling happens at all. `/N<n>` is wire channel n; channel 0 is unused.
Opening the bare `/N` descriptor makes the multiplexer hand out the lowest free
channel, so an inetd session's device name (and hence its shell prompt) varies
run to run — match the prompt loosely, not against a fixed `N1`.
