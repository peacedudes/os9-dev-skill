# Driving os9exec as an Agent

When real OS-9/68k equipment is not at hand, the os9exec emulator is one way
to get an OS-9 environment to work in. This page covers the mechanics of that
stand-in: launching, running programs, editing files, accounts, recovery. On
real hardware the OS-9 reference pages apply directly, and where the emulator
and a Microware manual disagree, the manual is the specification. The 6809
equivalent (NitrOS-9 under XRoar) is `6809/using-nitros9-repl.md`.

os9exec reimplements the OS-9 kernel interface over an emulated CPU; it is
not a hardware emulator running real firmware — no ROM, no video/keyboard
console to bridge around. Its stdin/stdout are the OS-9 console, so a plain PTY/pipe harness
works directly. It runs on macOS, Linux and Windows — in practice anything
with a C compiler; the Windows build is a PE cross-compiled with mingw-w64.
The Windows build is the narrower one. A few *host*-filesystem behaviors
differ there (NTFS permission mapping, device-alias path resolution), and it
lacks several things the Unix builds have: every socket path open returns
`E$Unit`, there is no system tick (so no pre-emption; a Windows run behaves
like a `-q` run on Unix), `/tN` host terminals cannot bind, and the idle wait
polls at 1 ms rather than sleeping. `Source` (os9exec). These are
emulator-platform facts, not OS-9 facts; don't encode them as OS-9 behavior.

The CPU core is a 68020 with a 68881, and `F$SysID` reports 68020; the
`D_MPUTyp` system global, however, always answers 68040. Code that branches on
`D_MPUTyp` takes its 68040 path here. `Source` (os9exec).

Microware's own OS-9/68k software (shell, compilers, utilities) is
proprietary and does not ship with the emulator: supply a legally-held disk
image or SDK. A host directory of your own files works identically for basic testing.

## Launching and disks

- `OS9DISK=<path>` (or a `dd` file/dir beside the binary) mounts as `/dd`;
  `OS9H0`…`OS9Hz` (or `h0`…`hz` beside the binary) mount as `/h0`…`/hz`.
  Each can be a host directory or an RBF disk image. **Configure devices by
  these variables** rather than by the magic file names and host symlinks —
  the variable says plainly which image is which.
  - **The device letter is case-sensitive**: `/hz` is configured by `OS9Hz`,
    and `OS9HZ` is silently ignored — no device, no complaint. `Live` (os9exec).
  - **Two variables may name the same image, and that is supported.** A
    collection that programs expect at both `/dd` and `/h0` needs only
    `OS9DISK=<img> OS9H0=<img>` and mounts it silently. `Live` (os9exec). No
    symlinking or copying required. (The console line `# /h0: using
    OS9H0='<img>', ignoring '<startPath>/h0'` means something else: a
    magic-name `h0` file also exists beside the start path, and the variable
    won.)
  - **But only ONE PROCESS may have an image open for writing.** One emulator
    mounting the same image as two devices is fine — it is one kernel, with one
    copy of the allocation bitmap. **Two emulator processes sharing one image are
    two kernels, each caching its own bitmap**, and each will allocate over the
    other's blocks. `Source, Flag`: this is the reasoning recorded in a
    collection's own image-locking tool rather than a corruption anyone here has
    reproduced, and the failure it predicts is the nastiest kind — a damaged
    volume discovered much later, with nothing to say when it happened.
    Until someone measures it, treat it as a rule and not a risk to weigh.

    The practical check before starting any harness: **`lsof` the image** and
    confirm no long-lived session — somebody's interactive shell, a REPL left
    running — is holding it. If one is, build a fresh image under another name
    and point the harness at that. Cheaper than the alternative, and it is the
    one hazard here whose symptom does not arrive while you are watching.
- **Prefer an RBF image over a host directory** for anything but the most
  basic testing. File permission attributes are enforced, and record locking
  works, only on the RBF path — on a host directory locking is deliberately
  absent, so a program that relies on it appears to work and silently
  doesn't: an explicit `SS_Lock` on a host file fails `E$UnkSvc`, on a host
  directory it reports success, and automatic record and EOF locking simply
  does not happen. `Source` (os9exec). `mount -k=<size> h0`…`hz` makes a blank image to start from.
  - **The trade is immediacy.** A host directory shows the guest whatever is on
    the host *now*, so an edit is live on the next open. An image is a snapshot:
    **a file you add to the source tree an image is built from does not exist
    inside the emulator until the image is rebuilt.** The symptom is
    `Error #000:216` / `E_PNNF` on a path you just created and can see on the
    host, which reads convincingly like a broken program or a corrupt image.
    `dir /dd/<the directory you added to>` settles it in seconds, and is worth
    making a reflex before debugging anything else. Build pipelines make this
    easy to forget twice: knowing the rule does not help if the build step is a
    separate command you did not run.
  - **A device you did not configure is not absent — it falls back**, and the
    fallback can be a different tree from the one you are editing. Setting only
    `OS9H0` leaves `/dd` pointing at whatever the start path supplies, so a file
    you changed under your own image is read from somewhere else entirely by any
    program that opens `/dd/...` — and most do, since `/dd` is the default data
    directory. Nothing warns you: the read succeeds, against the wrong file.
    `Live` (os9exec): a program reported `Unknown terminal type` against a
    termcap that had been corrected, because the correction was made under
    `OS9H0` while the program read `/dd/sys/termcap` from the original tree.
    **Set every device you intend to be the same image** (`OS9DISK=<img>
    OS9H0=<img>`), and when a program's behaviour disagrees with a file you just
    edited, confirm *which* file it read before concluding anything about the
    program. The crash dump's `Current` and `Execution` directory lines name
    real host paths and will tell you outright.
- Launch: `OS9DISK=/abs/path/disk ./os9exec /dd/CMDS/shell`
- macOS first run: `xattr -d com.apple.quarantine os9exec`
- **Pass absolute paths to `OS9DISK` and `OS9Hx`.** `OS9DISK=./dd` works
  (`Live` (os9exec), a host directory), but a *relative* `OS9Hx` splits down
  the middle: `Live` (os9exec), with `OS9H2=rel` naming a host directory,
  **opening a file on `/h2` works while `load /h2/<module>` fails with
  `E_PNNF` (216)**, which reads like a missing module rather than a path
  problem. An image named by a bare relative name (`OS9H2=rimg`) gives
  `E_PNNF` for everything; `./rimg` works. Absolute paths avoid all of it.
  - **Do not "tidy away" an `h0`…`hz` file or symlink** because it looks like a
    leftover of the magic-name scheme. It may be exactly what `OS9H0` names: a
    symlink is a perfectly ordinary target for the variable, and deleting one
    took out a working system here, because the variable pointed at the link
    rather than at the image behind it. Read the configuration that launches the
    emulator — the alias, script or `.zshrc` line — before deciding any path
    beside it is unused.
