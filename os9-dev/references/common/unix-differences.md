# OS-9 for people who already know Unix

Delta document, not a tutorial — ordered by how badly a wrong Unix
assumption bites, not by topic. Tier 3 (bottom) is a flat 1:1 lookup table;
skim once. Spend attention on Tier 1.

Applies OS-9-wide, not just 68k: the shell/directory/pipe behaviors below
(chd/chx split, `!` not `|`, CR line endings, ESC-exit, the control-key
inversions) were independently cross-referenced against multiple 6809
primary sources and confirmed identical. Where 6809 genuinely differs
(register conventions, `int` width, module header encoding), that's a
Tier 2/3 item, not a Tier 1 one — the model-level breaks from Unix are the
same regardless of which OS-9 architecture you're on.

---

## Tier 1 — model breaks (wrong, not just slow, if you assume Unix)

### 1. Two current directories, not one

Unix has one cwd. OS-9 has two:

| | Command | Governs |
|---|---|---|
| **Data directory** | `chd` | Relative *data* file paths; where the shell looks for a procedure file |
| **Execution directory** | `chx` | Relative *command* names when running something |

`chd` ≠ `cd`. A program visible via `dir` (data dir) can be "not found"
when run — running searches `chx`/`PATH`, not `chd`. Like Unix `cd`, `chd`
with no argument returns to `$HOME` (the `HOME` env var, **not** the
password-file login data dir); `chx` with no argument does nothing
(`Live` (os9exec) — see `os9-tools-and-shell.md` for the
test). Full resolution rule, `PATH` guidance, and the
compiler-driver exception: `os9-mental-model.md`'s "Two current
directories, not one" section; practical gotchas hitting this live:
`using-os9exec-repl.md`.

### 2. Lines end with CR, not LF

OS-9's line terminator is CR (0x0D), not LF (0x0A) — the most common
host↔OS-9 file-boundary bug.

- OS-9 C's `\n` **is CR**, not LF — a separate `\e` escape produces a true
  LF when one is genuinely needed.
- A Unix-authored (LF) source file can make the OS-9 C compiler read the
  whole file as one line, producing cascading syntax errors at nonsensical
  spots.
- RBF/SCF translation behavior: see `os9-mental-model.md`'s "Conventions
  that bite" section.
- Convert with `flip -m` (host-side files only — can't touch files inside
  an RBF image; edit those natively with `vi`/`ed`, which already produce
  correct native line endings). See `using-os9exec-repl.md`.

### 3. A program is a *module*, not a flat executable

Header + body + CRC, position-independent, no fixed load address, no
absolute addresses inside.

- One loaded copy is shared reentrantly across every process running it —
  each process gets its own data area, not its own code copy.
- `F$Link` finds an already-resident module by name (increments a link
  count); `F$Load` from disk only happens if it isn't resident. A module
  can outlive the process that loaded it ("sticky" attribute). Loading a
  higher-revision module of the same name silently replaces the directory
  entry without disturbing processes already running the old copy — only a
  fresh lookup sees the new one.
- No `mmap`, demand paging, or copy-on-write — a process's data area is
  allocated up front at fork time.
- Header carries type, language, access permissions, edition, and a
  supervisor-state/reentrant/sticky attribute byte; the kernel rejects a
  fork/link whose requested type doesn't match the module found. Offsets
  are `Live` (os9exec) against a real compiled program: `module-format.md`.

### 4. Pipe is `!`, not `|`

`cmd1 ! cmd2`. `|` isn't a shell metacharacter at all — code or muscle
memory using it fails silently, not with an error. Chains: `a ! b ! c`.
Redirection differs too: `>` is stdout, but `>>` redirects **stderr** — it
is not append. **To append, use `>+`.** The Unix reflex that `>>` means
append is the trap, and it fails quietly: you get a file of error text and
an untouched original.

