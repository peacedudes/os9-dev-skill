# OS-9 C Standard Library Reference

For Microware C Compiler targeting 68000/6809 OS-9 systems.

**Every `Live` tag here is `Live` (os9exec)** — OS-9/68k. No 6809 C
compiler was available to this project, so nothing on this page is
6809-verified; treat the 6809 column of any comparison as `Manual`.

## Overview

The Microware C library bridges OS-9 system calls and UNIX-style C I/O patterns.
The startup routine converts the OS-9 parameter string into `argc`/`argv`.
All standard I/O is path-based (paths 0=stdin, 1=stdout, 2=stderr) and
uses OS-9 `I$Open`, `I$Read`, `I$Write` calls under the hood.

Most wrapper functions follow UNIX naming for portability, but parameters
and return values may differ from their raw OS-9 equivalents—verify against
the manual's cross-reference table between C names and raw service-request
names (`F$xxx`/`I$xxx`).

## A complete worked program — `Live` (os9exec)

Compiled with `cc` and run on os9exec. It covers the three things a C
program does on OS-9 that a Unix habit gets wrong: path I/O, `errno`
carrying OS-9 codes, and process creation through `os9fork()` rather than
`fork()`/`exec()`.

```c
#include <stdio.h>
#include <errno.h>

#define READ_MODE  1
#define ATTRS      0x03

main()
{
    int path, child, status;

    /* --- happy path: create, write, close --- */
    path = creat("cexfile.txt", ATTRS);
    if (path < 0) {
        printf("FAIL creat, errno %d\n", errno);
        exit(1);
    }
    write(path, "written by cexample\015", 20);
    close(path);
    printf("PASS create/write/close\n");

    /* --- error path: open a file that is not there --- */
    path = open("no.such.file", READ_MODE);
    if (path < 0)
        printf("PASS open of a missing file: errno %d\n", errno);
    else {
        printf("FAIL open of a missing file succeeded\n");
        close(path);
    }

    /* --- error path: fork a module that is not there --- */
    child = os9fork("nosuchmod", 0, "", 1, 1, 0);
    if (child < 0)
        printf("PASS os9fork of a missing module: errno %d\n", errno);
    else
        printf("FAIL os9fork of a missing module returned %d\n", child);

    /* --- happy path: fork a real child and collect its status --- */
    child = os9fork("exfio1", 0, "", 1, 1, 0);
    if (child < 0) {
        printf("FAIL os9fork, errno %d\n", errno);
        exit(1);
    }
    child = wait(&status);
    printf("PASS child pid %d exited, status %d\n", child, status);
    exit(0);
}
```

Built and run, and what it actually printed (`exfio1` is the worked
assembly example from `68k/os9-68k-assembly.md`; its two lines appear
inline because the child shares the terminal):

```
cc cex.c -f=/dd/CMDS/DOG/cex2
cex2

PASS create/write/close
PASS open of a missing file: errno 216
PASS os9fork of a missing module: errno 221
PASS create/write/close
PASS open of a missing file failed as expected: Error #000:216 (E_PNNF) Path Name Not Found
PASS child pid 7 exited, status 0
```

What to take from it:

- **`errno` holds OS-9 error codes, not POSIX ones.** A missing file gives
  **216** (`E$PNNF`), not `ENOENT`/2. Testing `errno == ENOENT` is the
  reflex to unlearn; the numbers are the same ones a syscall returns in
  `d1.w`, so `common/error-codes.md` is the table to read.
- **A missing *file* and a missing *module* are different errors.**
  `open()` on an absent file gives 216; `os9fork()` on an absent module
  gives **221** (`E$MNF`), because module lookup is a different search
  (the execution directory) from file lookup.
- **`os9fork()` does not block.** It returns the child PID immediately;
  the parent must `wait()` to collect the status. Here `wait()` returned
  the same PID and the child's exit status of 0.
- **Note the K&R shape**: `main()` with no return type and no prototypes.
  See `c/kandr-vs-ansi.md` before reaching for ANSI syntax.
- `\015` writes the CR that OS-9 uses as its line terminator; the resulting
  file dumped as 20 bytes ending `0d`. `\n` is *not* a newline here — see
  `common/unix-differences.md`.
- **Don't interleave `write()` and `printf()` on the same path** — this
  program keeps the file on its own path and messages on stdout. The File
  I/O section below has the corruption details.

## Standard Headers Available