- **A device has to answer a *raw* open for `stat()` to work at all.**
  Microware's C library opens the device's identification sector (`/h1@`) and
  reads 256 bytes before it will describe any file on it — and a ported
  `bash` finds commands, and answers `[ -f ]`/`[ -x ]`, through `stat()`. So a device that
  refuses that raw open has no working command lookup even with `PATH`
  correct and the files plainly present. `Source` (os9exec, traced).
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
  normally run with. A lost line then reads as a missing feature — "this build
  has no `-k` option" from a `mount -?` listing that arrived short. If a claim
  is about what reaches the screen, reproduce it the way a user sees it: no
  `-r`, and compare against the `-r` run rather than trusting either alone.
- **`-r` also destroys any animation built from carriage returns**, `Live`
  (os9exec). Removing the pacing removes the only thing that made successive
  frames distinguishable in time, so a program that redraws a line per frame —
  a spinner, a counter, a progress bar, anything CR-per-frame — **collapses to
  its last frame**. Run without `-r` before describing what a program's output
  looks like, or you will document a still image as the whole behaviour.

## REPL harness: what it is, and two send modes

The harness is **`tools/os9repl.sh`** in the os9exec checkout — a tmux helper
that drives the emulator one command at a time and prints only the output that
command produced, instead of the whole scrollback. `tools/nitros9repl.sh` beside
it is the 6809 sibling (NitrOS-9 under XRoar plus DriveWire). Its own header
comment is the authority on the full command set; the shape of it is:

| Verb | Does |
|---|---|
| `start` | boot via `/dd/startup` — preloads the toolchain, then `tsmon` to `User name?:` |
| `send <cmd>` | send one command, wait for a prompt, print the new output |
| `key <keys…>` | raw keystrokes, no Enter (`Escape Enter Up Down Left Right`) |
| `snap [label]` | labelled snapshot of the pane |
| `vi <file> <seq>` | run `vi` and walk a key sequence, showing the screen at each step |
| `peek` | the whole current pane — the one to reach for after a crash |
| `stop` / `restart` | kill the session / stop, rebuild and start |

**Right after `start`, send the bare account name** (`send dog`, not
`login dog`): `tsmon` has already invoked `login`, so there is no login verb.
The prompts it treats as "ready" are the shell `$`, `for hlp)` ending a
debug-prompt line, `User name?:` and `Password:`.

**Set `OS9REPL_SESSION` when another session may be running.** It names the tmux
session (default `os9exec`), and two callers sharing one name will fight over
the same pane. `OS9REPL_TIMEOUT` is seconds per command (default 20 — raise it
for a compile), `OS9REPL_KEY_DELAY` the gap between keystrokes in `vi` mode. The
6809 script reads `NITROS9REPL_*` equivalents and adds `connect` (an interactive
session in your own terminal) and `server` (the DriveWire protocol log).

- **Gated `send`** — waits for a recognized prompt (shell `$`, debugger)
  before and after sending. **It goes silent inside any sub-program with
  its own prompt** (BASIC09's `B:`/`E:`, an editor, a custom login
  prompt): the send times out with zero pane change because the gate
  failed *before* sending. Switch to raw mode. **A program's own raw output
  can trigger the same desync**, `Live` (os9exec): a bare CR (no LF) written by a raw
  `write()` mid-output (stdio `printf` of `\r` arrives with a LF added, and
  does not do this)
  repositions the cursor to column 0 without clearing the line, so a genuine
  fresh prompt sits mid-line behind leftover text and the gate — which wants
  the prompt at line-start — times out even though the shell is fine.
  Recovery for both cases: one raw `key Enter` to force a blank prompt line,
  confirm, resend. The timed-out command was never sent, so nothing is lost.
  The same byte costs you output at the *end* of a run: a program whose last
  message ends in a bare CR has that line overwritten by the shell prompt that
  follows, so a capture shows `Cannot open modem path (/t0) - bash#` or
  `bash# EM port defined!` and reads as the program truncating itself.
  Appending `; echo ""` to the command moves the prompt to a fresh line and the
  message survives. `Live` (os9exec).

  **If EVERY line behaves that way, suspect `PD_ALF` rather than the program.**
  A single program ending its last message with a bare CR is the case above; a
  terminal where nothing advances a line is a path option that some earlier
  program cleared, and it can outlive that program. The CR:LF ratio of the raw
  stream settles which you have — see `common/memory-and-io.md`.
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

## Passing environment variables in: the `@` prefix

**A host variable reaches the emulated process only if its name starts with `@`.**
`Source` (os9exec, `prepParams` in `os9exec_nt.c`): the routine that builds the
guest's environment block walks the host `envp[]` and takes **only** entries
beginning with `@` — "OS-9 environment variables must start with a '@'".

`Live` (os9exec), one probe printing `getenv("TERM")`, run as the boot program:

```sh
env '@TERM=vt100' '@TERMCAP=…' os9exec /h0/CMDS/prog   # prog sees TERM=[vt100]
env  'TERM=vt100'               os9exec /h0/CMDS/prog   # prog sees TERM=[]
```

So the familiar `TERM=vt100 os9exec …` does nothing for the program inside, and
it fails **silently** — there is no warning that the variable was ignored. This
is the first thing to check when a program behaves as though a variable you
"set" is missing.

**What a non-crossing variable looks like inside is build-dependent, `Flag`.**
Measured here, `TERM` and `TERMCAP` arrive as **empty strings** — non-NULL
pointers to `""`. Measured on a different os9exec build (263b94a, started via
`bash`), `TERM` instead arrives as **`dumb`** while `TERMCAP`, `USER` and `HOME`
are genuinely **NULL**. Both were measured with probes that distinguish NULL from
empty, so this is a real difference between builds or invocations and not a
reporting artefact; which it is has not been established.

**The consequence survives the difference, and is the part to act on.** A guard
like

```c
if ((t = getenv("TERM")) == NULL) { fprintf(stderr, "TERM not defined\n"); exit(1); }
```

passes in *both* worlds, because the variable is present — just useless. The
program then proceeds with `""` or with `dumb`, and a curses or termcap program
reports either `Unknown terminal type ''` (empty name — the type never arrived)
or a failure naming a terminal you never chose. Neither is a fault in your
termcap file.

