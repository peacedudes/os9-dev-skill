# OS-9 for people who already know Unix

Delta document, not a tutorial - ordered by how badly a wrong Unix
assumption bites, not by topic. Tier 3 (bottom) is a flat 1:1 lookup table;
skim once. Spend attention on Tier 1.

Applies OS-9-wide, not just 68k: the shell/directory/pipe behaviors below
(chd/chx split, `!` not `|`, CR line endings, ESC-exit, the control-key
inversions) were independently cross-referenced against multiple 6809
primary sources and confirmed identical. Where 6809 genuinely differs
(register conventions, `int` width, module header encoding), that's a
Tier 2/3 item, not a Tier 1 one - the model-level breaks from Unix are the
same regardless of which OS-9 architecture you're on.

---

## Tier 1 - model breaks (wrong, not just slow, if you assume Unix)

### 1. Two current directories, not one

Unix has one cwd. OS-9 has two:

| | Command | Governs |
|---|---|---|
| **Data directory** | `chd` | Relative *data* file paths; where the shell looks for a procedure file |
| **Execution directory** | `chx` | Relative *command* names when running something |

`chd` != `cd`. A program visible via `dir` (data dir) can be "not found"
when run - running searches `chx`/`PATH`, not `chd`. Like Unix `cd`, `chd`
with no argument returns to `$HOME` (the `HOME` env var, **not** the
password-file login data dir); `chx` with no argument leaves the execution
directory where it was, though on an RBF device it also prints
`Error #000:214`
(`Live` (os9exec) - see `os9-tools-and-shell.md` for the
test). Full resolution rule, `PATH` guidance, and the
compiler-driver exception: `os9-mental-model.md`'s "Two current
directories, not one" section; under os9exec, its own gotchas:
`using-os9exec-repl.md`.

### 2. Lines end with CR, not LF

OS-9's line terminator is CR (0x0D), not LF (0x0A) - the most common
snag when a file crosses between Unix and OS-9.

- OS-9 C's `\n` **is CR**, not LF - a separate `\e` escape produces a true
  LF when one is genuinely needed.
- A Unix-authored (LF) source file can make the OS-9 C compiler read the
  whole file as one line, producing cascading syntax errors at nonsensical
  spots.
- RBF/SCF translation behavior: see `os9-mental-model.md`'s "Conventions
  that bite" section.
- Convert on the Unix side before the file reaches OS-9 (`tr '\n' '\r'`, or
  `flip -m` where installed), or edit on OS-9 itself with `vi`/`ed`, which
  already produce correct native line endings. Under os9exec, see
  `using-os9exec-repl.md`.

**The CR rule fails differently depending on what the file is FOR.**
That OS-9 text is CR-terminated is easy to remember. What catches people is
that an LF file announces itself in three different ways, and only the first
is obvious. `Live` (os9exec), all three:

1. **Source (`.c`, `.h`) - loud, but not always in the same way.** The whole
   file is one line, and what that does depends on how long the file is.
   Reported for real sources: `**** source line too long ****` from `cpp`, on
   every file at once - hard to miss, easy to misread as a defect in the code.
   Measured on a *short* LF file, `cpp` said **nothing at all** and the
   failure surfaced at link time as `Symbol 'main' unresolved`, referenced by
   `cstart_a` - because with everything on one line the leading `#include`
   directive swallows the rest of it, so no `main` is ever compiled. That form
   is the more misleading of the two: it points at your entry point, not at
   your line endings. A long enough one-line file has also been seen to hang
   `cpp` outright rather than diagnose anything. `Live` (os9exec). **A silent
   `cpp` death is not diagnostic of line endings on its own** - an over-long
   *logical* line kills it the same way, including one you believed you had
   disabled inside `#if 0` (`c/os9-c-cheatsheet.md`). Both are the same
   underlying limit reached from opposite directions; check line endings first
   because it is cheaper, then the line.