| Header | Notes |
|--------|-------|
| `<stdio.h>` | File I/O, printf/scanf; defines `FILE`, `stdin`, `stdout`, `stderr` |
| `<stdlib.h>` | `exit()`, `system()`; limited (no `rand()`, etc.). **Not on Ultra C's default `CDEF` include path** — `Live` (os9exec): `#include <stdlib.h>` fails `cpp` with `can't open /h0/DEFS/stdlib.h (err=216)` under the standard `cc` toolchain; the file exists on-disk only under the gcc2-specific `DEFS/os9lib`/`DEFS/GCC2` trees (reachable with `-I/h0/DEFS/os9lib`). K&R doesn't require a prototype for `exit()`, so dropping the include and declaring nothing works fine |
| `<ctype.h>` | Character classification (macros, K&R-era coverage) |
| `<setjmp.h>` | `setjmp()`, `longjmp()` |
| `<time.h>` | OS-9-specific system time (see "File Dates and Time Zones" below) |
| `<errno.h>` | OS-9 error-code extensions. **The 6809 runtime's `EFPOVR`/`EDIVERR`/`EINTERR` (40/41/42) are not in the 68k header** — `Live` (os9exec): each is an "undeclared identifier" at compile. 68k uses different OS-9-style short names; read the header itself, or `common/error-codes.md`, for the actual FP/divide/overflow codes. |
| `<module.h>` | OS-9 module linking |
| `<sgstat.h>` | OS-9 file status/setstat (`I$SetStt`) |
| `<modes.h>` | File status/mode bits (owner/public only, no group class). **`Live` (os9exec): `<stat.h>` does NOT exist on the 68k `DEFS` — use `<modes.h>`** (see File Permissions below) |

**String functions live in `strings.h`, not `string.h`.**

## File I/O

| Function(s) | OS-9-specific behavior |
|---|---|
| `fopen`/`freopen`/`fdopen(char *name, char *action, ...)` | Action letters: r/w/a/u/c/e/**d** (directory read — OS-9 specific). Append `x` (e.g. `"wx"`) locks to current directory and sets execute permission. `freopen` closes the original stream even on failure. |
| `fclose`/`fflush(FILE *fp)` | `fflush(NULL)` flushes every open stream, not just one. |
| `fread`/`fwrite(void *ptr, int size, int number, FILE *fp)` | Returns item count actually transferred; 0 on EOF/error. |
| `fseek`/`rewind`/`ftell` | `fseek` place: 0=start, 1=current, 2=end. |
| `getc`/`getchar`/`getw`/`gets`/`fgets` | `getc()` **auto-selects** `read()` (raw/binary) vs `readln()` (line-edited terminal) based on file type — override with `_SCF`/`_RBF` flags before the first read if you need to force one. `gets()` replaces the trailing `\n` with a null. |
| `putc`/`putchar`/`putw`/`puts`/`fputs` | `puts()` appends `\n`; `fputs()` does not. |
| `printf`/`fprintf`/`sprintf` | **No marker call is needed on 68k** — `Live` (os9exec): `%ld` and `%f` both print correctly with nothing called first (a bare `printf("%f", 3.14159)` gives `3.141590`). The `_pfltinit()`/`_prfloat()` markers some documentation requires before printing a `long`/`double` **don't exist in 68k `clib.l`** at all: calling either fails to *link* (`Symbol '_pfltinit'`/`'_prfloat' unresolved`). They're a 6809-era artifact — with a 16-bit `int` and a proprietary float format a width-disambiguating marker is meaningful, but on 68k, where `int`/`long` are both 32-bit and floats are IEEE, it's dead weight. **6809 behavior unverified (`Manual`) — the markers may genuinely be required there.** |
| `scanf`/`fscanf`/`sscanf` | Specs: `%d %o %x %u %f %e %g %c %s`, plus `%D %O %X` for long and `[...]` for character-set match. **Every argument must be a pointer** — passing a value instead of `&value` is an easy mistake the compiler won't catch. |
| `setbuf(FILE *fp, char *buffer)` | Call after `fopen()`, before any I/O. `stderr` is always unbuffered by default. **Do not make `stdout` unbuffered** — passing `NULL` is documented as doing it and the result is corrupt output, not slow output. `Live` (os9exec): after `setbuf(stdout, (char *)NULL)`, `printf("sb3 unbuffered printf %s\n", "ok")` emitted 22 bytes of `0x16`, two of `0x02` and one of `0x01` — each literal run and each conversion written as a byte equal to **its own length**, repeated that many times. Measured across nine programs to both routes, not to `setbuf` alone: `setvbuf(stdout, NULL, _IONBF, 0)` corrupts identically, while a real buffer, `_IOLBF`, the untouched default, and `fprintf` to either stream are all correct, and `putc` on the same stream after the same call writes the right bytes. Pipes, redirection, output size and `fflush` are all innocent. Whether the fault is this C library's or the runtime's is unresolved, `Flag` — the rule for a porter is not to leave `stdout` unbuffered: give it a buffer, or leave the default alone and `fflush()`. Unix programs that do this in `main` (cshar's `unshar`) print garbage until the call is removed. |
| `write(int path, char *buf, int count)` / `read(int path, char *buf, int count)` | Raw path-based I/O (OS-9 `I$Write`/`I$Read` directly, no `FILE *` or buffering) — the primitive underneath the numbered stdin/stdout/stderr paths (0/1/2). **Do not mix these with `printf`/`fprintf`/other stdio calls on the same path without an explicit `fflush()` in between.** `Live` (os9exec): interleaving a raw `write()` with a buffered `fprintf()` on the same fd doesn't just reorder or drop output — the two calls' bytes physically overlay each other in the shared stdio buffer, corrupting both (e.g. `"raw write with fflush first\n"` came out as `"after writeith fflush first"` when a `printf` followed without a flush). `write()`/`read()` used alone, with no stdio calls sharing the same path, work correctly. |

**`Live` (os9exec)** — the core File I/O behaviors above check
out: `fwrite("ABCDE",1,5)` returned `5` and `fread(...,1,5)` read back `ABCDE`
(both return the item count); all three `fseek` place codes work — `0`/start
(→`CD` at offset 2), `1`/current (a `+3` from offset 2 then read gave `56`), and
`2`/end (a `-3` from end gave `78`); `puts` appends `\n` while `fputs` does not
(`puts("PUTSLINE")` then `fputs("FPA")`/`fputs("FPB\n")` produced `PUTSLINE`
on its own line followed by `FPAFPB`); and `gets` strips the trailing newline
and NUL-terminates (input `HELLOWORLD` → a 10-char string, no `\n`). `getc`
auto-select confirmed on the **disk-file** side: reading a file containing
`41 08 42` (an `A`, a raw `0x08` backspace, a `B`) returned all three bytes
intact (`COUNT=3`, no line-editing) — i.e. `getc` uses raw `read()` for a disk
file. The terminal side (line-edited `readln()`) isn't scriptable here, but the
type-based selection is demonstrated by the raw disk read.

## `putchar`/`putc` evaluate the character twice when the stream is line-buffered

**Never give `putchar` or `putc` an argument with a side effect.** `putchar(*p++)`
is a bug here, and it is a bug that hides from the obvious test.

`Source` (SDK `<stdio.h>`):

```c
#define putc(c, p)	\
	(((p)->_ptr >= (p)->_end || (((p)->_flag & _IOLBF) && (c) == '\n')) \
	? _flshbuf((p), (c)) : ((p)->_flag |= _WRITTEN, *(p)->_ptr++ = (c)))