**`USER` and `HOME` being NULL matters for ports.** Programs that name the player
from `getenv("USER")` hand that pointer straight to `strncpy`. Supply a fallback
rather than assuming a login session set one.

**So: pass `@NAME=VALUE` on the host command line, or set the variable
in-universe** (`setenv` in a shell procedure, or a real login through
`SYS/login`, which is what exports `TERM`, `TERMCAP`, `USER` and `HOME` on a
configured disk).

## A working `getenv` is not evidence a library can see your variable

Two routes exist into a guest process's environment — the emulator's parameter
block (`@NAME=VALUE`, above) and the OS-9 shell's
`setenv` — and **they are not equivalent to every consumer.** `getenv` consults
both. A library that walks the environment block itself need not.

`Live` (os9exec), one program printing `getenv("TERM")` and then calling
`initscr()`, so nothing differs but how the variable was created:

| route | `getenv("TERM")` | `initscr()` |
|---|---|---|
| `@TERM=vt100` on the host command line, os9exec launching the program itself | `vt100` | `LINES=24 COLS=80` |
| `@TERM=vt100` on the host command line, program started from a shell procedure | `vt100` | `Unknown terminal type ''`, `LINES=0 COLS=0` |
| `setenv TERM vt100` in a shell procedure | `vt100` | `Unknown terminal type ''`, `LINES=0 COLS=0` |

Same binary, `getenv` agreeing in every row. The failing cases report an
**empty** name: curses is not failing to match `vt100`, it never sees a name.
And the `@` route fails too once Microware's shell is between os9exec and the
program, so on this rig what decides it is whether the curses program is the
process os9exec started, not how the variable was created. It is not every
shell: on the freeware rig, bash's `export TERM=vt100 TERMCAP=/dd/SYS/termcap`
in `SYS/login` reaches the curses and termcap programs that bash starts.

**This is one rig's curses, not a property of OS-9 curses, `Flag`.** On a second
rig the same comparison passes on all three routes — `@`-passed, `setenv`, and a
real `SYS/login` session — so the builds differ. Two candidate explanations for
the split were tested here and **eliminated**: forking the program by absolute
path versus by bare name makes no difference, and `TERMCAP` holding a file path
versus the entry string makes no difference. On the rig that fails, what moves
it is whether the program is the first process or a shell's child.

**What to take from it regardless of which build you have:**

- **Do not use `getenv` to prove a variable reached a library.** It is the one
  check that cannot distinguish these routes, which makes it worthless for
  exactly this fault and reassuring while you chase the wrong thing.
- **If a terminal library reports an empty name**, try passing the variable as
  `@TERM=`/`@TERMCAP=` and letting os9exec launch the program directly, with
  no shell between, before suspecting your termcap. It needs no login session:

```sh
env '@TERM=vt100' '@TERMCAP=/dd/SYS/termcap' os9exec /h0/CMDS/prog
```

  `TERMCAP` may hold a path or the entry itself; both work where this works.

## Batch-testing binaries

Each candidate can be its own boot program in a fresh instance — no shell
needed:

```
gtimeout 5 env OS9DISK=/abs/path/disk ./os9exec /dd/CMDS/<name> </dev/null 2>&1
```

**`gtimeout`, not `timeout`, on macOS** — the GNU coreutils build installs under
the `g` prefix there (`/opt/local/bin/gtimeout` from MacPorts, likewise
Homebrew), and a bare `timeout` does not exist. On Linux it is `timeout`. Harness
code that assumes the unprefixed name dies before it runs a single case, so pick
one and use it everywhere; the examples in this file all say `gtimeout`.

`</dev/null` is explicit and harmless (a redirected host stdin returns
end-of-file on its own, so a stdin-reader does not hang without it); the
timeout is still mandatory.

This tests **"loads and starts"** and nothing more — at that narrow question a
usage message is a pass, and it is the right signal for auditing a disk full of
binaries, far faster than driving a shell. **Do not carry it further than that.**
A usage line proves argument parsing ran and says nothing about whether the
program's I/O works; for the case where that distinction bites hardest, and the
sounder test, see the `cio` link-mode pitfall in `c/os9-c-cheatsheet.md`.

**Drive a program the way a person would, not the way that is easiest to
capture.** How you invoke it decides which defects can appear at all, and no
single convenient route exposes them all — three measured classes, each
invisible under a different one:

| defect | hidden by | exposed by |
|---|---|---|
| `putchar`/`putc` with a side-effecting argument (`c/os9-clib-reference.md`) | redirect to a **file** | a **pipe** or a terminal |
| a scanner whose `freopen(…, yyin)` did nothing (`c/os9-c-cheatsheet.md`) | a **pipe** — it was going to read `stdin` anyway | a **named file** argument |
| a raw `write()` whose line feeds the terminal never adds | a **file** — the bytes are exactly as written | a **terminal** |

Note that the first two point opposite ways: the pipe that reveals one conceals
the other. **So "always capture through a pipe" is not the rule** — the rule is
that a harness redirecting everything to files and comparing checksums will
pronounce all three classes clean, and a harness that only ever pipes will miss
the second. Exercise the real invocations: a named file argument, a pipe, and at
least a spot-check on a terminal. `Live` (os9exec), all three.

## An internal command can BE the boot program — no shell needed

`Live` (os9exec). os9exec's own built-ins run as the boot program, so a disk
image can be built and populated before any shell or SDK is available:

```
os9exec mount -k=360k h7      # a real RBF image at <startPath>/h7
os9exec makdir /h7/SCRATCH    # ...and directories inside it
os9exec dir /h7               # SCRATCH
```

This is the route for CI and for a fresh clone with no system disk. `mount -k`
streams the image (head plus a zero tail) rather than buffering it, so size is
bounded by host disk, not by the 68k arena — 125 MB builds in well under a
second. `mount -r`, a genuine RAM disk, IS bounded by the arena and says so.

**The RAM-disk form wants the size on the option and the device as a path** —
`mount -r=256k /r0`. `Live` (os9exec): `mount -r r0` answers `can't mount
device ""` and `mount -r=256k r0` answers `can't mount device "r0"`; only the
leading slash works. `mount -?` also lists `-n=<bytes>` sector size,
`-c=<num>` cluster size and `-d=<device>` (a RAM disk copied from a device).
Worth knowing because a good deal of freeware wants a `/r0` to scribble on.

