# Driving os9exec as an Agent

Operational mechanics for running an OS-9/68k system through the os9exec
emulator: launching, running programs, editing files, accounts, recovery. The
6809 equivalent (NitrOS-9 under XRoar) is `6809/using-nitros9-repl.md`.

os9exec **is** the CPU plus an OS-9 kernel implementation, not a hardware
emulator running real firmware — no ROM, no video/keyboard console to bridge
around. Its stdin/stdout are the OS-9 console, so a plain PTY/pipe harness
works directly. It builds native on macOS and Linux and cross-compiles to a
Windows PE via mingw-w64. A few *host*-filesystem behaviors differ on Windows
(NTFS permission mapping, device-alias path resolution) — emulator-platform
quirks, not OS-9 facts; don't encode them as OS-9 behavior.

Genuine OS-9/68k binaries (Microware's shell, compilers, utilities) are
proprietary and none ship with the emulator: supply a legally-held disk image
or SDK. A host directory of your own files works identically for basic testing.

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
  compare. A file dropped into the wrong host directory is simply invisible
  inside the emulator and mimics a "can't open file" bug.
- Booting a full system: `os9exec shell /h0/startup` — the startup file is
  an argument to the `shell` boot program; booting the file directly fails
  `E_FNA`. A startup file typically `load`s the toolchain and common
  utilities, then runs `tsmon /term` for a login prompt. With `OS9STOP=1` in
  the host environment, typing `stop` shuts the emulator down cleanly.
- **Default to full speed.** os9exec paces terminal output to the path's
  configured baud rate (`baud_throttle`, on by default); `-r` disables it.
  Keep the throttle only for a test that genuinely depends on real-time
  pacing.
- **But never check OUTPUT behaviour with `-r`**, `Live` (os9exec). Pacing runs
  bytes through a finite FIFO, and that is where output gets lost or reordered;
  `-r` bypasses it, so a truncation bug is invisible under the flag you
  normally run with. This is not hypothetical: `mount -?` delivered four of its
  eleven option lines under pacing and all eleven under `-r`, and the missing
  lines were read as "this build has no `-k` option" — twice, once into a
  roadmap and once into a retraction of that roadmap entry. If a claim is about
  what reaches the screen, reproduce it the way a user sees it: no `-r`, and
  compare against the `-r` run rather than trusting either alone.

## REPL harness: two send modes

- **Gated `send`** — waits for a recognized prompt (shell `$`, debugger)
  before and after sending. **It goes silent inside any sub-program with
  its own prompt** (BASIC09's `B:`/`E:`, an editor, a custom login
  prompt): the send times out with zero pane change because the gate
  failed *before* sending. Switch to raw mode. **A program's own raw output
  can trigger the same desync**, `Live` (os9exec): a bare CR (no LF) written mid-output
  repositions the cursor to column 0 without clearing the line, so a genuine
  fresh prompt sits mid-line behind leftover text and the gate — which wants
  the prompt at line-start — times out even though the shell is fine.
  Recovery for both cases: one raw `key Enter` to force a blank prompt line,
  confirm, resend. The timed-out command was never sent, so nothing is lost.
- **Raw `key`** — no gating, returns after a fixed delay **without waiting
  for the program to finish**. Poll the pane until the expected prompt
  returns; never treat `key`'s return as completion.

Rule: if the pane's last non-blank line isn't the shell's `$`, use raw keys
until you're back at the shell. One command at a time; never pipe a blind
script into an interactive session. On a wedged or garbled session, restart —
it's cheap and reliable.

## Host-side output filtering: always `grep -a`

OS-9 programs emit control bytes freely; plain `grep` decides the stream
is binary and replaces real output with `Binary file matches`, silently
fabricating batch results (a failing program's error text vanishes and it
"passes"). Always `grep -a`; distrust suspiciously clean output in batch runs.

**Set `tmode pag=0` before reading any listing.** With page pause on, output
longer than one screen stops and waits for a key; the harness's next send
answers the pause instead of running, and the tail of the listing is lost. A
directory or `mdir` entry that exists then reads as absent — the same class of
silent truncation as the `grep` case, and just as easy to build a wrong
conclusion on.

## Batch-testing binaries

Each candidate can be its own boot program in a fresh instance — no shell
needed:

```
timeout 5 env OS9DISK=/abs/path/disk ./os9exec /dd/CMDS/<name> </dev/null 2>&1
```

`</dev/null` is explicit and harmless (a redirected host stdin now returns
end-of-file on its own, so a stdin-reader no longer hangs without it); the
timeout is still mandatory. This
tests "loads and starts" (a usage message is a pass) — the right signal
for auditing a disk full of binaries, and far faster than driving a shell.

## An internal command can BE the boot program — no shell needed

`Live` (os9exec). os9exec's own built-ins run as the boot program, so a disk
image can be built and populated with no shell, no SDK and no Microware
software at all:

```
os9exec mount -k=360k h7      # a real RBF image at <startPath>/h7
os9exec makdir /h7/SCRATCH    # ...and directories inside it
os9exec dir /h7               # SCRATCH
```

This is the route for CI and for a fresh clone with no system disk. `mount -k`
streams the image (head plus a zero tail) rather than buffering it, so size is
bounded by host disk, not by the 68k arena — 125 MB builds in well under a
second. `mount -r`, a genuine RAM disk, IS bounded by the arena and says so.

**`OS9DISK` CAN point at an RBF image** — `Live` (os9exec), re-measured
against os9exec `e8a3c81` on macOS, with `env -i` and from an unrelated
working directory. All three of these work against a 253 MB RBF
image:

```
env -i OS9DISK=/abs/image.dd os9exec -r /dd/CMDS/cat /dd/SYS/motd   # absolute
env -i OS9DISK=/abs/image.dd os9exec -r cat SYS/motd                # bare name
env -i OS9DISK=/abs/image.dd os9exec -r /dd/CMDS/cat SYS/motd       # relative open
```

The bare-name boot program proves the execution directory resolves inside the
image, and the relative open proves the data directory does. A whole test
harness in the wild drives its RBF image this way.

**This entry previously said the opposite**, tagged `Live`, on the strength of
one session: that the top-level process's directories were resolved as HOST
paths, so the boot program never started (`E_PNNF`, or `E_UNIT` from the first
relative open). It does not reproduce. Either os9exec changed, or that session
hit the `OS9DISK=./disk` trap documented immediately above — a leading `./`
breaks every ordinary file open while module loading still works, which
produces very much this shape of failure. Rule that out first if you ever see
it again; do not conclude the image cannot be mounted.

## Batch-driving a whole session: a procedure file, never a pipe

For unattended multi-command work (building an image, populating a disk),
pass the shell a **procedure file** — the mechanism `os9repl.sh` itself uses
to boot (`shell /h0/startup`):

```
gtimeout 60 env OS9DISK=<dir>/h0 OS9STOP=1 ./os9exec shell /h1/<proc> </dev/null 2>&1
```

`/h1` here is any host directory under the emulator's start path. Four traps,
all `Live` (os9exec), the first two silent:

- **The procedure file must be CR-only.** With LF endings OS-9 sees one
  enormous line: the shell echoes the entire file and runs nothing, reporting
  no error. Generate with `tr '\n' '\r'`.
- Piping the same commands into an interactive `shell` **used to hang** at
  end of input and no longer does (`Live` (os9exec), as of the freeware-sweep
  fixes): a redirected or piped host stdin now delivers end-of-file, so the
  shell runs the piped commands and then exits. The procedure file is still
  the tidier route — it gives CR-ending control and a named artifact — but a
  pipe terminating cleanly is the difference between the two now, not a hang.
- **A utility that prompts devours the rest of the file.** `copy` onto an
  existing destination reports `Error #000:218` and then asks `Overwrite
  (yes/no/all/quit)?`. The following procedure lines are read as answers to
  that prompt instead of being run, and once the file is exhausted it re-prompts
  without bound until the timeout kills it. The damage is worse than a hang,
  because a stray `y` in a consumed line answers *yes* and the overwrite
  happens anyway. Give `copy` an explicit `-r` (`-f` for a write-protected
  destination) so it never asks. Abort-on-error does *not* rescue this case:
  in a procedure file the prompt is reached before the failure can end the run,
  so the error is reported, the overwrite still happens, and the lines that
  answered it are gone.

- **The first failure ends the run, and nothing announces that it did.** The
  shell's `-x` (abort on error) is on by default, so a procedure file stops at
  its first failing command: that command's own error prints, the remaining
  lines never execute, and the run then exits looking exactly like a completed
  one. A four-line file whose second command failed produced line one's output,
  the error, and nothing further. Pass `-nx` when a batch must finish
  regardless — and never read "no further errors" as "the rest ran".

**No two utilities spell "don't ask" the same way**, so the flag cannot be
guessed: `copy -r`, `deldir -q`, `frestore -s`, `format -r`, `fsave -p`. `del`
is the one that inverts the default — it never asks unless `-p` opts in. Look
the flag up in `utility-usage.md` (which carries each one's own tag) before
putting any of these in a procedure file.

## Stamping non-super ownership on an RBF image

`Live` (os9exec). Files are stamped with the creating process's ID, so ownership is set
by *who creates them*, not by any later command. Inside a build procedure:

```
mount -k=360k h7
login claude          ← every file created after this line is owned 1.7
makdir /h7/CMDS
```

`dir -e` confirms it — `0.0` for anything created before the `login`, `1.7`
after. Two consequences worth knowing before shipping an image:

- **Copy into the image with `copy -n`.** The default duplicates the source
  file's whole FD including its owner; a host-native directory has no real
  OS-9 owner, so os9exec synthesises `0.0` and reproducing that is an owner
  change a non-super caller may not make. The copy then prints `E$PERMIT`
  *and still transfers the data*, which reads as harmless noise — the kind
  of error that trains you to ignore a real one later. `-n` creates a fresh
  FD and the error stops happening.
- **A file created by a non-super account has no public read by default**
  (`------wr`). On any machine where the operator is neither that owner nor
  in group 0, the disk is unreadable. Set public bits explicitly.
- **ToolShed's `copy -o=<id>` is not an ownership route**: it sets only the
  low byte, so the group is always 0 — and Microware defines the super user
  as *any* user in group zero, so every file would ship privileged.

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
   reads it as one giant line. **`flip -t` before every `-m`** — `Live` (os9exec):
   running `flip -m` on a file that's already CR-only silently collapses it
   to a single line (all line-ending bytes vanish). Recoverable with `flip
   -u` and re-editing, but check state first rather than reflipping blind.

**tmux eats a trailing semicolon**: `send-keys` treats a final `;` as its
own separator even with `-l`, so a typed C line arrives without its
semicolon — a baffling syntax error on a line that looks correct in the
pane. Escape it (`\;`) or don't end the send with `;`.

## Compiling and running C

```
setenv CLIB /h0/LIB
setenv CDEF /h0/DEFS
cc /dd/source.c
```

- `cc` forks its sub-tools (`cpp`, `c68`, `o68`, `r68`, `l68`) by bare
  name, which resolves against the **execution directory, not PATH** (see
  below). Keep `chx` parked at the shared command directory via `.login`.
- `cc: cannot execute the pre-processor` usually means the sub-tools
  aren't loaded/reachable — `load` them in the startup file rather than
  patching `chx` around it.
- **Hand-invoking `l68` directly writes its `-o=<name>` output to the
  execution directory (`chx`), not the current data directory** — `Live` (os9exec),
  same pattern as `cc`'s `-F=` flag. Symptom: the linker reports no error
  and no output file appears in the data directory; check `chx` (typically
  `/h0/CMDS`) before assuming the link failed.
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
- **Loading host-authored source:** write plain BASIC09 text, `flip -m`,
  place it where OS-9 sees it, then `B: LOAD <exact-filename>` and `RUN
  <procedure-name>` (from the file's PROCEDURE line — need not match the
  filename). `LOAD` compiles plain source directly and does a **literal
  name match** — no extension inference (OS-9 convention is no extension at
  all; `LOAD qt` will not find `qt.bas`).
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

- **Classify by running it, not by reading the binary** — `Live` (os9exec).
  Run each program against an image with `cio`, `csl`, `csl020`, `math` and
  `math881` removed, and match the banner. Searching the file for the module
  name `cio` is wrong in *both* directions: `vi_nocio` contains the string
  and runs without the module, while `cyberwar`, `gnuchess` and `g` do not
  contain it and need it. Only `cio`/`csl` are fatal — `math`/`math881` are
  the optional floating-point handlers and referencing one is harmless.
- A statically linked "cio-free" build of the same utility is noticeably
  larger; prefer it when both exist.
- Escape hatch: anything compiled with a public compiler plus a POSIX
  wrapper header set that calls syscalls directly needs no trap handler.
- **The same banner also means "present but not reachable."** A trap
  handler's companion module is found through the module directory and then
  the current execution directory, so moving `chx` off the directory holding
  `cio` stops every `cio`-linked program with the identical
  `**** Can't install trap handler **** cio ****` — `chx /dd/CMDS/GCC2`, to
  reach a compiler driver by bare name, does exactly this. `load /dd/CMDS/cio`
  first cures it. A module on another *device* instead fails with a generic
  Path-Not-Found though the file exists. `Live` (os9exec). Check `chx` before
  concluding the module is absent or the binary is built for the wrong CPU.

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
- **Never use `login` as os9exec's boot program** — it prints the banner
  then exits the emulator with no error. Boot to a shell or tsmon first.
- Login authenticates against `/dd/SYS/password` (comma-separated:
  user, password, group.user, priority, initial execution dir, initial
  data dir, initial program) and forks a genuinely separate process under
  that identity. Exit with `logout` (not `bye` — that's BASIC09's).
- A fresh login inherits nothing: without a `.login` in the account's data
  directory setting `PATH` and `TERM`, even `procs` fails and `vi`
  misbehaves. A custom prompt set at login also breaks a harness's gated
  send — switch to raw keys.
- **Per-account layout that works**: a personal execution directory
  *inside* the shared `CMDS` (e.g. `/dd/CMDS/ALICE`) plus a personal home
  elsewhere (e.g. `/dd/USR/ALICE`), with `.login`:

  ```
  chx /dd/CMDS
  chd /dd/USR/ALICE
  setenv PATH .:ALICE:SHARE
  ```

  **Park `chx` at the shared CMDS.** `PATH` entries resolve relative to
  `chx`, so pointing it at a personal directory breaks ordinary interactive
  command lookup, not just compiler sub-tool forking — `Live` (os9exec), `basic #32k`
  fails with `Error #000:216 (E_PNNF)` right after such a `chx`. `chx` is a
  per-session identity set once at login, not a scratch variable; to make a
  directory runnable, extend `PATH` instead.
- Tradeoff: with `chx` at shared CMDS, compilers *default* their output
  there — name outputs explicitly (`cc -F=ALICE/<name>`). And `copy prog
  ALICE/prog` resolves against `chd`, not `chx` — install with a full path.

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
- A **host-native directory** is a convenience shim: RBF-specific behavior has
  nothing real underneath. Behavior observed on a host-native mount may not
  hold on a real image or real hardware. `format`/`iniz` can build a real RBF
  image from a blank file on an `OS9Hx` device when RBF-specific behavior
  needs testing.

  **Traversal above the root is confined**, `Live` (os9exec), for devices
  configured through `OS9DISK`/`OS9Hx` and for ones created by `mount -k=0`
  alike: `list ../outside` and `list ../../../../outside` both give `E_PNNF`
  while a read inside the device works. The one exception is NESTED device
  roots — if one device's host root sits inside another's, `..` walks from the
  inner device into the outer one (the clamp matches the first configured root
  the path is a prefix of, which is the enclosing one). It still cannot leave
  the set of configured devices. When testing confinement, make sure the
  directory holding your device is not itself a device root, or you will
  measure this instead.

  **Permissions and ownership are only real on an RBF image.** A host
  directory cannot carry OS-9 ownership at all. Attributes do map to Unix mode
  bits in both directions (`Live` (os9exec): `attr f -e` → host `+x`; `chmod 400` →
  `-------r`), but Windows cannot represent them and reports read/write/exec
  forced on. Crucially the `e` attribute is *reported, never enforced* — a
  module with no `e` still runs from a host mount, because only the RBF path
  checks attributes before an open. Test permission behaviour on an RBF image.

**Host links inside a device root — avoid; if present, know the quirks**:
hard links behave as ordinary files (deleting one name leaves the other's
content). In-root symlinks resolve correctly. A symlink pointing *outside*
the device root is silently redirected to the device root — no error, wrong
data; a single such stray link can corrupt `dsave` output downstream.
`deldir` recurses into and deletes a directory-symlink's real target (OS-9
has no link concept, so it can't tell). Symlink cycles can crash the
emulator after ~40–60 hops.

## Launching two concurrent background processes

`Live` (os9exec): sending a second `key` command (to launch process B) while process
A's backgrounded job is actively streaming output to the same terminal is
**unreliable** — sends can be silently dropped, land seconds late, or land
character-interleaved mid-line. Retrying a send that looks like it didn't
land is risky: it sometimes *did* land, launching a duplicate. **Fix**:
launch both in a single combined command line in one send (`procA & procB
&`) while the terminal is idle.

`Live` (os9exec): an unthrottled polling loop in two concurrent processes can generate
1000+ retries/second combined and starve a concurrent process of CPU for 60+
real seconds. Give any tight retry/poll loop a small busy-wait when running
it alongside another process that needs to make progress.

## Two syscalls that end a scripted session

Both look ordinary in the call table and are not:

- **`F$SysDbg`** drops os9exec into its own *interactive* meta-debugger. A
  scripted harness has nobody to answer its prompt, so the session hangs.
- **`F$RTE`** kills the caller unless it is genuinely inside an intercept
  routine — and `F$Icpt` alone does not put you there.

Neither has been exercised live for that reason. Call them only from a forked
child, or where losing the session is acceptable.

## What os9exec does not implement, and how it says so

A missing call is not a crash. The unimplemented kernel-internal requests —
named under "Not implemented on os9exec" in `68k/syscall-reference.md` —
return a clean `E$UNKSVC` (208) and change nothing. A program that tests the
carry survives; one that does not may read 208 as its own failure.

Unmodelled **system globals** answer differently. A `F$GetSys`/`F$SetSys`
read of an offset os9exec does not keep prints `F$SetSys: unimplemented
<hex>` on the console and returns 0. Usually harmless, and `getsys` prints a
page of them. `D_SPUMem` ($3D8) is the one worth recognising: every
Microware-C start-up reads it to detect a System Security Module, so it
appears several times per C program, and 0 is now answered deliberately
because that is what a machine without an SSM reports — see
`kernel-internals.md` in `os9-systems-dev`.

**Do not chase these from an older report.** `F$Mem`, `F$GPrDsc` and
`F$GPrDBT` were all gaps in v4.0.0 — the first answered 208 and stopped any
program whose first allocation went through it, the other two took a bus
error instead of refusing — and later builds implement all three. `top` still
dies, and that one is `top`'s own bug rather than the emulator's: it asks for
PID 0, gets the documented `E$IPrcID` (224) refusal, ignores the carry, and
reads its unfilled buffer. It would do the same on real hardware.
`Live` (os9exec).

**The emulator's own diagnostics share the running program's stderr.** Every
`# `-prefixed line — the unimplemented-global notice above, `# No more
memory:` from the allocator, `# /tN is /dev/ttysNNN` from hostterm — goes to
that path rather than a channel of its own, so it interleaves with guest
output. `2>/nil` is what separates the two when capturing. `Live` (os9exec).

## Stopping a runaway program

- **Ctrl-C**: shell keeps the prompt, child continues in background.
- **Ctrl-E**: kills the child, immediately, regardless of what the process
  is doing — compute loop, blocked read, or blocked write.
- **Neither key aims at a process you choose.** Both are delivered to the
  device's *last writer* (`Source`, os9exec: `lastwritten_pid`), so with two
  processes interleaving output the signal can land on a bystander — the one
  that happened to write most recently, not the runaway. `kill <pid>` after
  `procs` is the aimed alternative, and the only safe one while output from
  more than one process is in flight.
- **ESC on a blank line** exits the shell; a harness restart is the
  reliable reset when state is unknown. EOF is a per-path setting a site
  may have retuned (see the dual-environment tip in
  `common/os9-tools-and-shell.md`), so a harness should not assume ESC:
  prefer the emulator's own `stop`, which sets `quitFlag` directly and
  never consults the path's EOF char. (`stop` needs group 0 or `OS9STOP`.)

From os9exec's own debugger (`idbg` — emulator-level, distinct from the
OS-9 `debug` command): `break` halts timesharing into the idbg prompt
(`g` resumes cleanly); `s 1` auto-enters the debugger on bus/address
errors and unimplemented syscalls *before* the process dies; `k <pid>`
kills; `q` quits the emulator. Tracing without stopping: `idbg -o 1`
(trace to terminal) or `-o /file`, `-d 2` (syscall tracing; `-dh` lists
mask bits), `-j <pid>`/`-w <pid>` include/exclude a process, `-d 0` off.

**`-d 2`'s `<<<` return lines can name the wrong call.** The entry (`>>>`)
and return (`<<<`) lines are printed from a single per-process current-call
field, read again at return time rather than saved at entry (`Source`,
os9exec: `cp->func`, `debug_return`). Anything that dispatches a nested call
in between overwrites it, so the outer call's return is attributed to the
inner one. Trust `>>>` lines for what was called; pair a return with its
entry by position, not by the name on it, and do not conclude a call
returned a value it never returned.

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
Everything above is `Live` (os9exec) unless tagged otherwise inline —
a few emulator-internal details are `Source` (read from os9exec's own C
rather than observed), and any `Manual` claim says so.