#	define putchar(c)	putc(c, stdout)
```

`(c)` appears in the guard and again in whichever branch runs. When `_IOLBF`
(`0x0800`) is clear the guard short-circuits before reaching `(c)`, so it is
evaluated once. **When `_IOLBF` is set it is evaluated twice** — once to ask
whether it is a newline, once to store it. The usual licence for `putc` to
evaluate its argument repeatedly covers the *stream*, not the character, so this
is a real defect rather than a hazard you were warned about.

The stream argument is multiply evaluated too, unconditionally — `putc(c,
*fpp++)` is broken on any stream, and `getc(p)` evaluates `(p)` several times
for the same reason.

**Which streams are line-buffered is the whole problem.** `Live` (os9exec), one
binary writing `ABCDEFGH` with `while (*p) putchar(*p++);`:

| stdout is | output |
|---|---|
| a terminal | `ACEG` + a NUL |
| a pipe | `ACEG` + a NUL — and it stays wrong downstream |
| a file | `ABCDEFGH`, byte-exact |

Every second byte is eaten by the newline test, and the string's own terminating
NUL is written as data at the end. The first byte survives because the buffer is
not yet set up, so that call takes the flush branch and evaluates `(c)` once.

**So `prog >file` is clean and `prog | anything >file` is corrupt.** A test that
captures output by redirecting to a file cannot find this class of bug, and a
byte-identical file comparison will pronounce the program correct. Test through a
pipe.

Grepping source for `putc`/`putchar` with a `++` or `--` argument is a useful
screen but **not a verdict** — binaries carrying the pattern in their source have
been measured clean. A shipped binary need not have been built from the source
beside it, or against this library vintage. Use the grep to choose what to test,
then settle it on the binary by comparing its output to a file against its output
through a pipe.

The fix is one line at the top of the file:

```c
#undef putchar
#define putchar(c) fputc((c), stdout)
```

`fputc` is a function, so its argument is evaluated once. Do the same for `putc`
where a stream may be line-buffered. Afterwards file output is unchanged and pipe
output becomes correct.

## Restore the option fields you changed, never a whole saved struct

`Live` (os9exec). `_gs_opt`/`_ss_opt` read and write the path's whole option
structure, so the obvious idiom — save a `struct _sgs` on entry, put the copy
back on exit — makes every routine that does it **clobber every other one**.

Measured in a rogue port with two independent routines: one turned echo off, the
other cleared the `^C`, `^E` and `ESC` keys. The keyboard routine took its copy
*after* echo was already off, and on exit wrote that copy back *after* the echo
routine had turned echo on — leaving `kbich=3 kbach=5 eofch=27` correct and
**`echo=0`**, with nothing having failed. Restoring only the fields each routine
had actually changed gave `echo=1` and the rest unchanged.

Nothing here is concurrent. It is an ordinary read-modify-write on shared state,
where the "shared state" is a struct each routine believed it owned, and the
stale write wins simply by happening last. **Read, change your fields, write —
do not snapshot and replay.**

Two reasons this is worse on OS-9 than the same mistake elsewhere: the failure is
**silent and partial**, so what you get is one wrong setting among several right
ones rather than an obvious breakage; and option changes may not be private to
your path at all (see the `PD_ALF` discussion in `common/memory-and-io.md`), so a
whole-struct replay can undo something another *process* set, not merely another
routine of yours.

## A signal that kills a read leaves stdio latched, and the loop spins

`Live` (os9exec). A signal in the deadly range aborts a blocked serial or pipe
read (see `common/ipc.md`), and through Microware stdio the aftermath is worse
than the abort:

- `getchar()` returns **EOF**, with `ferror(stdin)` **set**;
- the error flag **stays set**;
- every later `getchar()` returns −1 **immediately, without reading**, until
  `clearerr(stdin)`.

So a program looping on `getchar()` does not block, does not report anything, and
**spins** — consuming the CPU while appearing hung. The cure is `clearerr(stdin)`
once you have decided the signal was survivable; the diagnosis is that a hang
which burns CPU is a latched error flag, not a blocked read. A genuinely blocked
read is idle.

**So do not tidy away a `clearerr()` you cannot account for.** Period code
already knew about this and guarded it: a 1980s game with an alarm timeout calls
`clearerr(stdin)` on the path its interrupted read returns through, commented
only as being in case a user sends end-of-file. `Live` (os9exec): that program
takes its timeout, returns to its menu, and reads the next prompt normally — no
spin. The guard is doing work that its comment does not claim, which is exactly
what makes it easy to delete during a port.

## Third-party `signal()` may not be asynchronous at all

`Live` (os9exec), and a trap for anything ported with a Unix compatibility
library rather than Microware's own calls. The `unix.l` shipping with one
freeware collection implements `signal()` **without asynchronous delivery**: it
installs an intercept that merely *records* the signal code, and your handler
runs only when the program later calls `check_signal()`.

**What is deferred is the handler, not the signal.** The distinction matters,
because the signal has a visible effect that looks like success. Measured `Live`
(os9exec) on a real terminal, `signal(5, lose)` then `alarm(3)` then blocking in
`gets()`:

| time | what happened |
|---|---|
| 0.0s | blocked in `gets()` |
| 3.0s | **`gets()` returned early**, with no key pressed — the alarm interrupted the read |
| — | the handler had *not* run |
| 3.1s | handler ran, on the next `check_signal()` |

So a ported program can time out at exactly the right moment and print exactly
the right message while its handler has never been entered — the timeout it is
reporting came from the interrupted read, and whatever it prints next is
ordinary code after `gets()`. **Do not read a correct-looking timeout as evidence
that asynchronous delivery works.** Conversely, a program that only ever waits,
with no poll and no read to interrupt, gets nothing.

An interrupted read is also the case that latches stdio's error flag — see the
section on that below, because the two together turn one timeout into a spinning
loop.

Microware's own `intercept()` does run the handler: measured, it ran for a
self-sent signal.

So when a ported program's timers appear dead, establish **which `signal()` it
linked** before suspecting the kernel or the emulator. The two have the same name
and different semantics, which is the whole difficulty.

## Single-key input: `cbreak()` does not make the terminal raw

`cbreak()` and `crmode()` **cannot affect stdio**, because they are not calls at
all. The SDK's `DEFS/curses.h` defines them as `#define cbreak() crmode()` and
`#define crmode() _crmode = TRUE` — a flag assignment. Nothing issues `SS_Opt`,
nothing calls `tmode`, nothing reaches the SCF driver, so the path's line
discipline is untouched.