**`Manual`-confirmed** — *Using Professional OS-9* v2.4 lists exactly three
modifiers: "`<` Redirects the standard input path, `>` Redirects the
standard output path, `>>` Redirects the standard error path." OS-9
additionally has `>+` (append to existing file or create) and `>-`
(truncate existing file or create) — undocumented in the v2.4 manual but
both `Live` (NitrOS-9, os9exec). Standard `>` (create only, fail if exists)
remains the default. Full table: `common/os9-tools-and-shell.md`.

### 5. Control keys are inverted or unfamiliar

Behavior, not just codes, differs:

| Key | Unix | OS-9 |
|---|---|---|
| **Ctrl-C** | kills foreground process | Backgrounds it instead (as if `&`), works immediately regardless of process state — `Live` (os9exec) — sends interrupt signal 3; see `using-os9exec-repl.md` |
| **Ctrl-E** | — | The actual kill key — terminates the child outright, `Live` (os9exec) — sends abort signal 2, not the uninterceptable signal 0; see Tier 2's signal table |
| **Ctrl-A** | move to start of line | Redisplays the previous input line without executing it, cursor at end — back up over it and retype to edit and resubmit; stands in for arrow-key/history recall (symbol `C$Rpet` — "repeat"; see `os9-tools-and-shell.md`) |
| Flow control | Ctrl-S pause / Ctrl-Q resume | Same (XOFF/XON), **plus** Ctrl-W pauses until any key |
| EOF / exit shell | Ctrl-D | ESC on a blank line |

Hazard: an arrow key sends an ANSI escape sequence starting with a raw ESC
byte; the line editor reads bare ESC as "exit." `tmode eof=04` remaps
exit/EOF to Ctrl-D, verified live, fixing this.

Configurable per-device via `tmode`/`xmode` — table is the documented
default, not guaranteed. Full key set and remapping:
`os9-tools-and-shell.md`.

---

## Tier 2 — same concept, different contract (close, but specifics differ)

### `fork` doesn't share memory

`F$Fork` gives the child a fully independent data area — no
copy-on-write, no shared pages. Only deliberate IPC (pipes, data modules,
events, signals) shares state. Child inherits current
directories/environment/open paths, not memory.

`F$Chain` (≈ `exec()`) reuses the current process (no new PID), preserving
open paths.

### Signals are numbers carrying data; handlers must be tiny

- Numeric codes, not names. 0=Kill, 1=Wake (uninterceptable); 2=Abort
  (Ctrl-E), 3=Interrupt (Ctrl-C); 5-255 reserved; 256-65535 user-defined,
  the code itself usable as a payload. **The 256-65535 tier is 68k-only**
  (16-bit code in `d1.w`) — 6809 carries the signal code in the 8-bit `B`
  register and caps at 255; see `6809/syscalls-and-module-format.md`'s
  Signals section for its (source-disputed) reserved-range boundary within
  that smaller space.
- A handler runs immediately and can't be interrupted by another signal
  (kernel masks during it) — keep it short/reentrant, no syscalls or
  sleeping. Do real work in the mainline under a mask, not in the handler.
  - **This is the kernel's `F$Icpt` contract, and a ported program may not be
    using it.** A Unix-compatibility `signal()` can install an intercept that
    only *records* the code, leaving your handler to run at the next poll —
    so "handlers run immediately" is true of OS-9 and can be false of the
    library in front of it. Establish which `signal()` was linked before
    concluding the kernel or the emulator is at fault; see
    `c/os9-clib-reference.md`.
- Masking nests with ±1 (`F$SigMask`); clearing to 0 wipes all nesting, not
  just yours. `F$Sleep` auto-unmasks — this is what makes
  mask→request→sleep→service safe.

Patterns and deadlock shapes: `ipc.md`.

### Events are counted semaphores — one primitive, not three

An event is a counter with waiters blocked on a target value. Binary mutex
= event with range (1,1); condition variable = wait/signal on an event.
One primitive (`F$Event`) covers what Unix splits into three.

### Shared memory is a data module

`F$DatMod` creates a named, shared, mutable region accessed by ordinary
pointer addressing — the "processes see the same live bytes" mechanism (vs.
a pipe, which moves bytes, or a signal/event, which carries no payload).
Unlike a program module, a data module is allowed to be non-reentrant
(mutated in place) — that's the whole point of it. No implicit atomicity —
synchronize explicitly.

