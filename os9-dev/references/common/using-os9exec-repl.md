# Driving os9exec as an Agent

Operational mechanics for running an OS-9/68k system through the os9exec
emulator: launching, running programs, editing files, accounts, recovery.
Everything here was verified against a live emulator. The 6809 equivalent
(NitrOS-9 under XRoar) is `6809/using-nitros9-repl.md`.

## Platforms

os9exec is one C codebase that builds native on **macOS** and **Linux**
(`make`) and cross-compiles to a genuine Windows PE via **mingw-w64**
(`make OS=Windows_NT CC=x86_64-w64-mingw32-gcc`) — no Wine involved; the PE
runs natively (an x86_64 build executes on ARM64 Windows through the OS's own
x64 emulation). The repo's `test/` integration suite (a Swift `OS9Tests`
runner that pipes commands to the emulator) drives it identically on all
three, so REPL sessions and batch tests behave the same cross-platform. A few
*host*-filesystem behaviors legitimately differ on Windows (NTFS permission
mapping, device-alias path resolution) — those are emulator-platform quirks,
not OS-9 facts, so don't encode them as OS-9 behavior.

## Launching and disks

- `OS9DISK=<path>` (or a `dd` file/dir beside the binary) mounts as `/dd`;
  `OS9H0`…`OS9HZ` (or `h0`…`hz` beside the binary) mount as `/h0`…`/hz`.
  Each can be a host directory or an RBF disk image.
