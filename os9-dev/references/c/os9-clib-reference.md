# OS-9 C Standard Library Reference

For Microware C Compiler targeting 68000/6809 OS-9 systems.

## Overview

The Microware C library bridges OS-9 system calls and UNIX-style C I/O patterns.
The startup routine converts the OS-9 parameter string into `argc`/`argv`.
All standard I/O is path-based (paths 0=stdin, 1=stdout, 2=stderr) and
uses OS-9 `I$Open`, `I$Read`, `I$Write` calls under the hood.

Most wrapper functions follow UNIX naming for portability, but parameters
and return values may differ from their raw OS-9 equivalents—verify against
the manual's cross-reference table between C names and raw service-request
names (`F$xxx`/`I$xxx`).

## Standard Headers Available

| Header | Notes |
|--------|-------|
| `<stdio.h>` | File I/O, printf/scanf; defines `FILE`, `stdin`, `stdout`, `stderr` |
| `<stdlib.h>` | `exit()`, `system()`; limited (no `rand()`, etc.). **Not on Ultra C's default `CDEF` include path** — `Live` (68k): `#include <stdlib.h>` fails `cpp` with `can't open /h0/DEFS/stdlib.h (err=216)` under the standard `cc` toolchain; the file exists on-disk only under the gcc2-specific `DEFS/os9lib`/`DEFS/GCC2` trees (`-I/h0/DEFS/os9lib`, see `os9-c-compiler-setup` in project history). K&R doesn't require a prototype for `exit()`, so dropping the include and declaring nothing works fine |
| `<ctype.h>` | Character classification (macros, K&R-era coverage) |
| `<setjmp.h>` | `setjmp()`, `longjmp()` |
| `<time.h>` | OS-9-specific system time (see "File Dates and Time Zones" below) |
| `<errno.h>` | OS-9 extensions: EFPOVR=40, EDIVERR=41, EINTERR=42 |
| `<module.h>` | OS-9 module linking |
| `<sgstat.h>` | OS-9 file status/setstat (`I$SetStt`) |
| `<stat.h>` | File status/mode bits (owner/public only, no group class) |

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
| `printf`/`fprintf`/`sprintf` | **Gotcha, `Flag` — wrong as stated for 68k**: this table claimed printing a `long` requires one call to `_pfltinit()` in the program first, and `float`/`double` requires `_prfloat()` first. `Live` (68k): calling `_pfltinit()` before a `%ld` fails to *link* outright (`Symbol '_pfltinit' unresolved`, `l68: error - unresolved references`) — not a silent no-op as claimed. Dropping the call entirely, `%ld` printed correctly with no marker function at all. Plausible cause, not independently confirmed: this file's own data-types table notes 68k's `int`/`long` are both 32-bit, unlike the 6809 C compiler manual (this claim's sole source) where `int` is 16-bit — a width-disambiguating marker may be meaningful on 6809 but dead weight on 68k, same cross-architecture-noise pattern as other findings in this file's Pitfalls section. **6809 behavior unverified — do not assume this claim is also wrong there.** `_prfloat()`/float-double printing not independently re-tested on 68k either; treat as unverified rather than assuming it shares `_pfltinit()`'s fate. |
| `scanf`/`fscanf`/`sscanf` | Specs: `%d %o %x %u %f %e %g %c %s`, plus `%D %O %X` for long and `[...]` for character-set match. **Every argument must be a pointer** — passing a value instead of `&value` is an easy mistake the compiler won't catch. |
| `setbuf(FILE *fp, char *buffer)` | Call after `fopen()`, before any I/O. Pass `NULL` to disable buffering. `stderr` is always unbuffered by default. |
| `write(int path, char *buf, int count)` / `read(int path, char *buf, int count)` | Raw path-based I/O (OS-9 `I$Write`/`I$Read` directly, no `FILE *` or buffering) — the primitive underneath the numbered stdin/stdout/stderr paths (0/1/2). **Do not mix these with `printf`/`fprintf`/other stdio calls on the same path without an explicit `fflush()` in between.** `Live`: interleaving a raw `write()` with a buffered `fprintf()` on the same fd doesn't just reorder or drop output — the two calls' bytes physically overlay each other in the shared stdio buffer, corrupting both (e.g. `"raw write with fflush first\n"` came out as `"after writeith fflush first"` when a `printf` followed without a flush). `write()`/`read()` used alone, with no stdio calls sharing the same path, work correctly. |

## String Functions (`strings.h`, not `string.h`)

| Function | Notes |
|---|---|
| `strcat`/`strncat`/`strcmp`/`strncmp`/`strcpy`/`strncpy`/`strlen` | `strncpy` pads the remainder with nulls if the source is shorter than n. |
| `strhcpy` | Copy with a sign-bit string terminator (OS-9 specific). |
| `index(s, ch)` / `rindex(s, ch)` | OS-9/BSD names instead of ANSI's `strchr`/`strrchr`. |

**No bounds checking** — caller must ensure buffers are large enough. No `strstr()`.

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

## File Permissions (`<stat.h>`)

OS-9 has only two permission classes, **owner** and **public** — there is
no group class. `<stat.h>` reflects this deliberately: the group macros are
aliased directly onto the public ones (`S_IRGRP`/`S_IROTH` both `0x0008`,
`S_IWGRP`/`S_IWOTH` both `0x0010`, and so on). Code ported from Unix that
extracts a permission triple with the classic octal masks `0700`/`0070`/
`0007` misses OS-9's actual permission bits (`0x01`-`0x20`) entirely and
renders every permission as absent.

The aliasing is itself a hint: when rendering a Unix-style 10-character
mode string, mirroring the public bits into the group position matches
what the header already implies. A giveaway symptom: an `ls -l`-style
listing whose file-type character is right but whose permission bits are
all dashes means the *permission* decode is using Unix masks — independent
of whatever else might be wrong with the type decode.

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
| `os9fork(char *modname, int paramsize, char *paramptr, int type, int lang, int datasize)` | Not a standard C function — direct OS-9 process creation. `type`=1 is "program". `lang`=1 is native object code for whatever CPU the running system is (the module header's `M$Lang` field) — on a 6809 system that's 6809 object code (code 4 there is C I-code instead); on 68k, code 1 is 68K object code. It's not a single cross-architecture enum where one number always means "6809." Returns child PID or -1. Parent does **not** automatically wait — pair with `wait()`. **Known gap:** this skill gives no rule for how `modname` is resolved (a full path was used successfully in live testing, e.g. `/dd/forktest`; whether a bare name also resolves via the module directory/`PATH` the way Shell does is untested) or how to size `datasize` (a `4096`-byte guess worked live but isn't derived from any documented rule — compare `M$Mem` in `module-format.md`, which is the analogous field for a linked module's own declared requirement). |
| `exit`/`_exit` | `exit()` flushes stdio buffers first; `_exit()` doesn't. |
| `wait(int *status)` | Waits for a child to terminate. |
| `setpr(pid, priority)` | Priority 0–255. |
| `sleep(seconds)` | Actually delays in **ticks**, not true seconds — tick duration is clock/hardware-dependent (68k systems typically run 100Hz/~10ms ticks, see os9-systems-dev kernel-internals; 6809 CoCo/Dragon systems commonly derive 60Hz/~16.66ms ticks from video vertical sync) — `sleep(0)` sleeps indefinitely; `sleep(1)` gives up time slice but may not wait a full tick. |
| `kill(pid, signal)` / `intercept(handler)` | `intercept()` installs a signal handler function. |
| `system(char *cmd)` | Passes the string to the OS-9 shell; blocks until it completes. **Max 80 characters** — use `os9fork()` directly for anything longer. |

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
| `stdlib.h` (full) | No `rand()`, `abs()`, `div()`; `atoi()`/`atol()` may be limited or absent |
| `strings.h` | Use this, not `string.h` (different API: `index`/`rindex` not `strchr`/`strrchr`) |
| `ctype.h` (full ANSI) | Missing `isgraph()` and other ANSI additions; link errors, not compile errors |
| `stat.h` (group permissions) | No group class on OS-9 — group macros alias public bits |

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