**`mount <image> hX` attaches an existing RBF image while the emulator runs**,
`Live` (os9exec). The image may be named by an OS-9 path (`mount /h5/disk.dsk
hc`, the file sitting on a host-directory device), by a name relative to the
current directory, or by a host path. `-w` mounts it write-protected, so a
write gives `E_WP` (242). A device name already in use is refused with `/h5 is
already a device` and `E_DEVBSY` (250). It is the alternative to naming the
image with `OS9Hx` at startup when you only find out mid-session that you need it.

**`OS9DISK` CAN point at an RBF image** — `Live` (os9exec), measured
on macOS with `env -i` and from an unrelated
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

## Batch-driving a whole session: a procedure file, never a pipe

For unattended multi-command work (building an image, populating a disk),
pass the shell a **procedure file** — the mechanism `os9repl.sh` itself uses
to boot (`shell /h0/startup`):

```
gtimeout 60 env OS9DISK=/abs/path/image OS9H1=/abs/workdir OS9STOP=1 \
    ./os9exec shell /h1/<proc> </dev/null 2>&1
```

`/h1` is whatever `OS9H1` names — give it an **absolute path** to the directory
holding the procedure file, rather than relying on a magic `h1` beside the
binary, for the reasons under "Launching and disks" above. The traps, all
`Live` (os9exec), the first two silent:

- **The procedure file must be CR-only.** With LF endings OS-9 sees one
  enormous line: **its first command runs with the rest of the file as its
  arguments** (`makdir A` LF `makdir B` created both directories; any other
  commands in the file became more directory names). With `-nx` on the first
  line the shell instead echoes the line and prints `^syntax error`. Generate
  with `tr '\n' '\r'`.
- **And commands fed on HOST stdin must be the opposite — LF-terminated.**
  `Live` (os9exec): `./os9exec shell < cmds`, or the same commands through a
  pipe, needs `\n` endings. A CR-only stdin file is echoed as **one line** with
  only the first command taking effect — typically surfacing as a complaint from
  that first command alone (`setenv requires two arguments`) while everything
  after it silently never runs.

  **The two rules are opposites and it is the same session that needs both**: a
  file named as an *argument* is read by OS-9 and wants CR; bytes arriving on
  *stdin* cross the host boundary and want LF. Which rule applies is decided by
  how the commands reach the shell, not by what the file is called — so a
  generator that emits one ending for both uses is wrong half the time.
- Piping the same commands into an interactive `shell` works too (`Live`
  (os9exec)): a redirected or piped host stdin delivers end-of-file, so the
  shell runs the piped commands and then exits. The procedure file is still
  the tidier route — it gives CR-ending control and a named artifact.
- **A utility that prompts devours the rest of the file.** `copy` onto an
  existing destination reports `Error #000:218` and then asks `Overwrite
  (yes/no/all/quit)?`. `Live` (os9exec): the following procedure lines are
  read as answers to that prompt instead of being run — one character at a
  time, re-prompting after each one that is not an answer — and when the file
  runs out it gives up. Every line after the `copy` is gone without a word,
  and a stray `y` among them answers *yes*, so the overwrite can happen
  anyway. Give `copy` an explicit `-r` (`-f` for a write-protected
  destination) so it never asks. Abort-on-error does *not* rescue this case:
  in a procedure file the prompt is reached before the failure can end the run,
  so the error is reported, the overwrite still happens, and the lines that
  answered it are gone.

- **The first failure ends the run, and nothing announces that it did.** The
  shell's `-x` (abort on error) is on by default, so a procedure file stops at
  its first failing command: that command's own error prints, the remaining
  lines never execute, and the run then exits looking exactly like a completed
  one. A four-line file whose second command failed produced line one's output,
  the error, and nothing further. Use `-nx` when a batch must finish regardless —
  and never read "no further errors" as "the rest ran".
  - **`-nx` goes on the first line of the procedure file, not on the command
    line.** `Live` (os9exec): `os9exec shell -nx /h6/proc` prints
    `^syntax error` and runs nothing at all — the shell is parsing `-nx` as the
    thing to execute. Put `-nx` as the file's own first line and invoke it plainly
    with `os9exec shell /h6/proc`. Worth knowing because the failing spelling is
    the one a Unix habit reaches for, and its error names syntax rather than the
    option.

- **`sleep` counts ticks unless given `-s`.** `sleep 5` in a procedure file
  meant to wait for a background server is gone in a twentieth of a second, and
  the run ends before anything it was waiting for happens. Write `sleep -s 5`.
  See `sleep` in `utility-usage.md`.

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
   endings natively. Needs a correct `TERM`/termcap — and for this era
   **`vt100` is usually the right answer, not a modern value**. `Live`
   (os9exec): under `TERM=xterm-256color` (a valid entry in the disk's own
   termcap) `sc` refuses to start at all with
   `'xterm-256color': Unknown terminal type`, and `backgammon` draws its top
   rule and nothing else — no cursor-addressed walls or pieces. `TERM=vt100`
   and both render fully. Programs that carry their own compiled termcap, or
   that simply assume a vt100, do not all accept a modern name. Set it before
   blaming the program or the emulator. If a correct `vt100` still draws
   `Unknown terminal type`, two further causes sit behind that one message, and
   the quotes tell them apart: a **named** type means the entry was not matched,
   so suspect the reader that skips any entry lacking a two-character first
   field (below); an **empty** `''` means the name never reached the library at
   all — check the `@` prefix above, and note that a `setenv`-created variable
   is visible to `getenv` and invisible to curses
   (`c/os9-clib-reference.md`). Basic loop: `i`,
   type, ESC, `:wq`.
3. **Host-side editing + `flip`** — host-native directories only (a file
   inside an RBF image has no host file to touch). `flip -m` → CR-only
   (OS-9), `flip -u` → LF (Unix), `flip -t` reports current state. Best
   route for large sources; the file must end up CR-only or the compiler
   reads it as one giant line. `flip -m` on a file that is already CR-only
   leaves it unchanged, so reflipping is safe.

**tmux eats a trailing semicolon**: `send-keys` treats a final `;` as its
own separator even with `-l`, so a typed C line arrives without its
semicolon — a baffling syntax error on a line that looks correct in the
pane. Escape it (`\;`) or don't end the send with `;`.

### The CR rule fails differently depending on what the file is FOR

That OS-9 text is CR-terminated is easy to remember. What catches people is
that an LF file announces itself in three different ways, and only the first
is obvious. `Live` (os9exec), all three met in one evening:

1. **Source (`.c`, `.h`) — loud, but not always in the same way.** The whole
   file is one line, and what that does depends on how long the file is.
   Reported for real sources: `**** source line too long ****` from `cpp`, on
   every file at once — hard to miss, easy to misread as a defect in the code.
   Measured here on a *short* LF file, `cpp` said **nothing at all** and the
   failure surfaced at link time as `Symbol 'main' unresolved`, referenced by
   `cstart_a` — because with everything on one line the leading `#include`
   directive swallows the rest of it, so no `main` is ever compiled. That form
   is the more misleading of the two: it points at your entry point, not at
   your line endings. A long enough one-line file has also been seen to hang
   `cpp` outright rather than diagnose anything. `Live` (os9exec). **A silent
   `cpp` death is not diagnostic of line endings on its own** — an over-long
   *logical* line kills it the same way, including one you believed you had
   disabled inside `#if 0` (`c/os9-c-cheatsheet.md`). Both are the same
   underlying limit reached from opposite directions; check line endings first
   because it is cheaper, then the line.
2. **Data read at run time — silent.** The program builds, starts, and reads
   records that are not delimited the way it expects. A word list, a
   dictionary, a grammar, a score file. Nothing reports anything.
3. **Data `#include`d as source — the trap.** Files that are data by name and
   extension but source by use: `monop` keeps its board, properties and cards
   in `.dat` files that `monop.def` pulls in as C initialisers, so an LF
   `.dat` kills the *build*, with `cpp` dying exactly as it would on a `.c`.
   Convert "the source" and leave "the data" alone and you have broken the
   build in a file you are not looking at.

**The handling that avoids all three: unpack inside the OS-9 universe.** A
well-stocked disk carries `unshar`, `tar`, `ar`, `lha`, `gzip`, `compress`,
`unzip`, `zip`, `arc` and `zoo`; every file an OS-9 tool writes is
CR-terminated by construction, whatever its extension or role. Verified by
extracting one archive both ways — the disk's own `unshar` produced files
byte-identical to a host-side unpack, without the conversion step that can be
got wrong.

That leaves exactly one host-side step, and it is transport: a **text** archive
has to arrive on the disk as OS-9 text. Skip it and OS-9's `unshar` cannot read
it either — it answers `No shell commands in <file>`, which is not an obvious
way of saying "wrong line endings". Binary archives (`.lzh`, `.Z`, `.tar`)
transport unconverted; converting one corrupts it.

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
- **Two emulators compiling in one directory clobber each other.** `cc`
  names its intermediates after its own process ID (`ctmp.000004.r`), and in
  a fresh batch run `cc` gets the same PID every time, so parallel runs
  sharing one data directory overwrite each other's temporaries. `Live`
  (os9exec). Give each run its own directory, or run them one at a time.

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
- **An intermittent `**** Can't install trap handler ****` / `Error #000:216`
  while `mdir` shows the handler resident** is an emulator-level race,
  timing-sensitive and historically correlated with baud-rate pacing. Restart
  the os9exec session; if it recurs, it is os9exec, not your program. The
  OS-9 causes of that banner are triaged in `basic09/pack-and-runb.md`.
- A named pipe (`/pipe/<name>`) makes good read-once scratch storage — no
  cleanup needed.

## The cio trap handler divides archived binaries

Most archived OS-9/68k programs were linked against Microware's
proprietary `cio` C-I/O trap handler; on a disk without it they die
immediately with `**** Can't install trap handler **** / **** cio ****`.

- **Classify by running it, not by reading the binary** — `Live` (os9exec).
  Run each program against an image with `cio`, `csl`, `csl020`, `math` and
  `math881` removed, and match the banner, which names the handler that could
  not be installed (`cio`, `csl`, or a program's own, such as `Graph`).
  Searching the file for the string `cio` is a proxy that can fail in both
  directions — a name can appear without the module being needed, and a
  program can need it without the name appearing where a search looks. Only
  `cio`/`csl` are fatal — `math`/`math881` are the optional floating-point
  handlers and referencing one is harmless.
- A statically linked "cio-free" build of the same utility is noticeably
  larger; prefer it when both exist.
- **Linking the SDK's `cio` library against a mismatched `cio` module
  silently corrupts I/O** rather than failing — the selector numbers differ.
  Build trap-free (`-qm`) for anything installed; see the `cio` selector
  pitfall in `c/os9-c-cheatsheet.md`.
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

## Existing freeware is a development resource, not just software to run

Worth knowing before you write anything: a well-stocked OS-9 disk carries a
large body of period freeware, and **source frequently ships beside the binary**.
Two uses that are not obvious:

- **Read a working program instead of deriving a convention.** When a manual
  gives you a register contract but no idiom, a program from the era that already
  does the thing is often the faster answer — and it is evidence that the
  sequence works, which the manual alone is not.
- **A period-built binary is a control.** This is the more valuable one. When
  something you built misbehaves, a program built by its author in the 1980s or
  90s, run on the same disk in the same shell, differs from yours in exactly one
  way: who compiled it. That comparison is what narrowed `system()` from "this
  call is broken" to "our builds differ from period builds" (see
  `c/os9-clib-reference.md`), and it is the cheapest way to find out whether a
  fault is yours or the system's.

The corollary is worth stating because it has bitten: **a program failing is not
evidence the system is at fault until a period binary fails the same way.** Most
of the C-toolchain traps in these references — link mode, line endings, buffering
— produce programs that are broken by how they were built, on a disk where
everything around them works.

**Check that the binary and the source beside it are the same program.** Both
uses above assume they are, and an archive is not obliged to honour that: a
directory can hold one edition's source and a different edition's binary, in
which case reading the source tells you nothing about the binary, and the binary
is not a control for anything you build from that source. `Live` (os9exec): a
shipped `ispell` faulted at its first dictionary lookup while a build from the
source next to it worked — different editions, and neither the emulator nor the
data was at fault. **The cheapest tell is the usage text**: run the binary with
no arguments and compare its usage line, option letters and version string
against the source. A mismatch settles it in seconds and costs nothing to check
before you spend an evening on the wrong question.

## When `vt100` is right and the program still says "Unknown terminal type"

A family of ported programs carries its own termcap reader, and **it will not
look at a modern termcap entry** — so a correct `TERM` and a termcap file that
plainly contains `vt100` are not enough, and the `TERM=vt100` advice above does
not rescue it. Identify the family from the binary:

```sh
strings -a <program> | grep -E '/dd/sys/termcap|%s/sys/termcap'
```

