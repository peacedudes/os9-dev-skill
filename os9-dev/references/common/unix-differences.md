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

`open(path, S_IREAD)` on a directory fails — the directory bit must be set
in the access mode (`S_IFDIR | S_IREAD`). `fopen()` offers no way to set
that bit at all, so it cannot open a directory under any mode. Unix code
that does `fopen(dir, "r")` to walk a directory simply doesn't work here.

### More dots, not more `../`

`../..` → `...`; `../../..` → `....` — one more dot per level, not another
`../`. `..` (one level) is unchanged. Verified for both `dir` and `chd`.

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