### `mknod()` creates a directory, not a device node

Unix's `mknod()` is a general-purpose special/device-file factory. OS-9's C
library `mknod()` only creates a directory — ordinary files come from
`creat()`. The name survived; the behavior didn't. Code ported from Unix
that calls `mknod()` expecting a device node gets a directory instead, with
no error to flag the mismatch.

### Directories can't be opened like ordinary files

### `open(path, 0)` opens a file you cannot read

**The single most costly line to port unchanged.** OS-9's access mode is a *bit
field* — `D S E W R`, directory/single-user/exec/write/read (`Manual`, v2.4 TRM,
I$Open) — so **mode 0 requests no access at all**. POSIX spells read-only `0`.
Ported code therefore asks for nothing while its author believes it asked for
read, and **OS-9 grants exactly that**.

It does not fail in any way the code notices. `Live` (os9exec), a probe opening a
six-byte file and reading 64:

```
OPEN mode=0  fd=7  read=-1      <- a valid path number, and every read fails
OPEN mode=1  fd=7  read=6       <- S_IREAD
```

So the open **succeeds**, returns a usable-looking descriptor, and the file reads
as empty forever. Found in agrep 2.01, which calls `open(name, 0)` in five
places: files named on the command line were searched as empty, `agrep -c e file`
answered `0`, and nothing matched — while the *same* searches through stdin were
correct, because stdin was never opened by that code. A program can therefore
look half-working in a way that points at the pattern matcher rather than the
open.

Write `S_IREAD` (1). Treat a literal `0`, or any `O_RDONLY` from a compatibility
header, as a porting defect until you have checked what that header defines.

### `I$Create` is not `creat()`

`Manual` (v2.4 TRM, I$Create): *"An error occurs if the pathlist specifies a file
name that already exists."* Unix `creat()` on an existing file truncates it and
hands it back; OS-9 refuses with **`E$CEF` (218)**. Anything built on
open-or-create, or on "clobber the output file and start writing", needs its own
delete-then-create, and should expect 218 rather than treating it as fatal.

`I$Create` also **cannot make a directory** — that is `I$MakDir`. And on pipes
the same rule holds by name: a named pipe that already exists returns `E$CEF`,
while unnamed pipes cannot raise it.

`open(path, S_IREAD)` on a directory fails — the directory bit must be set
in the access mode (`S_IFDIR | S_IREAD`). `fopen()` offers no way to set
that bit at all, so it cannot open a directory under any mode. Unix code
that does `fopen(dir, "r")` to walk a directory simply doesn't work here.

### Climbing: count the dots