- Launch: `OS9DISK=/abs/path/disk ./os9exec /dd/CMDS/shell`
- macOS first run: `xattr -d com.apple.quarantine os9exec`
- **Never write `OS9DISK=./disk`.** A leading `./` silently breaks every
  ordinary file open while module loading still works: the emulator boots,
  the boot program runs, but the shell can't exec anything (`not
  accessible` even for absolute paths) and can't open `/dd/SYS/errmsg` —
  that boot-time "Unable to open error message file" is the tell. Bare or
  absolute paths both work. The symptom is indistinguishable from a
  missing C-library trap handler, so rule this out first.
- **Verify which host directory a device maps to before creating host-side
  test files**: run `dir` inside the emulator and `ls` on the host and
  compare. Mount conventions drift; a file dropped into the wrong host
  directory is simply invisible inside the emulator and mimics a "can't
  open file" bug.
- Booting a full system: `os9exec shell /h0/startup` (the startup file is
  an argument to the `shell` boot program — booting the file directly
  fails with `E_FNA`). A startup file typically `load`s the toolchain and
  common utilities, then runs `tsmon /term` for a login prompt. With
  `OS9STOP=1` in the host environment, typing `stop` shuts the emulator
  down cleanly.
- **Default to full speed unless a test specifically depends on real-time
  pacing.** `os9exec` paces terminal output to the path's configured baud
  rate by default (`baud_throttle`, on by default) — pass `-r` on launch
  (`./tools/os9repl.sh start -r`, or `os9exec -r ...` directly) to disable
  it and run at full host speed. Only skip `-r` for a test that genuinely
  needs realistic timing (e.g. measuring how far behind a slow reader
  falls against a producer writing on a real-time cadence) — for
  everything else (the overwhelming majority of verification/dogfood
  work), `-r` just makes the session faster with no downside.

## REPL harness: two send modes

A tmux-based harness (e.g. `tools/os9repl.sh`) typically has:

- **Gated `send`** — waits for a recognized prompt (shell `$`, debugger)
  before and after sending. **It goes silent inside any sub-program with
  its own prompt** (BASIC09's `B:`/`E:`, an editor, a custom login
  prompt): the send times out with zero pane change because the gate
  failed *before* sending. Not a bug — switch to raw mode. **A program's
  own raw output can trigger the same desync**, `Live`: a bare CR (no LF)
  written mid-output by the program under test repositions the terminal
  cursor to column 0 without clearing the line, so a genuine fresh shell
  prompt ends up sitting mid-line behind leftover garbled text instead of
  at line-start — the gate's prompt-matching wants the prompt at the
  start of a line, so it times out even though the underlying shell is
  fine. Recovery is the same as the sub-prompt case: one raw `key Enter`
  to force a blank prompt line (confirm with `snap`), then resend — the
  originally "timed out" command was never actually sent, so nothing is
  lost.
- **Raw `key`** — no gating, returns after a fixed delay **without waiting
  for the program to finish**. Poll the pane (`snap`) until the expected
  prompt returns; never treat `key`'s return as completion.

Rule: if the pane's last non-blank line isn't the shell's `$`, use raw
keys until you're back at the shell.

Session discipline: one command at a time, read the result before the next
send; never pipe a blind script of commands into an interactive session;
prefer running a claim over asserting it; on a wedged/garbled session a
full restart is cheap and reliable; if 2–3 attempts at the same problem
fail, stop and write up what's ruled out.

## Host-side output filtering: always `grep -a`

OS-9 programs emit control bytes freely; plain `grep` decides the stream
is binary and replaces real output with `Binary file matches`, silently
fabricating batch results (a failing program's error text vanishes and it
"passes"). Always `grep -a`; distrust suspiciously clean output in batch
runs.

## Batch-testing binaries

Each candidate can be its own boot program in a fresh instance — no shell
needed:

```
timeout 5 env OS9DISK=/abs/path/disk ./os9exec /dd/CMDS/<name> </dev/null 2>&1
```

`</dev/null` stops stdin-readers hanging; the timeout is mandatory. This
tests "loads and starts" (a usage message is a pass) — the right signal
for auditing a disk full of binaries, and far faster than driving a shell.

## Creating and editing files

Three routes, in order of preference by size:

1. **`tee >file`** + text + EOF key — OS-9-native heredoc for short files.
   EOF is ESC by default, Ctrl-D after `tmode eof=04`. Works on RBF images
   and host dirs alike.
2. **`vi`** (or `ed`) — for real editing; produces correct CR-only line
   endings natively. Needs a correct `TERM`/termcap. Basic loop: `i`,
   type, ESC, `:wq`.
3. **Host-side editing + `flip`** — host-native directories only (a file
   inside an RBF image has no host file to touch). `flip -m` → CR-only
   (OS-9), `flip -u` → LF (Unix), `flip -t` reports current state. Best
   route for large sources; the file must end up CR-only or the compiler
   reads it as one giant line. **`flip -t` before every `-m`, not just the
   first time** — `Live`: running `flip -m` a second time on a file
   that's already CR-only silently collapses it to a single line (all
   line-ending bytes vanish, not a harmless no-op or a CR↔LF swap). Easy
   to hit in an iterate-edit-reflip loop; recoverable with `flip -u` back
   to LF and re-editing, but check state first rather than reflipping
   blind.

**tmux eats a trailing semicolon**: `send-keys` treats a final `;` as its
own separator even with `-l`, so a typed C line arrives without its
semicolon — a baffling syntax error on a line that looks correct in the
pane. Escape it (`\;`) or don't end the send with `;`. Another reason to
prefer the `flip` route for source files.

## Compiling and running C

```
setenv CLIB /h0/LIB
setenv CDEF /h0/DEFS
cc /dd/source.c
```

- `cc` forks its sub-tools (`cpp`, `c68`, `o68`, `r68`, `l68`) by bare
  name, which resolves against the **execution directory, not PATH** (see
  below). Keep `chx` parked at the shared command directory (via
  `.login`); a mid-session `chx` you must remember to undo is a smell.
- `cc: cannot execute the pre-processor` usually means the sub-tools
  aren't loaded/reachable — `load` them in the startup file rather than
  patching `chx` around it.
- **Hand-invoking `l68` directly (bypassing `cc`) writes its `-o=<name>`
  output to the execution directory (`chx`), not the current data
  directory** — `Live`, same `chx`-not-`PATH`/output-defaults-to-`chx`
  pattern as `cc`'s `-F=` flag below, just not previously stated for
  `l68` on its own. Symptom: the linker reports no error, no output file
  appears in the data directory — check `chx` (typically `/h0/CMDS`)
  before assuming the link silently failed.
- A freshly compiled program in your data directory can fail to run by
  bare name (`chd` doesn't affect command search). Run it by full path, or
  put its directory on `PATH`.
- Source must be CR-only before compiling.

## BASIC09 interactively

```
basic          → B: (system mode)
B:e test       → edit mode, * / E: prompt
E: print "hi"  → LEADING SPACE required — see below
E:q            → back to B:
B:run test
B:bye          → back to the OS-9 shell
```

- **In the line editor, a leading space means "insert this line."**
  Without it the text is parsed as an editor command and usually fails
  with `What?` — easy to misread as a BASIC09 syntax error. `list` works
  from `B:`, not inside the editor.
- **Memory:** `basic #32k` (the shell's `#<size>k` modifier — see
  `os9-tools-and-shell.md`) fixes load/run failures caused by the small
  default allocation. Reach for it before suspecting the program.