Measured, `Live` (os9exec), sending one bare keystroke and only then an Enter:

| Reader, after `initscr(); cbreak();` | Bare keystroke | Enter |
|---|---|---|
| `getchar()` | echoed, still blocked | returned |
| `getchar()` after `crmode()` instead | echoed, still blocked | returned |
| `getchar()` with no curses at all (control) | echoed, still blocked | returned |
| **`getch()`** | **returned immediately** | not needed |

**So `cbreak()` is honoured by curses and invisible to stdio** — it is not
inert, and it is not a no-op; it simply only means something to the one reader
that consults the flag. The three `getchar()` rows agreeing with the no-curses
control is what a flag-only macro predicts, and `getch()` returning on the bare
key is `curses` doing its own single-character read.

The tell in the `getch()` capture is worth recognising: the echoed key and the
program's output run together on one line (`kGOT 107`), because `getch()`
returned before any line discipline was involved.

Practical consequence: a program that calls `cbreak()` and then reads with
`getchar()` compiles, links, runs, and silently requires Enter after every
key — it reads as a broken game rather than a porting error. Read keys with
`getch()`, or change the path's own editing with `tmode`/`SS_Opt`.

**Building a curses probe**: if the link reports `wclrtoeol` unresolved *while
naming `curses.l` as the referencing file*, that is link order, not a missing
symbol — `curses.l` both references and defines it, so a single-pass linker has
already passed the definition. Listing `-l=.../curses.l` **twice** resolves it.

**A curses program needs `TERM` set inside the guest.** `Live` (os9exec): boot
straight to a shell rather than through a login and `initscr()` fails with
`Unknown terminal type ''`, because the host's `TERM` does not reach the guest —
the guest's own login/startup is what normally sets it. The tell is that
message; a run that shows it has measured nothing about curses behaviour,
because `initscr()` never succeeded. `setenv TERM vt100` in the guest first.

## `termlib`: the pad character is `PC_`, and the error you get hides the real bug

`Source` (SDK `DEFS/termcap.h`):

```c
extern char PC_, *BC, *UP, *tgetstr(), *tgoto();
extern short ospeed;
```

Two things follow, and the dangerous one is silent.

**The pad character is named `PC_`, not `PC`.** Period termcap code declaring
`PC` fails to link. That is the *safe* failure: the linker names it, you rename
it, it works.

**`BC` and `UP` are `char *`.** Code of the era commonly declares them as small
arrays — `extern char BC[2], UP[2], PC;` — and against this library the array
declarations **link cleanly**, because the symbols exist and a linker cannot see
the type disagreement. Writing `BC[0]`/`BC[1]` then overwrites termlib's pointer
rather than filling a buffer, and what breaks is whatever uses that pointer
later.

So the trap is the shape of the diagnostic: **the one symbol that fails to link
is the one that is harmless to fix, and fixing only it leaves two silent memory
corruptions in place.** If `PC` is unresolved in a port, treat it as a signal to
check the declarations of `BC` and `UP` in the same file and make them `char *`,
not as a one-line rename.

## `printw()` bus-errors on a floating-point conversion

**Do not pass a float to `printw`.** `Live` (os9exec), reproduced independently
on two rigs with `curses.l`, `termlib.l` and `math.l` linked:

```c
printw("F %.2f", 100.0);        /* bus error, vector $02 */
printw("I %d",   100);          /* fine -- same program, same libraries */
sprintf(buf, "F %.2f", 100.0);  /* fine -- the C library formats it correctly */
addstr(buf);
```

So it is `printw`'s own conversion, not the C library's float formatting and not
a missing math library.

**The trace is the reason this is worth knowing**, because it does not look like
a formatting fault. The last syscall is a write, and the PC sits in a runaway
zero-padding loop:

```
Executing: -->0005715a: 16fc 0030    MOVE.B #$30,(A3)+     ; $30 is ASCII '0'
              0005715e: 5385         SUB.L  #$00000001,D5
```

A reader who sees a byte-fill loop and a write syscall will start auditing their
own buffers. **The fix is to format with `sprintf` and draw with `addstr`.**

**Scope: `printw` alone. The rest of the family is fine.** Measured with curses
genuinely initialised (`LINES=24 COLS=80`), same float, same program:

| call | result |
|---|---|
| `printw("%.2f", 100.0)` | **bus error** |
| `wprintw(stdscr, "%.2f", 100.0)` | drew `100.00` |
| `mvwprintw(stdscr, 2, 2, "%.2f", 100.0)` | drew `100.00` |
| `mvprintw(2, 2, "%.2f", 100.0)` | survived |

`stdscr` is what `printw` is shorthand for, so **the defect is in the wrapper,
not in the window and not in curses initialisation.**

That gives a lighter fix than `sprintf` for a program with many call sites:

```c
#define printw(f, a)   wprintw(stdscr, (f), (a))
```

**But note the arity.** `printw` is variadic; that macro takes exactly one
argument after the format and will break any call with a different count. It
suits a program whose calls are uniform — and where they are not, `sprintf` into
a buffer and `addstr` it remains the general answer.

### A working `getenv` is not evidence a library can see your variable

Two routes exist into a guest process's environment — the emulator's parameter
block (`@NAME=VALUE`, see `common/using-os9exec-repl.md`) and the OS-9 shell's
`setenv` — and **they are not equivalent to every consumer.** `getenv` consults
both. A library that walks the environment block itself need not.

`Live` (os9exec), one program printing `getenv("TERM")` and then calling
`initscr()`, so nothing differs but how the variable was created:

| route | `getenv("TERM")` | `initscr()` |
|---|---|---|
| `@TERM=vt100` on the host command line | `vt100` | `LINES=24 COLS=80` |
| `setenv TERM vt100` in a shell procedure | `vt100` | `Unknown terminal type ''`, `LINES=0 COLS=0` |

Same binary, same run, `getenv` agreeing in both. The failing case reports an
**empty** name: curses is not failing to match `vt100`, it never sees a name.

**This is one rig's curses, not a property of OS-9 curses, `Flag`.** On a second
rig the same comparison passes on all three routes — `@`-passed, `setenv`, and a
real `SYS/login` session — so the builds differ. Two candidate explanations for
the split were tested here and **eliminated**: forking the program by absolute
path versus by bare name makes no difference, and `TERMCAP` holding a file path
versus the entry string makes no difference. On the rig that fails, the route is
the only variable that moves it.

**What to take from it regardless of which build you have:**

- **Do not use `getenv` to prove a variable reached a library.** It is the one
  check that cannot distinguish these routes, which makes it worthless for
  exactly this fault and reassuring while you chase the wrong thing.
- **If a terminal library reports an empty name**, try passing the variable as
  `@TERM=`/`@TERMCAP=` before suspecting your termcap. It needs no login session:

```sh
env '@TERM=vt100' '@TERMCAP=/dd/SYS/termcap' os9exec /h0/CMDS/prog
```

  `TERMCAP` may hold a path or the entry itself; both work where this works.

## String Functions (`strings.h`, not `string.h`)

| Function | Notes |
|---|---|
| `strcat`/`strncat`/`strcmp`/`strncmp`/`strcpy`/`strncpy`/`strlen` | `strncpy` pads the remainder with nulls if the source is shorter than n. |
| `strhcpy` | Copies a sign-bit-**terminated** *source* (the OS-9 name/string convention: the final char has bit 7 set to mark the end) into a NUL-terminated C string — it copies through the terminator char with the high bit cleared, then NUL-terminates. **`Live` (os9exec) — dangerous gotcha, NOT in any manual:** `strhcpy` stops **only** at a high-bit byte, **not at NUL**. Handing it a plain NUL-terminated C string makes it read *past* the NUL into adjacent memory and **overflow the destination** — `strhcpy(buf,"AB")` copied `41 42 00 44 4F 4E 45 20` (`AB\0DONE ...`, straight into the next string literals) and with a small `buf[8]` corrupted the stack and bus-errored (`Error #000:102`) deterministically. **Only ever pass a genuinely sign-bit-terminated source**; to convert a C string, set bit 7 on its last char first. |
| `index(s, ch)` / `rindex(s, ch)` | OS-9/BSD names instead of ANSI's `strchr`/`strrchr`. **`Live` (os9exec)**: `index("hello",'l')`→`"llo"`, `rindex(...)`→`"lo"` both link and work; `strchr` fails to link (`Symbol 'strchr' unresolved`, `l68: error - unresolved references`) — the ANSI names genuinely aren't in `clib.l`. |

**No bounds checking** — caller must ensure buffers are large enough. No `strstr()`.

**`Live` (os9exec) — actual 68k `clib.l` symbol availability** (each
link-tested on os9exec): `strcmp`/`strncmp`/`strlen`/`malloc`/`free`/`atoi`
link and work. **Memory functions are ANSI, not BSD:** `memcpy`/`memset` link;
`bcopy`/`bzero` are **absent** (`Symbol unresolved`) — an inconsistency with the
BSD-style *string-search* names (`index`/`rindex`, no `strchr`) just above.
Also **absent** (unresolved at link): `strchr`/`strrchr` (use `index`/`rindex`),
`strtol` (use `atoi`), `strdup`, `strstr`. Reach for the name the library
actually has, or the link fails outright rather than at runtime.

## Character Classification (`<ctype.h>`)

Fast inline macros built over `_chcodes[]` table: `isalpha isupper islower
isdigit isxdigit isspace ispunct isalnum isprint iscntrl isascii toupper
tolower toascii`. Domain guaranteed for ASCII only (-1 to 127).
`_toupper`/`_tolower` (with underscore) are faster but restricted: pass
only lowercase to `_toupper` and uppercase to `_tolower`, or result is
undefined.

**Gotcha: no `isgraph()`** — this K&R-era header lacks ANSI additions.
Calling `isgraph()` fails at *link* time (unresolved symbol), not compile
time. Implement as `isascii(c) && isprint(c) && c != ' '`.

## File Permissions (`<modes.h>`)

**The mode/permission bits live in `<modes.h>`, not `<stat.h>`** —
`Live` (os9exec): `#include <stat.h>` fails `cpp` outright
(`can't open /dd/DEFS/stat.h`, err 216 — there is no `stat.h` in the 68k
`DEFS`), while `<modes.h>` is present and compiles. `<stat.h>` was a Unix-ism
that doesn't exist on this toolchain.