Both strings together mean this reader. With `TERMCAP` unset it tries
`/dd/sys/termcap` then `$HOME/sys/termcap`; set to a path it opens that; set to
anything not starting with `/` it treats the value itself as the entry.

**First rule out the file you think it is reading.** A device you did not
configure falls back to another tree, so a termcap you corrected under `OS9H0`
is not what a program opening `/dd/sys/termcap` sees — that trap is described
under "Launching and disks" above, and it produces this identical message. Once
the program is provably reading your file, read on.

**The cause is the entry's first field.** The reader skips a line unless its
**third byte is `|`** — the older two-character alias form, `d0|vt100:...` —
and it skips lines beginning `#` as comments. A modern entry whose first field
is longer than two characters is skipped outright:

```
xterm-256color|xterm|vt100|xterm with 256 colors:     skipped: byte 2 is 'e'
d0|vt100:bs:co#80:li#24:cl=\E[H\E[J:...              matched
```

`vt100` present only as a later alias is never reached, because the line
carrying it is discarded before any alias is examined.

**The fix is to give the entry a two-character alias.** `Live` (os9exec): with
`TERMCAP` pointing at a file holding `d0|vt100:...`, two programs of this family
that had answered `'vt100': Unknown terminal type` against a stock termcap both
got past `tgetent` — one drew its screen correctly, the other proceeded into
terminal setup and failed there for an unrelated reason. Same file, same
programs, only the first field changed.

**The alternative is to put the entry in `TERMCAP` directly**, which needs no
termcap file at all and is the better answer when you do not own the file:

```sh
TERMCAP='vt100|dec vt100:bs:co#80:li#24:cl=\E[H\E[J:...'
```

The value is used as the entry, so the two-character alias is not required on
this route — the first field is only read when scanning lines of a file.

Two hazards, both measured `Live` (os9exec) in one build, and both on the string
route rather than the file route:

- **The copy that reads the value stops only on a carriage return** — no length
  limit and no NUL check. An environment variable is NUL-terminated, so that
  build runs away through memory until it dies. A program that aborts *after*
  you supply a working `TERMCAP` string may be failing this way; give that one a
  file instead, where the line's terminator stops the copy.
- **The destination is a 128-byte buffer** while the line buffer is 256, so an
  entry over about 127 bytes overruns it. Keep entries short on either route.

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

**Some disks' `sh` cannot fork an absolute pathname at all** — the workaround is
`load` the module first, then fork it by bare name. That is a property of the
shell on a given disk rather than of the emulator: `Live` (os9exec), one disk
requires it while another forks bare names and absolute paths alike. Worth
trying before concluding a program is unrunnable, and worth not mistaking for an
emulator difference when two setups disagree.
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

  **Traversal above the root is confined**, `Live` (os9exec), **on
  host-directory devices** — those configured through `OS9DISK`/`OS9Hx` pointing
  at a directory, and those created by `mount -k=0`, which also makes one:
  `list ../outside` and `list ../../../../outside` both give `E_PNNF` while a
  read inside the device works. The four-level climb really did climb four
  levels: on a host directory a relative pathlist is joined to an absolute path
  and resolved host-side (see the climbing section in
  `common/unix-differences.md`). Naming the device type
  matters here, because `OS9DISK`/`OS9Hx` can equally name an image. The one exception is NESTED device
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

**Name lookup on a host directory is not what OS-9 does**, `Live` (os9exec) and
`Source` (its own `CaseSens` path lookup). The exact host name is tried first;
failing that, the directory is scanned and the **first** entry whose *shown* name
matches wins — where "shown" means cut to 28 characters with spaces rendered as `_`, compared **case-insensitively**. Consequences, none of them OS-9 semantics:

- **Case-insensitive even on Linux.** `list /h5/sub/file.txt` opens `Sub/File.txt`
  on a case-sensitive host filesystem. Code that relies on case to distinguish
  two files will not behave here as it does on the host.
- **A host name longer than the cut opens by its cut name**, and its *full*
  name gives `E_PNNF` — the reverse of the intuition that the full name is the
  real one.
- **Two host names that agree up to the cut are indistinguishable**:
  `dir` lists both identically and only the one earlier in host order can be
  opened. The other is unreachable without renaming it on the host.
- **A name containing spaces opens by its `_` spelling** — unless a file really
  spelt with `_` also exists, which then wins and shadows it.
- **`makdir sub` beside an existing `Sub` fails `E_CEF`** on Linux, because the
  lookup finds `Sub` first.

**Line endings are not translated on a host directory.** `Live` (os9exec):
nothing converts LF, and `I$ReadLn` ends only at CR, so a three-line LF file
reads as a single line — `linecount` reports **0 lines** for it. Editing a file
host-side therefore leaves it unreadable to OS-9 line I/O unless you convert it
(see the CR-rule section above); the device being a plain host directory does not
buy you host line endings.

**`chx` with no argument prints nothing on a host directory**, where on an
RBF image it prints `Error #000:214 (E_FNA)`; either way the execution
directory is unchanged. `Live` (os9exec).

**Host-side modes the emulator chooses**, `Live` (os9exec): `makdir` creates a
directory at `0700`, and a shell `>` redirect creates a file at `0600`. A
super-user `I$Create` on a host directory always keeps owner **read**
and never write — a deliberate choice, and RBF is unchanged.