- **Loading host-authored source:** write plain BASIC09 text (no editor
  artifacts), `flip -m`, place it where OS-9 sees it, then `B: LOAD
  <exact-filename>` and `RUN <procedure-name>` (from the file's PROCEDURE
  line — need not match the filename). `LOAD` compiles plain source
  directly and does a **literal name match** — no extension inference
  (OS-9 convention is no extension at all; `LOAD qt` will not find
  `qt.bas`).
- **Don't start the file with a `!` comment above PROCEDURE** if the same
  source might ever run on 6809 — fine on 68k, but 6809 fails the whole
  `LOAD` with `Error #043`. See `basic09/gotchas.md`.
- Packed modules, RunB, PACK output location, `PARAM` argument binding,
  and trap-handler error triage: `basic09/pack-and-runb.md`.
- A named pipe (`/pipe/<name>`) makes good read-once scratch storage — no
  cleanup needed.

## The cio trap handler divides archived binaries

Most archived OS-9/68k programs were linked against Microware's
proprietary `cio` C-I/O trap handler; on a disk without it they die
immediately with `**** Can't install trap handler **** / **** cio ****`.

- Classify binaries by searching for the NUL-terminated module name
  `cio\0` — not a bare substring (matches inside words), and not `math`
  (the floating-point handler is optional; referencing it is harmless).
  Only `cio`/`csl` are fatal.
- A statically linked "cio-free" build of the same utility is noticeably
  larger; prefer it when both exist.
- Escape hatch: anything compiled with a public compiler (e.g. gcc2) plus
  a POSIX-compatibility header set that wraps syscalls directly needs no
  trap handler. Small utilities are often quicker to rewrite and recompile
  than to hunt down cio-free.
- A trap handler's companion module must be reachable from the current
  `chx` (that's `F$Load`'s search path) — a module on another device fails
  with a generic Path-Not-Found even though the file exists. Check `chx`
  before suspecting a wrong-CPU binary; a path issue is likelier and
  cheaper to rule out.

## Discovering what's installed

Ask the running system, never assume: `dir /dd/CMDS` (core set), look for
freeware/toolchain subdirectories (their separation from core CMDS is
usually deliberate — name collisions), `ident`/`attr <name>` for what a
thing is, `mdir` for what's loaded, and `imdir` (an os9exec built-in, not
an OS-9 command) for the emulator's own view of loaded modules — useful to
confirm a trap handler actually installed.

## Accounts: don't stay superuser

Booting straight into `shell` runs as group 0 (superuser — `procs` shows
`Grp.Usr 0.0`). Fine for a smoke test; for real work use the login mechanism:

- Via a tsmon boot you land at `User name?:` — send just the account name
  (`login` is already running). At a shell prompt, `login <user>` works
  too (empty-password accounts skip the password prompt; an account with
  an empty password that still prompts wants a bare Enter).