OS-9 has only two permission classes, **owner** and **public** — there is no
group class. `<modes.h>` names them with OS-9's own symbols: owner
`S_IREAD`/`S_IWRITE`/`S_IEXEC` and public `S_IOREAD`/`S_IOWRITE`/`S_IOEXEC`
(plus `S_ISHARE`, `S_IFDIR`) — **not** Unix's `S_IRGRP`/`S_IROTH` group
macros, and there is no `stat.h` aliasing those onto the public bits. Code
ported from Unix
that extracts a permission triple with the classic octal masks
`0700`/`0070`/`0007` misses OS-9's actual permission bits (`0x01`-`0x20`)
entirely and renders every permission as absent.

When rendering a Unix-style 10-character mode string, mirror the OS-9 public
bits into *both* the group and other positions (OS-9 has no separate group
class). A giveaway symptom: an `ls -l`-style listing whose file-type character
is right but whose permission bits are all dashes means the *permission* decode
is using Unix masks — independent of whatever else might be wrong with the type
decode.

## File Dates and Time Zones

OS-9 stores file modification dates as **local wall-clock time** — the FD
sector's 5-byte `fd_date` field (year-1900, month, day, hour, minute; no
seconds). A Unix `time_t`, by contrast, is UTC. Treating the stored fields
as if they were UTC and printing them back through `localtime()` shifts
every timestamp by the local UTC offset — a flat, silent whole-timezone
error.

The obvious fix — `mktime()`, which interprets a `struct tm` as local time
— is not available under gcc2: os9lib's `<time.h>` only declares it in its
non-GCC branch. A zone-agnostic workaround needing no new library symbol:
convert the raw fields naively into a `time_t`, run it through
`localtime()`, measure how far the returned fields drifted from the
originals, and add that difference back. This is correct in any timezone;
it can be off by an hour for a timestamp that lands inside a DST
transition, which minute-resolution local dates can't disambiguate anyway.

## Memory Management

| Function(s) | Notes |
|---|---|
| `malloc(unsigned size)` / `free(ptr)` / `calloc(nel, elsize)` | `calloc` zero-initializes. Repeated `free()` of the same pointer is undefined, not caught. |
| `sbrk(int increase)` | Request memory from OS; returns -1 if refused. |
| `ibrk(int increase)` | Request memory from the program's initial pool (distinct from `sbrk`). |
| `freemem(void)` | Pointer to the base of free memory. |

**`Live` (os9exec)**: `calloc(16,1)` returned a block whose
16 bytes were all zero (zero-init confirmed), and `sbrk(1000000000)` (a ~1 GB
ask) returned `-1` (refused, as documented). `malloc`/`free`/`calloc`/`sbrk`
all link.

**Memory layout** (high to low address): stack (grows downward) → free
memory (`malloc`/`sbrk` pool) → I/O buffers (256 bytes per open file) →
uninitialized data → initialized data → kernel/registers. The global
`memend` marks the heap's upper bound. (Some 6809-era documentation adds a
"direct page" region here for small, directly-addressed variables — that's
a 6809 hardware feature with no 68000 equivalent; don't expect it on our
target.)

**Compile-time sizing:** the linker adds 4KB by default for data/stack/
parameters/buffers — override with `-m=<n>` (`-m=2` = 512 bytes, `-m=10k`
= 10KB) if a program needs more.

## Process/Exec Functions