**Write `...`, not `../..`.** One period per level plus one — `.` stays put,
`..` is the parent, `...` climbs two, `....` three. This is the form the manual
documents (`Manual`, *Using Professional OS-9* v2.4, p. 4-9: "add a period for
each higher directory level") and the form to use in anything you write, because
**it is uniquely OS-9** and says so at a glance where a stack of `../` reads as
borrowed Unix.

**The rule underneath.** A component made only of periods climbs one level fewer
than it has dots, and **components compose** — a pathlist may chain any number of
them, and the arithmetic is simply addition. `../......./.././file` climbs
1 + 6 + 1 + 0 = **eight** levels. Climbing is **clamped at the volume root**: you
cannot walk off the top of a device.

**`../..` is also accepted** — it is two one-level components and lands in the
same place. Worth knowing so that borrowed Unix code is not suspected wrongly,
and so that a mixed pathlist is read correctly, but not worth writing.
`Hearsay` (rdoggett, from a real system: "yes real os-9 accepts `../../../..`
no problem"), so this is OS-9's behaviour and not a runtime indulgence.

`Live` (os9exec, 985e0d8 and later): an RBF image and a host directory agree on
`../..`, `../...`, `.../..`, `../......./.././`, `A/..`, `A/B/...`,
`A/B/C/../../..`, absolute pathlists with mixed runs, and `chd ../..`.

One measured case is worth quoting in full, because it carries its own control —
note that it mixes spellings to *exercise* composition, and is evidence rather
than a model to copy. From seven levels down, `list ./../.../...././SYS/f` opens a file **exactly six levels up**
— `0+1+2+3+0` — on both device types, and `chd` with the same pathlist followed
by `pd` lands six up. The control: that climb does **not** reach a file seven
levels up, which fails `E_PNNF`. So the runs are being *counted* rather than
merely accepted, a leading `./` and a trailing `/.` contribute zero without
disturbing the sum, and every run length in between composes.

**Historical note, because earlier text here said otherwise.** os9exec before
`985e0d8` mis-resolved relative dot-runs **on RBF images only**: the path code
treated the start of a relative pathlist as the device root, so `../..`
collapsed to `..` and a leading component was never cancelled (`A/../x` became
`A/x`). Every spelling in which a dot-run followed another component failed
`E_PNNF`. Host-directory devices resolved the same pathlists on the host and were
correct throughout, and absolute pathlists were always correct. **That was an
emulator defect, not OS-9 behaviour** — if you are reading a claim that `../..`
silently means `..`, or that the two forms cannot be mixed, it described that
bug. It is also a clean example of why a result measured on one device type is
not evidence about the other.

### A filename is at most 28 characters — and os9exec reaches only 27

OS-9 allows 1 to 28 characters in a name (`Manual`: *Using Professional OS-9*
v2.4, "Rules for Constructing File Names"), which is exactly what an RBF
directory entry holds — a 28-byte name field whose last character carries the
sign bit (Technical Manual, "Directory File Format"). A 29-character name is
too long everywhere.

**os9exec stops one short**, `Live` (os9exec), `Flag` against the manual: 27 characters reach a file and 28 do not. `build` accepted a
28-character name without complaint and the host file appeared under its full
name, but `dir` listed only the 27-character prefix and opening the full name
failed `E_PNNF`. The prefix does open it, and is the only handle left. So on
os9exec two names agreeing for 27 characters are one file — which is how host
files with long names collide when they are dropped into the tree, silently
and without either name being wrong. This is the emulator's limit, not
OS-9's: a 28-character name made on real OS-9 is legal, and is the one this
runtime mishandles.

The same boundary shows on an RBF image, measured on a fresh `mount -k=360k`
image and on a host-directory mount:

| | host directory | RBF image |
|---|---|---|
| 27 characters | opens | created, listed, opens |
| 28 characters | full name `E_PNNF`; the **27-char cut name opens it** | **`makdir` succeeds silently**, `dir` shows 27, opening the full name fails |
| 29+ characters | full name `E_PNNF`; the cut name opens it | `makdir` refuses outright — "can't make" |

On a host directory the cut name is not merely what `dir` displays — it is the
name that works, and the full one is the name that fails. Two host files sharing
their first 27 characters are therefore one file as far as OS-9 can reach: both
list identically and only the first in host order opens. See the host-directory
lookup rules in `common/using-os9exec-repl.md`.

So under os9exec 28 is the dangerous one: on RBF the directory entry is made
and reports success, and only the 27-character prefix can ever reach it
afterwards. A tool that writes a 28-character output file is told nothing and
cannot reopen what it wrote. **For anything that must also work under
os9exec, keep names to 27 characters** — one fewer than OS-9 allows.

### Priority + aging scheduler

Preemptive, priority-driven, default 2-tick (20ms) timeslice. Aging is a
single **system-wide** counter consumed at each process insertion, **not**
a per-process value that ticks up while a process waits (a commonly
repeated misreading) — a process queued earlier ends up with a more
favorable scheduling constant than one queued later at the same priority,
which is what keeps low-priority work from starving. `D_MaxAge` is a
**priority threshold**, not an age cap: processes at/above it are ordered
by raw priority with aging switched off among themselves, and as a group
fully preempt everything below for as long as any of them stays active —
not merely "get nearly all the CPU." Set priority: `setpr`/`F$SPrior`.
Full mechanism: `os9-systems-dev` skill's `kernel-internals.md`.

### The C compiler is K&R, not ANSI

No `const`/`volatile`, old-style function definitions only, `<strings.h>`
not `<string.h>`, no bit-fields, no `//`, no prototypes/call
type-checking. `int` is 32-bit on 68k (`Live` (os9exec); 16-bit claims
describe the 6809 compiler). Full list: `c/kandr-vs-ansi.md`.

### BASIC09: AND/OR/XOR are boolean; LAND/LOR/LXOR are bitwise

Both primary BASIC09 manuals (Rev G and Rev H) agree: `AND`/`OR`/`XOR`/`NOT`
operate on BOOLEAN values (TRUE/FALSE), while `LAND`/`LOR`/`LXOR`/`LNOT` are
bitwise/logical functions operating on integer values. Unlike C, where `&&`/`||`
and `&`/`|` are lexically distinct, BASIC09 names are similar — but the
distinction is consistent across both manuals: boolean operators vs. logical
functions for bit manipulation.

---

## Tier 3 — effectively 1:1. Just a rename; look it up and move on.

| Unix/Linux | OS-9 | Note |
|---|---|---|
| file descriptor (0,1,2) | path number (0,1,2) | same stdin/stdout/stderr convention |
| `open`/`close` | `I$Open` / `I$Close` | |
| `read` / `write` | `I$Read`/`I$ReadLn`, `I$Write`/`I$WritLn` | Ln variants do line editing/formatting |
| `lseek` | `I$Seek` | |
| PID | PID | plus an owner ID, inherited — a `group.user` pair on 68k, one flat integer on 6809 |
| `wait`/`waitpid` | `F$Wait` | |
| `exit` | `F$Exit` | |
| `getpid`/`getuid` | `F$ID` | returns PID, owner ID, priority (68k `group.user`; 6809 flat) |
| `kill(pid,sig)` | `F$Send` | |
| `signal`/`sigaction` | `F$Icpt` | contract differs, see Tier 2 |
| `sleep` | `F$Sleep` | counts ticks; 0 = sleep until signaled |
| `alarm`/`setitimer` | `F$Alarm` | one-shot, cyclic, or absolute date/time |
| semaphore | `F$Event` | counted, see Tier 2 |
| `setenv`/`getenv` | `setenv`/`printenv` (shell) | shell-level, not kernel syscalls |
| shell script | procedure file | no shebang; run by name or `shell <file` |
| subshell | `F$Fork` of the shell module | |
| `/dev/*` | device descriptor modules | named `/term`, `/d0`, `/p`, `/pipe`, `/nil`, … |
| VFS layer | file managers (RBF/SCF/SBF/PIPEMAN) | see `os9-mental-model.md` |
| ELF/executable | OS-9 module | see Tier 1 #3, `module-format.md` |
| shared library | reentrant module / trap handler | e.g. math via `trap #15` |
| `dlopen` | `F$Load` by name | |
| pipe / named pipe | `/pipe` unnamed / `/pipe/<name>` named | default buffer 90 bytes per the manuals, but **os9exec uses 4096** — see `ipc.md` |
| UID/GID | owner ID / group ID in process descriptor | |
| `sudo`/root | super-user = group 0 (**68k**; on 6809 it is flat user ID 0 — `6809/syscalls-and-module-format.md`) | |
| process states | Active / Waiting / Sleeping | |
| `nice`/`setpriority` | priority + `setpr` | aging twist, see Tier 2 |
| `errno` | `errno` | not cleared on success — check the call's return value first |

---

**Sources:** OS-9 v2.4 Technical Reference Manual, Technical I/O Manual v2.4,
Disk File Organization manual, Using Professional OS-9 v2.4, OS-9 Insights,
The OS-9 Guru, The OS-9 Primer, OS-9 C Compiler manual, BASIC09 Reference
Manual (Rev H), OS-9 BASIC User Manual (Rev G, 1991) (all official Microware
documentation). Directory-resolution rule, line-ending behavior, C `int`
size, module-header offsets, and the control-key/`tmode` fix additionally
verified live on os9exec.