- **Never use `login` as os9exec's boot program** (`os9exec login user`
  prints the banner then exits the emulator with no error). Boot to a
  shell or tsmon first; `login` from there works.
- Login authenticates against `/dd/SYS/password` (comma-separated:
  user, password, group.user, priority, initial execution dir, initial
  data dir, initial program) and forks a genuinely separate process under
  that identity. Exit with `logout` (not `bye` — that's BASIC09's).
- A fresh login inherits nothing: without a `.login` in the account's data
  directory setting `PATH` and `TERM`, even `procs` fails and `vi`
  misbehaves. A custom prompt set at login also breaks a REPL harness's
  gated send — switch to raw keys.
- **Per-account layout that works**: a personal execution directory
  *inside* the shared `CMDS` (e.g. `/dd/CMDS/ALICE`) plus a personal home
  elsewhere (e.g. `/dd/USR/ALICE`), with `.login`:

  ```
  chx /dd/CMDS
  chd /dd/USR/ALICE
  setenv PATH .:ALICE:SHARE
  ```

  **Park `chx` at the shared CMDS** — pointing it at the personal
  directory breaks more than compiler sub-tool forking: `Live`, it breaks
  **plain interactive command lookup too** (`basic #32k` failing with
  `Error #000:216 (E_PNNF)` right after a `chx` to a personal directory) —
  `PATH` entries resolve relative to `chx`, not just a compiler driver's
  own sub-process forking, so moving `chx` anywhere off the shared command
  path breaks ordinary command resolution generally, not a narrower
  compiler-specific case. With `chx` at CMDS, `PATH` entries are just
  names below it; no `..` traversal. This matches real historical
  practice: `chx` is a per-session identity set once at login, not a
  scratch variable — to make a directory runnable, extend `PATH` instead.
- Tradeoff: with `chx` at shared CMDS, compilers *default* their output
  there — name outputs explicitly (`gcc -o <name>` lands relative to
  `chd`; `cc -F=ALICE/<name>`). And `copy prog ALICE/prog` resolves
  against `chd`, not `chx` — install with a full path.

## Fork lookups use chx, not PATH

When a program forks another by bare name (`F$Fork`), the kernel resolves
against the caller's **execution directory** — `PATH` is purely the
shell's interactive search list. Classic symptom: `deldir` forks `pd` and
dies with "can't determine current directory" despite a perfect `PATH`.
Fix `chx`, not `PATH`, whenever "command X can't find helper Y."
(os9exec detail: the top-level process's chx comes from `OS9CMDS`,
default `$OS9DISK/CMDS`, interpreted as a *host* path — set chx from
inside OS-9 or via startup/`.login` instead.)

## RBF images vs. host-native directories

Two different things behind the same device names:

- A **real RBF image** behaves like OS-9: `..` clamps at the device root
  (real root inode), and genuine RBF mechanics (allocation bitmap, record
  locking) exist.
- A **host-native directory** is a convenience shim: traversal above the
  device root is possible, and RBF-specific behavior has nothing real
  underneath. Behavior observed on a host-native mount may not hold on a
  real image or real hardware. `format`/`iniz` can build a real RBF image
  from a blank file on an `OS9Hx` device when RBF-specific behavior needs
  testing.

**Host links inside a device root — avoid; if present, know the quirks**
(all verified): hard links behave as ordinary files (deleting one name
leaves the other's content). In-root symlinks resolve correctly.
A symlink pointing *outside* the device root is silently redirected to the
device root — no error, wrong data; a single such stray link can corrupt
`dsave` output downstream. `deldir` recurses into and deletes a
directory-symlink's real target (OS-9 has no link concept, so it can't
tell). Symlink cycles can crash the emulator after ~40–60 hops.

## Launching two concurrent background processes reliably