**Fuller treatment**: the emulator's own `docs/host-drives.md`
([os9exec](https://github.com/peacedudes/os9exec)) is a guide to how host drives
work and how they differ from RBF, and goes further than this section needs to.

**Host links inside a device root**, `Live` (os9exec): hard links behave as
ordinary files (deleting one name leaves the other's content), and a symlink
that stays inside the device resolves normally. **A symlink pointing outside
the device is refused**: `dir`, `list` or `chd` through it gives `E_PNNF`, as
does `deldir`, which therefore deletes nothing. `del` of the link itself fails
with `E_BPNAM` and leaves it in place, so remove such links on the host.

`deldir -q` on an in-device link to a directory deletes everything inside the
target — OS-9 has no link concept, so it cannot tell — and then removes the
link. The target directory itself stays, empty. Symlink cycles can crash
the emulator after ~40–60 hops.

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

A missing call is not a crash. `F$SSpd`, `F$Trans` and `F$UAcct` return a
clean `E$UNKSVC` (208) and change nothing; `F$SchBit`, `F$AllBit` and
`F$DelBit` are implemented. `Live` (os9exec). Of the three, only `F$SSpd` is
one the v2.4 manual itself marks "currently not implemented" (`Manual`). A
program that tests the carry survives; one that does not may read 208 as its
own failure.

`F$STime` is accepted and does not touch the host clock. `Live` (os9exec).

**No installed file manager or device driver ever runs.** os9exec serves
every path from its own host-side layer, dispatched by path prefix; its
`I$Attach` never allocates driver static storage or calls `Init`, and `iniz`
is not implemented. A correctly assembled, CRC-valid `FlMgr` or `Drivr`
therefore loads and is never invoked at any entry point. Module *format* can
still be built and checked here; entry-point conventions need OS-9 itself.
`Source` (os9exec).

**The kernel process has no real module.** It runs code built into the
emulator and reports `P$PModul` = 0, so a monitor that follows that pointer
to a module header (`devprc -a`, `top`, `sysmon`, `aprocs`) reads the zeroed
low page, finds no header, and fails cleanly. `Live` (os9exec).

A hand-built trap module with no init data still needs an init table:
`_midata`/`_midref` at 0 are not read as "no table" — os9exec parses a table
at that offset unconditionally, so the module needs a real empty one there
(dOff=0, cnt=0, then two 0-terminators) or the load fails `E$BMID`. `Source`
(os9exec).

Unmodelled **system globals** answer differently. A `F$GetSys`/`F$SetSys`
read of an offset os9exec does not keep returns 0, silently; the note
`# F$SetSys: unimplemented <hex>` appears only in the `-d` trace (`Source`,
os9exec). Usually harmless. `D_SPUMem` ($3D8) is the one worth recognising:
every Microware-C start-up reads it to detect a System Security Module, and 0
is answered deliberately because that is what a machine without an SSM
reports — see `kernel-internals.md` in `os9-systems-dev`.

**`top` shows its header and no process rows.** `Live` (os9exec), with
`@TERM=vt100`: it redraws the header until stopped and lists nothing. It asks
for PID 0, gets the documented `E$IPrcID` (224) refusal and ignores the
carry, so it reads a buffer nothing filled — `top`'s own bug, which what that
buffer happens to hold turns into an empty list or worse.

**There are no device descriptor modules, by design** — os9exec does not
provide them. It mounts `/dd`, `/hN` and `/term` without them: `imdir` lists only `OS9exec`, `init`, a built-in
`socket` descriptor and what you have loaded. So anything that *links* a
descriptor by name to read or change its options fails with
`Error #000:221 (E_MNF)`, although the device itself works — Microware's own
`xmode /term` gives `xmode: can't link "term"`, and `link dd` fails the same
way. `Live` (os9exec). Tools that go through the descriptor rather than an
open path (`xmode`, and third-party ones such as `dmode`) often exit 221
with little else said. To inspect a descriptor, `load` one from the SDK's
`CMDS/BOOTOBJS` (`r0`, `dd_r0` and others); it is then resident and linkable.

**The emulator's own diagnostics share the running program's stderr.** They
carry a `# ` prefix — `# No more memory:` from the allocator, for one — and go
to that path rather than a channel of their own, so they interleave with
guest output. `2>/nil` is what separates the two when capturing. `Live`
(os9exec).

The `-d` syscall trace (below) lands on the same stderr, which matters whenever
stderr belongs to something else — under a network login it goes down the
connection to the client. `idbg -o <path>` typed in the guest moves it to a
file instead, e.g. `idbg -o /h5/trc -d 2` with `OS9H5` naming a scratch
directory; the file is appended to, and its lines end in CR. `Source`
(os9exec: `Change_DbgPath`), `Live` (os9exec).

## Where os9exec departs from the manuals

Known places where os9exec, as a stand-in, behaves differently from the
Microware manual, each measured on os9exec V4.10 against the manual it
differs from. These are facts about the emulator, not about OS-9: the manual
remains the specification, and the reference pages state its behaviour and
point here. Code that passes on os9exec but relies
on one of these will behave differently on real equipment, and vice versa.
All `Live` (os9exec) unless tagged otherwise.

- **`F$CpyMem` range-checks its source.** The manual: "you can view any
  memory in the system". Here sources `0`, `$100`, `$10000`, `$01000000` and
  the boot-resident shell's header all gave `E$BPAddr` (210); a module the
  caller loaded could be read. os9exec models an SPU-protected system.
- **GetStat SS_Size on a pipe answers `E$UnkSvc`.** The manual reads both
  ways here (`68k/syscall-reference.md`); os9exec follows one reading, the
  one under which `less` pages piped input to its end (os9exec's v4.1.0 release notes;
  not measured here).
- **The default pipe buffer is 4096 bytes**, where the manual gives 90
  (`common/ipc.md`); 90 is os9exec's minimum. A C program writing 256-byte
  chunks to a pipe with no reader had exactly 16 accepted before the write
  failed. So a named-pipe writer with no reader blocks, and an unnamed-pipe
  writer gets `E_WRITE`, only after about 4 KB — code that leans on the larger
  buffer will stall or fail sooner on real equipment.
- **Console paths do not enforce `E$BMode` (203).** stdin, stdout and stderr
  share one descriptor, so writing to a console path opened read-only, or the
  reverse, passes silently. Disk files enforce it both ways, so a working
  console test says nothing about files.
- **`F$STrap` installs only vectors 2–8.** The manual makes the FPCP
  exceptions 48–54 catchable on a 68020/68030 (`68k/os9-68k-assembly.md`), and
  os9exec emulates a 68020, but a handler registered for them is accepted and
  never fires.
- **`F$PrsNam` also accepts `{` and `}`** as element characters, beyond the
  manual's `A-Z a-z 0-9 . _ $` — a deliberate convenience for MPW shell
  variables. `Source, Flag`. It is more permissive, so it cannot produce a
  spurious `E$BNam`.
- **`F$PErr` with `d0.w=0` prints a named message**, `Error #nnn:nnn (E_NAME)
  description`, where a stock system prints a bare `ERROR #mmm.nnn` — and in
  the `E_` spelling, against the `E$` the DEFS declare. A code missing from its
  table prints `(E_???) <<unknown error code>>`, a useful tell that the number
  is **not** an OS-9 kernel error; that is how 68k BASIC09's own error 43 was
  identified.

## Zeroed emulator memory can make someone else's bug look like the emulator's

This is the failure mode to hold in mind whenever os9exec looks at fault, and it
is the mirror of the rule that a `Live` claim is evidence about a
reimplementation: the emulator's memory is more uniform than a real machine's,
so a third-party bug may not present the way it would on real hardware.

**os9exec `calloc`s the guest arena** (`Source`: `memstuff.c` allocates
`emul_base` with `calloc`, and `fcalls.c` carries a comment to the same effect),
so unwritten guest memory is reliably zero. A program that scans past the end of
a buffer therefore finds neither a terminator nor accidental garbage that happens
to match — it reads zeros, for as long as you let it. On real hardware the same
code would more likely fault, or stop by luck on whatever was lying in memory.

A worked instance, `Live` (os9exec): a de-ANSIfier with an unbounded scan loop
(see `c/kandr-vs-ansi.md`) spun at 100% CPU and never returned. It was first
reported as an os9exec defect, on two pieces of circumstantial evidence that both
dissolved:

- **Output stopped at exactly 20,480 bytes.** The roundness of the number looked
  like a write ceiling in the emulator. It was the last full stdio buffer flushed
  before the program stopped writing anything at all — an artefact of buffering,
  not a limit.
- **The hang was perfectly reproducible** and the program was well known, so the
  new variable in the system looked like the likely cause. The actual new
  variable was a zeroed arena turning an out-of-bounds read into an infinite one.

So: a round number in a byte count is usually a buffer boundary, not a ceiling;
and a "deterministic emulator bug" in a long-established program is worth one look
at that program's bounds checking before it is filed.

## Stopping a runaway program

- **Ctrl-C** depends on whether the child has written to the terminal, as
  the manual describes (`Manual`, *Using Professional OS-9*; `Live`
  (os9exec)). One that has not — `sleep -s 20` — is moved to the background:
  the shell prints `+3` and prompts, and the child runs on. One that has
  written receives interrupt signal 3 and, with no intercept handler, dies
  with `Error #000:003 (S_Intrpt) User interrupt`. So Ctrl-C does not stop a
  silent computation, and does kill a chatty one.
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
`idbg -d=2 -o=/h5/trc` (the `=` form) works the same. **A bare number is not
a mask**: `idbg 0002` opens the interactive debug menu (os9exec's release
notes), which in a procedure file waits for input.

**Finding a stray write: `-W`.** Launching `os9exec -W …` makes a user-state
write outside the process's own memory — its data area, the blocks it
requested with `F$SRqMem`, and loaded modules — a bus error, and prints where
it happened. It is off by default. `Live` (os9exec): a program writing through
a plain `(a6)` (32 KB past its data; see `68k/os9-68k-assembly.md`) ran to
completion silently without it, and with it stopped at the write:

```
# -W: pid=4 wrote 4 bytes at $00059E40, outside its own memory (pc=$00051D96)
Error #000:102 (E_BUSERR) bus error TRAP 2 occurred
```

Real OS-9 does this only with an SSM fitted, so this is the tool for "my
program corrupts something" or "another program fails after mine ran" when
the hardware you target has none.

**`-d 2`'s `<<<` return lines can name the wrong call.** The entry (`>>>`)
and return (`<<<`) lines are printed from a single per-process current-call
field, read again at return time rather than saved at entry (`Source`,
os9exec: `cp->func`, `debug_return`). Anything that dispatches a nested call
in between overwrites it, so the outer call's return is attributed to the
inner one. Trust `>>>` lines for what was called; pair a return with its
entry by position, not by the name on it, and do not conclude a call
returned a value it never returned.

## Reading a process crash dump

When a process dies, os9exec prints a dump: exit code, open paths, last
syscall, registers, the faulting instruction with the bytes at `PC`, and the
static-memory range. Three things about it are easy to misread.

**`Last syscall` is the last one the process *made*, not where it died.**
It is a latched field, so a program that faults in a stretch of pure
computation still shows whatever it called before entering it — which can be
thousands of instructions and an unrelated subsystem away. `Live` (os9exec): a
program that ran away inside a memory-copy loop reported `Last syscall: F$ID
(0x000c)`, and `F$ID` had nothing to do with the fault. **Never treat that line
as the fault's location or cause** without independent evidence; it is a
starting point for "what had it been doing", not a pointer to the bug.

**`PC` is an absolute emulated address; the module is loaded somewhere.** To
get the module-relative offset — the one your disassembly is numbered in —
use the bytes the dump prints on the `Executing:` line:

1. Take the byte string shown at `PC` (e.g. `18d0 206f 000c 700d b010`).
2. Search the module file for that byte sequence; a run of 10-12 bytes is
   normally unique.
3. `base = PC - offset_of_match`. Sanity-check it: `base + M$Size` should land
   just below the static range the dump reports.

Then disassemble the file at that offset and you are looking at the
instruction that faulted. This also settles a question worth settling early —
**whether the fault is inside the module at all.** An address that matches
nothing in the image means execution left the program, which is a different
class of bug from one that has a line number.

**A crash that comes and goes with how busy memory is suggests a one-byte
stack overrun into a saved register's high byte.** 68k is big-endian, so the
first byte past a stack buffer is the high byte of whatever the function
saved above it — typically the frame pointer. A string one character too long
for its buffer writes its NUL there. While the program sits below 16 MB that
byte is already `$00` and nothing happens; above 16 MB the damaged pointer
sends `UNLK`/`RTS` into low memory, and the process dies with an illegal
instruction wherever execution stops — a `PC` that matches nothing in the
module. The dump's tell is `SP`: it points into the process's static range but with
bit 24 cleared, i.e. 16 MB below where it belongs. A 68000 or 68010 ignores the top address byte, so it never shows
there; a 68020 or later with more than 16 MB shows it, and so does os9exec,
which emulates a 68020 with a large arena. To reproduce, push the program's
memory high: `sleep -s 12 #20000k &` at the shell holds 20 MB while you run
it. `Live` (os9exec): the collection's `bash` 1.12 builds `BASH_VERSION` with
`sprintf` into a 12-byte buffer and writes 13; it crashed 2 of 2 with memory
pushed high, and a copy one character shorter ran 3 of 3.

**A dump hinting at a corrupted module is not evidence of one.** Check the file
with `ident`, which reports the module CRC and the header parity separately; a
module that reports `Good CRC` and `Good parity` is intact, whatever a
post-mortem probe of live memory made of it.

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
- Both behaviours (`sc` addresses, `gs` stepping) are attributed to the
  `debug` binary itself rather than to os9exec; neither has been checked on
  real hardware.

---
Everything above is `Live` (os9exec) unless tagged otherwise inline —
a few emulator-internal details are `Source` (read from os9exec's own C
rather than observed), and any `Manual` claim says so.