2. **Data read at run time - silent.** The program builds, starts, and reads
   records that are not delimited the way it expects. A word list, a
   dictionary, a grammar, a score file. Nothing reports anything.
3. **Data `#include`d as source - the trap.** Files that are data by name and
   extension but source by use: `monop` keeps its board, properties and cards
   in `.dat` files that `monop.def` pulls in as C initialisers, so an LF
   `.dat` kills the *build*, with `cpp` dying exactly as it would on a `.c`.
   Convert "the source" and leave "the data" alone and you have broken the
   build in a file you are not looking at.

**The handling that avoids all three: unpack on OS-9 itself.** A
well-stocked disk carries `unshar`, `tar`, `ar`, `lha`, `gzip`, `compress`,
`unzip`, `zip`, `arc` and `zoo`; every file an OS-9 tool writes is
CR-terminated by construction, whatever its extension or role. `Live`
(os9exec), verified by extracting one archive both ways - the disk's own `unshar` produced files
byte-identical to a host-side unpack, without the conversion step that can be
got wrong.

That leaves exactly one host-side step, and it is transport: a **text** archive
has to arrive on the disk as OS-9 text. Skip it and OS-9's `unshar` cannot read
it either - it answers `No shell commands in <file>`, which is not an obvious
way of saying "wrong line endings". Binary archives (`.lzh`, `.Z`, `.tar`)
transport unconverted; converting one corrupts it.

### 3. A program is a *module*, not a flat executable

Header + body + CRC, position-independent, no fixed load address, no
absolute addresses inside.

- One loaded copy is shared reentrantly across every process running it -
  each process gets its own data area, not its own code copy.
- `F$Link` finds an already-resident module by name (increments a link
  count); `F$Load` from disk only happens if it isn't resident. A module
  can outlive the process that loaded it ("sticky" attribute). Loading a
  higher-revision module of the same name silently replaces the directory
  entry without disturbing processes already running the old copy - only a
  fresh lookup sees the new one.
- No `mmap`, demand paging, or copy-on-write - a process's data area is
  allocated up front at fork time.
- Header carries type, language, access permissions, edition, and a
  supervisor-state/reentrant/sticky attribute byte; the kernel rejects a
  fork/link whose requested type doesn't match the module found. Offsets
  are `Live` (os9exec) against a real compiled program: `module-format.md`.

### 4. Pipe is `!`, not `|`

`cmd1 ! cmd2`. `|` isn't a shell metacharacter at all - code or muscle
memory using it fails silently, not with an error. Chains: `a ! b ! c`.
Redirection differs too: `>` is stdout, but `>>` redirects **stderr** - it
is not append. **To append, use `>+`.** The Unix reflex that `>>` means
append is the trap, and it fails quietly: you get a file of error text and
an untouched original.

**`Manual`-confirmed** - *Using Professional OS-9* v2.4 lists exactly three
modifiers: "`<` Redirects the standard input path, `>` Redirects the
standard output path, `>>` Redirects the standard error path." OS-9
additionally has `>+` (append to existing file or create) and `>-`
(truncate existing file or create) - undocumented in the v2.4 manual but
both `Live` (NitrOS-9, os9exec). Standard `>` (create only, fail if exists)
remains the default. Full table: `common/os9-tools-and-shell.md`.

### 5. Control keys are inverted or unfamiliar

Behavior, not just codes, differs:

| Key | Unix | OS-9 |
|---|---|---|
| **Ctrl-C** | kills foreground process | Sends interrupt signal 3 to the last process to use the terminal. If the foreground program has not written to the terminal yet, the shell moves it to the background (as if `&`) instead; if it has, it dies unless it intercepts the signal - `Manual`, `Live` (os9exec); see `using-os9exec-repl.md` |
| **Ctrl-E** | - | The actual kill key - terminates the child outright, `Live` (os9exec) - sends abort signal 2, not the uninterceptable signal 0; see Tier 2's signal table |
| **Ctrl-A** | move to start of line | Redisplays the previous input line without executing it, cursor at end - back up over it and retype to edit and resubmit; stands in for arrow-key/history recall (symbol `C$Rpet` - "repeat"; see `os9-tools-and-shell.md`) |
| Flow control | Ctrl-S pause / Ctrl-Q resume | Same (XOFF/XON), **plus** Ctrl-W pauses until any key |
| EOF / exit shell | Ctrl-D | ESC on a blank line |