| Function | Notes |
|---|---|
| `os9fork(char *modname, int paramsize, char *paramptr, int type, int lang, int datasize)` | Not a standard C function — direct OS-9 process creation. `type`=1 is "program". `lang`=1 is native object code for whatever CPU the running system is (the module header's `M$Lang` field) — on a 6809 system that's 6809 object code (code 4 there is C I-code instead); on 68k, code 1 is 68K object code. It's not a single cross-architecture enum where one number always means "6809." Returns child PID or -1. Parent does **not** automatically wait — pair with `wait()`. **`modname` resolution — `Live` (os9exec)**: a bare name (no leading `/`) resolves via the exec-directory search, same as `F$Fork`/Shell — confirmed forking `"childprg68k"` by bare name, correct child PID and exit status returned (needs the target module actually present in the current exec directory, which tripped up the first attempt here purely on directory placement, not a real resolution-rule question). **`datasize` sizing — `Source`-confirmed**: `os9exec`'s `F$Fork` implementation (`procstuff.c`) calls the same `prepData()` used for `F$TLink`'s trap-handler memory, with `datasize` (plus `paramsize`) simply *added* to the module's own declared `_mdata`+`_mstack` — it is headroom on top of the module's own requirement, not a replacement absolute total. A `4096`-byte guess "worked" because it's headroom added to whatever the module already needs, not because 4096 is itself the right number for any particular program. **Arity is deliberately unprototyped, `Flag` — and the one fixed prototype is the outlier.** The six-parameter form above is what was exercised here. Three separate Microware-derived `stdlib.h` copies (the SDK's `os9lib` tree and two archived ones) decline to commit: they declare bare `os9fork(), os9forkc(),` — K&R empty parens, any arity — and carry the only full signature **commented out**, as `(char *, char *, int, int, short, short, short, ...)`: **variadic**, and differently typed from the GCC2 tree's fixed seven-parameter `(const char*, int, const char*, short, short, int, short)` (`os9forkc` there takes eight). All three copies are character-identical, so they are one original rather than three witnesses. Read that as the Microware side documenting a variadic call and refusing to prototype it, with GCC2 having re-derived a fixed prototype for it — so a GCC2 arity is not corroboration. **Which arity the library actually implements is unmeasured**; pass arguments the way working period code does rather than trusting any header, and see the `system()` note below. |
| `exit`/`_exit` | `exit()` flushes stdio buffers first; `_exit()` doesn't. |
| `wait(int *status)` | Waits for a child to terminate. |
| `setpr(pid, priority)` | Priority 0–255. |
| `sleep(seconds)` | Actually delays in **ticks**, not true seconds — tick duration is clock/hardware-dependent (68k systems typically run 100Hz/~10ms ticks, see os9-systems-dev kernel-internals; 6809 CoCo/Dragon systems commonly derive 60Hz/~16.66ms ticks from video vertical sync) — `sleep(0)` sleeps indefinitely; `sleep(1)` gives up time slice but may not wait a full tick. |
| `kill(pid, signal)` / `intercept(handler)` | `intercept()` installs a signal handler function. |
| `system(char *cmd)` | Passes the string to the OS-9 shell; blocks until it completes. **Max 80 characters** — use `os9fork()` directly for anything longer. **It may launch nothing at all from a program you build yourself** — see below. |

### `system()` may launch nothing, and the return value will not tell you

**`system()` is environment-dependent here — verify it before relying on it.**
`Live` (os9exec), one binary built with the SDK's `cc` and run unchanged in two
environments:

| Where | Child ran? | `system()` returned |
|---|---|---|
| SDK disk, Microware's `shell` | **yes** — output appeared, redirect file created | 0 |
| freeware disk, `bash`, `SHELL=/dd/CMDS/ksh` | **no** — no output, no redirect file | 0 |

So the return value is worthless as a signal: the failing case returned **0**,
which reads as success. A large address-like value (640552) has also been seen
from the failing case. Neither tells you anything.

**The reliable diagnostic is a redirection inside the command string.** Put one
there and check whether the file appears:

```
system("list pctl.c >sysprobe.out")   -> no sysprobe.out  =>  no shell ran
```

That distinguishes "nothing ran" from "the child ran and printed nothing",
because a shell creates the redirect target *before* running the command — even
a command that does not exist leaves an empty file behind. A writable directory
and no file therefore means the command string was never interpreted at all.

Ruled out by measurement, so do not re-investigate: it is not the trap-free
build (a `cio`-linked build fails the same way), and not `wait(0)` versus
`wait(&status)` (identical). Period-built binaries shell out correctly on the
disk where freshly built ones do not. The mechanism is unresolved, `Flag`.

**The workaround is clean, and is verified to run** — fork the command
yourself, which is what `system()` would have done. `Live` (os9exec): this
returned a pid, the child's output appeared, and `wait` reported status 0:

```c
extern int os9exec(), os9fork(), wait();
int status = 0;

if ((pid = os9exec(os9fork, av[0], av, environ, 0, 0, 3)) < 0)
        return -1;
wait(&status);
```

**`os9exec()` takes a fork function as its first argument** — a *pointer*,
which is why `os9fork` appears bare with no parentheses. It is a wrapper that
calls the fork routine you nominate, so the name is passed as a value, never
invoked here. Its prototype, from the SDK's own `DEFS/os9lib/stdlib.h`:

```c
os9exec(int (*procfunc)(), char *, char **, char **, unsigned int, short, short)
```

Two things follow, and both are traps:

- **Do not collapse it into a direct `os9fork(...)` call.** The two take
  different arguments in every position, and under K&R rules the wrong one
  compiles silently and misbehaves at run time rather than failing to build.
- **The fork function has more than one name, and period code mostly uses the
  other one.** `os9forkc` sits in that slot in five of six archive sources
  measured on one disk (smail, `eo`, netpbm, `sc`, forum9), `os9fork` in the
  sixth. Both work, as a function-pointer argument should.

The trailing `0, 0, 3` is **measured as used, not documented**: the prototype
gives the types, six independent period sources pass exactly these values, and
it works — but what the `unsigned int` and the two `short`s select has not been
traced here, and the library header leaves the fork prototypes commented out.

The honest limitation of the whole approach: no shell is involved, so a
redirection or pipe written *inside* the command line is not interpreted. Build
the argument vector instead.

### The Unix process surface is mostly absent — check before you plan a port

The first thing to establish about a Unix program is whether the calls it is
built on exist here at all. Most of the process and job-control surface does
not. `Source`, scanning `clib.l` and `unix.l` for exported symbols:

| Unix call | here? | what there is instead |
|---|---|---|
| `fork()` | **no** | `os9fork()` (clib) — see the entry above for its arity |
| `wait()` | **no** | pair `os9fork` with the OS-9 wait; see `common/ipc.md` |
| `pipe()` | **no** | named pipes, `/pipe` (`common/ipc.md`) |
| `popen()`/`pclose()` | **no** | nothing; build it from `os9fork` + `/pipe` |
| `dup()`/`dup2()` | **no** | `os9exec`'s path arguments |
| `kill()` | **no** | `F$Send`; `getpid()` *is* present in both libraries |
| `sleep()` | **no** | `tsleep()` (unix.l), in **ticks** — with **bit 31** set it counts 256ths of a second, the same encoding as `F$Alarm` (`68k/syscall-reference.md`) |
| `execl()` | unix.l | **but it is a CHAIN, not an exec after a fork** — see below |
| `getcwd()`/`getwd()` | **no** | read the directory files and climb; see "No `getcwd`" in `common/unix-differences.md` |

**`execl()` replaces your process.** `Live` (os9exec): a program printing
`BEFORE execl`, calling `execl("/h0/CMDS/echo", "echo", "CHILD-RAN", 0)`, then
printing `AFTER` produced `BEFORE execl` and `CHILD-RAN` and **never printed
`AFTER`** — control does not come back. A Unix idiom that forks and then `exec`s
in the child will, transcribed literally, terminate the parent.

**Why, and how to get the other behaviour.** `os9exec()` takes its process-
creating function as its first argument (see the `os9exec()` entry below), and
`chain`/`chainc` are the chaining counterparts of `os9fork`/`os9forkc` —
`Source`, declared beside them in `os9lib/stdlib.h` in the same unprototyped
style, with `chain` exported by `clib.l` and `chainc` by `unix.l`. A `unixlib`
`execl` built as `exit(os9exec(chainc, ...))` therefore chains by construction.
**Pass the fork function instead of the chain function and the caller survives.**
One caution from the same scan: `os9forkc` is *declared* in that header but
exported by **neither** library, so do not reach for it as the `unix.l`-side
pairing.

**So a program built around a coprocess cannot be ported by substituting calls.**
Anything that forks a helper and talks to it over a two-way pipe — a front end
driving `bc`, a pager, a filter pipeline built in C — needs restructuring around
`os9fork` plus named pipes, not a compatibility shim.

### `<signal.h>` defines five signals, and job control is not among them

`Source` (SDK `DEFS/signal.h`), the complete list:

| name | value |
|---|---|
| `SIGKILL` | 0 — cannot be caught or ignored |
| `SIGWAKE` | 1 |
| `SIGQUIT` | 2 — keyboard abort |
| `SIGINT` | 3 — keyboard interrupt |
| `SIGHUP` | 4 — modem hangup |

With `SIG_DFL` 0 and `SIG_IGN` 1. **`SIGTERM`, `SIGSTOP`, `SIGCONT` and
`SIGTSTP` do not exist here**, so job-control handlers cannot be ported — they
have to be compiled out. Note also that a program quitting via
`kill(getpid(), SIGINT)` has no `kill()` to call and must invoke its own cleanup
path directly.

## `popen()` is not in this C library at all

Measured, because the gap was worth closing. On the v2.4-era SDK checked:

- `Source`: **no library exports it.** Scanning every `LIB/*.l` for `popen` and
  `pclose` finds neither — not `clib.l`, not `cio.l`, not `unix.l`.
- `Source`: **Microware's `<stdio.h>` does not declare it.** The only
  declaration on the disk is in `DEFS/GCC2/stdio.h`, a different toolchain's
  header — and no GCC2 library is present to satisfy it.
- `Live` (os9exec): a program calling `popen()` compiles with
  `**** warning - illegal pointer/integer combination ****` at the assignment —
  the tell that the function is undeclared and assumed to return `int` — and
  then fails at link:

```
Symbol 'popen' unresolved.
Symbol 'pclose' unresolved.
```

**So do not plan a port around `popen()` here.** Use `os9fork`/`os9exec` with an
explicit argument vector, or a pipe set up by hand (`common/ipc.md`), and treat
the warning above as the early signal — it appears at compile time, before the
link error names the problem.

There is a third-party account, `Hearsay`, of a `popen()` failing at run time
with a distinctive message:

    popen of "cccp ..." failed!

with the reported cure being to put the wanted program in the **data** directory
rather than on the execution path. That account cannot be about this library,
since a build here does not reach run time. It most likely describes a program
built with the GCC2 toolchain, whose header does declare `popen`. **Unmeasured,
and now known to be out of scope for a Microware `cc` build** — if you meet that
message, establish which toolchain and which library the program was built with
before treating the directory advice as a rule.

## Startup & Arguments

Every C program is linked against `LIB/cstart.r` first — the compiler
driver puts it at the front of the link file list automatically. This
module — built from `C/SOURCE/cstart.a` — supplies a root psect holding
the program's real OS-9 entry point: it runs startup initialization and
then calls `main()`.

Part of what that startup code does is convert OS-9's single parameter
string into `argc`/`argv` for `main(int argc, char *argv[])`: it splits on
whitespace, and a quoted substring (single or double quotes; use the other
quote type if the string itself contains one) is kept together as one
argument. E.g. the OS-9 parameter line `foo "bar baz" qux` becomes `argv =
{progname, "foo", "bar baz", "qux"}`, `argc = 4`.

## Process Memory Model

**Stack:** reserved per function call (locals, return address, register
temps); collision with the data area halts the program with `*** stack
overflow ***` on stderr. **Data area:** initialized statics/globals, plus
uninitialized ones (zeroed at startup) — addressable via the linker symbols
`&edata`/`&end`. **Parameters:** sized via the `-m` linker flag. **Free
memory:** whatever's left after static/stack allocation feeds the
`malloc()` pool (extendable via `sbrk()`).

## Limitations

| Feature | Status |
|---------|-------|
| `stdlib.h` (full) | No `rand()` (`Live` (os9exec): unresolved at link), and no `abs()`/`div()` (`Manual`). But `atoi()`/`atol()` **are** present and work — `Live` (os9exec): `atol("77")`→77, `atoi` likewise |
| `strings.h` | Use this, not `string.h` (different API: `index`/`rindex` not `strchr`/`strrchr`) |
| `ctype.h` (full ANSI) | Missing `isgraph()` and other ANSI additions; link errors, not compile errors |
| `stat.h` (absent entirely) | **`Live` (os9exec):** there is no `stat.h` on the 68k `DEFS` — `#include <stat.h>` fails to open. File mode bits are in `<modes.h>` (owner/public only, no group class) |

**Baseline:** K&R C — no enforced prototypes, no cross-file type checking.

## References

- Official Microware C Compiler manual (1983, 6809 edition) and "The OS-9
  Primer" (cross-checked against each other; the Primer also covers the
  later "Ultra C" compiler)
- **"The C Programming Language"** (Kernighan & Ritchie; K&R C is the
  baseline here)
- OS-9 v2.4 Technical Reference Manual (module header language-code
  values, syscall semantics underlying `os9fork()`/`sbrk()`)
- The OS-9 Guru, section 3.2.12 (`cstart.r` / linker startup file)

**Caution when consulting Microware C manuals directly:** the surviving
manuals cover both the 6809 and 68k compilers and sometimes blend them
without marking which architecture a detail applies to (e.g. `int` size,
"direct page" memory — the latter is always 6809). When in doubt on a
foundational claim, verify live on a 68k toolchain rather than trust a
single passage.