`Live`: sending a second `key` command (to launch process B) while
process A's already-backgrounded job is actively streaming output to the
same terminal is **unreliable** — sends can be silently dropped (no
echo, no effect), land several seconds late, or land visibly
character-interleaved mid-line with A's own output. Retrying a send that
looks like it didn't land is risky: it sometimes *did* land the first
time, launching a duplicate process and producing hopelessly interleaved
output from here on. **Reliable fix**: launch both in a single combined
shell command line in one `key` call (e.g. `procA & procB &`), sent while
the terminal is still idle — both start within the same real second and
there's only one send to ever retry-or-not. **Also `Live`**: an
unthrottled polling loop (no delay between retries) in two concurrent
processes can generate 1000+ retries/second combined and appears to
starve a concurrently-running process of CPU entirely (its own progress
stalls for 60+ real seconds) — a scheduler-fairness issue, not just log
noise. Give any tight retry/poll loop a small busy-wait between attempts
when running it alongside another process that needs to make progress.

## Stopping a runaway program

- **Ctrl-C**: shell keeps the prompt, child continues in background.
- **Ctrl-E**: kills the child. Documented to act immediately regardless of
  what the process is doing (compute loop, blocked write — no console
  read needed) — **`Flag`: does not hold for a process blocked writing to
  a full named pipe with no reader.** `Live`: both Ctrl-C and Ctrl-E,
  sent multiple times, had zero effect on a process wedged mid-`WRITE` on
  a full named pipe (45+ seconds observed, no progress, no response) —
  the shell prompt never returned. **A full harness `restart` was the
  only recovery; don't expect Ctrl-E to work if you deliberately induce a
  named-pipe write-block for testing.** Not root-caused: could be a real
  `os9exec`/UAE-core signal-delivery bug specific to a process parked deep
  in a kernel-level pipe wait, or the general claim simply doesn't extend
  to this specific blocked-syscall case. Host-native files/PACKed modules
  survive the restart intact; in-memory session state does not.
- `kill <pid>` after `procs`.
- **ESC on a blank line** exits the shell; a harness restart is the
  reliable reset when state is unknown.

From os9exec's own debugger (`idbg` — emulator-level, distinct from the
OS-9 `debug` command): `break` halts timesharing into the idbg prompt
(`g` resumes cleanly); `s 1` auto-enters the debugger on bus/address
errors and unimplemented syscalls *before* the process dies; `k <pid>`
kills; `q` quits the emulator. Tracing without stopping: `idbg -o 1`
(trace to terminal) or `-o /file`, `-d 2` (syscall tracing; `-dh` lists
mask bits), `-j <pid>`/`-w <pid>` include/exclude a process, `-d 0` off.

## Symbolic debugging (the OS-9 `debug` command)

`cc -g file.c` emits `file.dbg`/`file.stb`; `debug /dd/prog` auto-loads
them and shows symbol-resolved disassembly. At `dbg:`:

- `b <name>` set breakpoint by symbol — **reliable**; `g` run to it.
- `sc` (bare) lists code symbols; `sd`/`sm` data symbols / symbol modules.
  **Never take an address from `sc`'s listing**: it double-applies
  relocation (error grows with the symbol's offset), so addresses land
  inside unrelated functions. Verify any address with `di <addr>` — a
  function entry should look like a prologue. (`sc <module>` with an
  argument fails even for valid names; use bare `sc`.)
- `.` registers; `di <addr> [n]` disassemble without executing; `q` quit.
- **`gs` is not single-step**: it runs to the *fall-through* address of
  the current instruction. It steps over `bsr`/`jsr`, and on a taken
  branch the child runs until the fall-through is reached by accident —
  possibly a full loop iteration, possibly never (dead code after `bra`).
  Ctrl-C recovers to a fresh `dbg:` prompt. Use `gs` for straight-line
  code only; prefer `b <name>` + `g` to navigate.
- Both defects (`sc` addresses, `gs` stepping) are bugs in the shipped
  1980s binary, not os9exec.

---
Everything above is `Live` against os9exec unless explicitly tagged
`Manual`.