Hazard: an arrow key sends an ANSI escape sequence starting with a raw ESC
byte; the line editor reads bare ESC as "exit." `tmode eof=04` remaps
exit/EOF to Ctrl-D, verified live, fixing this.

Configurable per-device via `tmode`/`xmode` - table is the documented
default, not guaranteed. Full key set and remapping:
`os9-tools-and-shell.md`.

---

## Tier 2 - same concept, different contract (close, but specifics differ)

### `fork` doesn't share memory

`F$Fork` gives the child a fully independent data area - no
copy-on-write, no shared pages. Only deliberate IPC (pipes, data modules,
events, signals) shares state. Child inherits current
directories/environment/open paths, not memory.

`F$Chain` (≈ `exec()`) reuses the current process (no new PID), preserving
open paths.

### Signals are numbers carrying data; handlers must be tiny

- Numeric codes, not names. 0=Kill, 1=Wake (uninterceptable); 2=Abort
  (Ctrl-E), 3=Interrupt (Ctrl-C); 5-255 reserved; 256-65535 user-defined,
  the code itself usable as a payload. **The 256-65535 tier is 68k-only**
  (16-bit code in `d1.w`) - 6809 carries the signal code in the 8-bit `B`
  register and caps at 255; see `6809/syscalls-and-module-format.md`'s
  Signals section for its (source-disputed) reserved-range boundary within
  that smaller space.
- A handler runs immediately and can't be interrupted by another signal
  (kernel masks during it) - keep it short/reentrant, no syscalls or
  sleeping. Do real work in the mainline under a mask, not in the handler.
  - **This is the kernel's `F$Icpt` contract, and a ported program may not be
    using it.** A Unix-compatibility `signal()` can install an intercept that
    only *records* the code, leaving your handler to run at the next poll -
    so "handlers run immediately" is true of OS-9 and can be false of the
    library in front of it. Establish which `signal()` was linked before
    concluding the kernel is at fault; see
    `c/os9-clib-reference.md`.
- Masking nests with ±1 (`F$SigMask`); clearing to 0 wipes all nesting, not
  just yours. `F$Sleep` auto-unmasks - this is what makes
  mask->request->sleep->service safe.

Patterns and deadlock shapes: `ipc.md`.

### Events are counted semaphores - one primitive, not three

An event is a counter with waiters blocked on a target value. Binary mutex
= event with range (1,1); condition variable = wait/signal on an event.
One primitive (`F$Event`) covers what Unix splits into three.

### Shared memory is a data module

`F$DatMod` creates a named, shared, mutable region accessed by ordinary
pointer addressing - the "processes see the same live bytes" mechanism (vs.
a pipe, which moves bytes, or a signal/event, which carries no payload).
Unlike a program module, a data module is allowed to be non-reentrant
(mutated in place) - that's the whole point of it. No implicit atomicity -
synchronize explicitly.

### `mknod()` creates a directory, not a device node

Unix's `mknod()` is a general-purpose special/device-file factory. OS-9's C
library `mknod()` only creates a directory - ordinary files come from
`creat()`. The name survived; the behavior didn't. Code ported from Unix
that calls `mknod()` expecting a device node gets a directory instead, with
no error to flag the mismatch.

### Directories can't be opened like ordinary files

### `open(path, 0)` opens a file you cannot read

**The single most costly line to port unchanged.** OS-9's access mode is a *bit
field* - `D S E W R`, directory/single-user/exec/write/read (`Manual`, v2.4 TRM,
I$Open) - so **mode 0 requests no access at all**. POSIX spells read-only `0`.
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
answered `0`, and nothing matched - while the *same* searches through stdin were
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

`I$Create` also **cannot make a directory** - that is `I$MakDir`. And on pipes
the same rule holds by name: a named pipe that already exists returns `E$CEF`,
while unnamed pipes cannot raise it.

`open(path, S_IREAD)` on a directory fails - the directory bit must be set
in the access mode (`S_IFDIR | S_IREAD`). `fopen()` offers no way to set
that bit at all, so it cannot open a directory under any mode. Unix code
that does `fopen(dir, "r")` to walk a directory simply doesn't work here.

### Climbing: count the dots

**Write `...`, not `../..`.** One period per level plus one - `.` stays put,
`..` is the parent, `...` climbs two, `....` three. This is the form the manual
documents (`Manual`, *Using Professional OS-9* v2.4, p. 4-9: "add a period for
each higher directory level") and the form to use in anything you write, because
**it is uniquely OS-9** and says so at a glance where a stack of `../` reads as
borrowed Unix.

**The rule underneath.** A component made only of periods climbs one level fewer
than it has dots, and **components compose** - a pathlist may chain any number of
them, and the arithmetic is simply addition. `../......./.././file` climbs
1 + 6 + 1 + 0 = **eight** levels. Climbing is **clamped at the volume root**: you
cannot walk off the top of a device.

**`../..` is also accepted** - it is two one-level components and lands in the
same place. Worth knowing so that borrowed Unix code is not suspected wrongly,
and so that a mixed pathlist is read correctly, but not worth writing.
`Hearsay` (rdoggett, from a real system: "yes real os-9 accepts `../../../..`
no problem"), so this is OS-9's behaviour and not a runtime indulgence.

`Live` (os9exec): the rule holds for
`../..`, `../...`, `.../..`, `../......./.././`, `A/..`, `A/B/...`,
`A/B/C/../../..`, absolute pathlists with mixed runs, and `chd ../..`.

One measured case is worth quoting in full, because it carries its own control -
note that it mixes spellings to *exercise* composition, and is evidence rather
than a model to copy. From seven levels down, `list ./../.../...././SYS/f` opens a file **exactly six levels up** -
`0+1+2+3+0` - and `chd` with the same pathlist followed
by `pd` lands six up. The control: that climb does **not** reach a file seven
levels up, which fails `E_PNNF`. So the runs are being *counted* rather than
merely accepted, a leading `./` and a trailing `/.` contribute zero without
disturbing the sum, and every run length in between composes.

### No `getcwd`: name the current directory by climbing

`getcwd` and `getwd` are in neither `clib.l` nor `unix.l`, `Absent` (this
SDK's libraries). At the shell `pd` (and `pxd` for the execution directory on
6809) prints it. From C, work it out from the directory files themselves.

**An RBF directory is a file of 32-byte entries** (`Manual`, Technical Manual,
"Directory File Format"). Bytes 0-27 hold the name, with the sign bit set on
its last character. A first byte of 0 marks a deleted or unused entry. Byte 28
is zero and bytes 29-31 are the LSN of the file's descriptor sector, so reading
28-31 as one long gives the same number. Every directory is created holding
`.` and `..`, whose entries give its own and its parent's descriptor LSNs.

1. Open `.` with `S_IREAD | S_IFDIR` for the data directory, or `S_IEXEC |
   S_IREAD | S_IFDIR` for the execution directory. Execute mode alone cannot be
   read (`I$Open` in `68k/syscall-reference.md`). Read its `.` entry to get
   this directory's LSN.
2. Open the parent (`..`, then `...`, `....`, in the same mode) and look for
   the entry whose LSN matches the child's. Its name, with the sign bit
   cleared, is the child's name.
3. Stop at a directory whose `.` and `..` LSNs are equal: that is the root of
   the device. `_gs_devn(path, buf)`, given the **path number** of that open
   directory, returns the device name. Clear any sign bit on it too.

`Live` (os9exec): this gives `/h1/CMDS` after `chx /h1/CMDS` at Microware's
shell, on an RBF image; it works the same way under a ported shell. The collection's `which` does it in `pathof()`.

### A filename is at most 28 characters

OS-9 allows 1 to 28 characters in a name (`Manual`: *Using Professional OS-9*
v2.4, "Rules for Constructing File Names"), which is exactly what an RBF
directory entry holds - a 28-byte name field whose last character carries the
sign bit (Technical Manual, "Directory File Format"). **There is no
terminating NUL**: a 28-character name fills the field, and code that reads
entries as C strings runs on into the descriptor-sector bytes. End a name at
the character with bit 7 set. A 29-character name is too long everywhere.

### Priority + aging scheduler

Preemptive, priority-driven, default 2-tick (20ms) timeslice. Aging is a
single **system-wide** counter consumed at each process insertion, **not**
a per-process value that ticks up while a process waits (a commonly
repeated misreading) - a process queued earlier ends up with a more
favorable scheduling constant than one queued later at the same priority,
which is what keeps low-priority work from starving. `D_MaxAge` is a
**priority threshold**, not an age cap: processes at/above it are ordered
by raw priority with aging switched off among themselves, and as a group
fully preempt everything below for as long as any of them stays active -
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
and `&`/`|` are lexically distinct, BASIC09 names are similar - but the
distinction is consistent across both manuals: boolean operators vs. logical
functions for bit manipulation.

---

## Tier 3 - effectively 1:1. Just a rename; look it up and move on.

| Unix/Linux | OS-9 | Note |
|---|---|---|
| file descriptor (0,1,2) | path number (0,1,2) | same stdin/stdout/stderr convention |
| `open`/`close` | `I$Open` / `I$Close` | |
| `read` / `write` | `I$Read`/`I$ReadLn`, `I$Write`/`I$WritLn` | Ln variants do line editing/formatting |
| `lseek` | `I$Seek` | |
| PID | PID | plus an owner ID, inherited - a `group.user` pair on 68k, one flat integer on 6809 |
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
| `/dev/*` | device descriptor modules | named `/term`, `/d0`, `/p`, `/pipe`, `/nil`, ... |
| VFS layer | file managers (RBF/SCF/SBF/PIPEMAN) | see `os9-mental-model.md` |
| ELF/executable | OS-9 module | see Tier 1 #3, `module-format.md` |
| shared library | reentrant module / trap handler | e.g. math via `trap #15` |
| `dlopen` | `F$Load` by name | |
| pipe / named pipe | `/pipe` unnamed / `/pipe/<name>` named | default buffer 90 bytes per the manuals - see `ipc.md` |
| UID/GID | owner ID / group ID in process descriptor | |
| `sudo`/root | super-user = group 0 (**68k**; on 6809 it is flat user ID 0 - `6809/syscalls-and-module-format.md`) | |
| process states | Active / Waiting / Sleeping | |
| `nice`/`setpriority` | priority + `setpr` | aging twist, see Tier 2 |
| `errno` | `errno` | not cleared on success - check the call's return value first |

---

**Sources:** OS-9 v2.4 Technical Reference Manual, Technical I/O Manual v2.4,
Disk File Organization manual, Using Professional OS-9 v2.4, OS-9 Insights,
The OS-9 Guru, The OS-9 Primer, OS-9 C Compiler manual, BASIC09 Reference
Manual (Rev H), OS-9 BASIC User Manual (Rev G, 1991) (all official Microware
documentation). Directory-resolution rule, line-ending behavior, C `int`
size, module-header offsets, and the control-key/`tmode` fix additionally
verified live on os9exec.
