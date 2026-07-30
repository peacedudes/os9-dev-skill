# OS-9 Shell and Utilities

Shell syntax, line editing, terminal configuration, and the standard utility
set. Architecture-independent unless a row says otherwise — except the
utility catalog at the end, which is the 68k set with 6809 noted alongside.

## Shell model

- The shell is an ordinary unprivileged program, not part of the kernel.
  Multiple shells run concurrently; the default shell can be replaced (e.g.
  `MShell`).
- Each shell has private state: current directories (`chd`/`chx`), prompt,
  options. Child shells start with defaults — a child's changes never
  propagate back to the parent.
- The login shell executes `.login`/`.logout` in its own context, so their
  environment changes persist for that shell. Any shell forked afterward is
  a separate instance.

## Command line anatomy

`keyword params modifiers` — separators may join multiple commands. The
shell strips metacharacters (`;` `&` `!` `<` `>` `>>` `#` `*` `?`) from the
argument text before the program sees it; quote them to pass literally.

| Separator | Effect |
|---|---|
| `;` | Sequential — wait for each command before the next |
| `&` | Concurrent — commands run simultaneously in the background |
| `!` | Pipeline — connect stdout of the left command to stdin of the right. **Pipe is `!`, never `\|`** — `\|` is not a metacharacter at all and fails silently. Chains: `a ! b ! c` |

| Modifier | Effect |
|---|---|
| `#n` or `#nK` | Raise the process's memory allocation (both forms are kilobytes on 68k). Ignored if smaller than the module-header default; applies to that one command only. C programs use the extra purely as stack. Classic use: `basic09 #32k` when a program blows the default workspace |

### Redirection — `>>` is stderr, and append is `>+`

**To append to a file, use `>+`.** `>>` does *not* append on OS-9; it
redirects the standard error path. This is the single most common Unix
reflex to get wrong here, and it fails quietly — you get a log full of
error text and an original file that was never touched.

| Form | Redirects | Notes |
|---|---|---|
| `<path` | stdin | |
| `>path` | stdout | **Create only — fails if the file already exists** |
| `>+path` | stdout | **Append** to an existing file, or create it. The Unix `>>` |
| `>-path` | stdout | Truncate an existing file, or create it. The Unix `>` |
| `>>path` | **stderr** | *Not* append |
| `>>>path` | stdout **and** stderr | Both into one target |
| `<>>>path` | stdin, stdout, stderr | All three |

Combine freely: `cmd >out >>err` sends output and errors to separate files.

`Live` (NitrOS-9, os9exec): a failing `del`'s error text went to
`>>` (`del: can't delete '...'`, 40 bytes captured) but *not* to `>` (0
bytes) — direct confirmation that `>`=stdout, `>>`=stderr. `cmd >>>/nil`
swallows a stderr banner. `<>>>path` is owner-stated and accepted live —
note the shell still prints a failed child's exit status on its *own*
stderr, which is not the child's and looks like a leak.

`;`/`&`/`!` are also `Live` (os9exec) (`echo A;echo B` both ran; `echo hello !
tr a-z A-Z` → `HELLO`; `echo A & echo B` both ran).

Wildcards `*` (any string) and `?` (one character) are expanded by the shell
itself via `F$CmpNam`; the program receives matched names only.

**A pattern matching nothing aborts the command.** The shell prints `Wildcard
match failed for command '<name>'` and the program never runs at all, where a
Unix shell would hand the unmatched pattern through as a literal argument —
`Live` (os9exec), from both `list nosuchprefix*` and `echo ?`.

**The shell performs no variable substitution.** `$FOO` reaches the program as
those four characters even after `setenv FOO barvalue` — `Live` (os9exec).
Those two rules combine to make the borrowed Unix idiom `echo $?` fail with a
*wildcard* error, which points nowhere near the real cause: there is no
exit-status variable to expand, and the `?` is then read as a one-character
wildcard that matches no file.

## Built-in commands

| Built-in | Effect |
|---|---|
| `chd <dir>` / `chx <dir>` | Set current data / execution directory (see `unix-differences.md` for the two-directory model). `chd` with no argument returns to `$HOME` (the `HOME` environment variable, not the password-file data dir — see below); `chx` with no argument is a no-op |
| `ex <name>` | Replace this shell with the named program (no new process) |
| `w` / `wait` | Wait for any child / all children to terminate |
| `kill <pid>` | Send the kill signal to a process |
| `setpr <pid> <pri>` | Change a process's priority |
| `profile <file>` | Execute a file's commands **in the current shell**, so its `setenv`/`chd`/prompt changes persist — unlike running the file by name, which forks a child shell whose changes evaporate |
| `set <opts>` | Change shell options mid-session (no leading `-` needed: `set np`) |
| `setenv` / `unsetenv` / `printenv` | Set, remove, list environment variables. Names are case-sensitive (`PATH` ≠ `path`). `unsetenv` removes the variable outright |
| `logout` | End the login shell/session (runs `.logout`) |

Shell invocation options (also settable via `set`): `t`/`nt` echo input
lines on/off, `p="..."`/`np` prompt on/off, `x`/`nx` abort-on-error on/off.
`Live` (os9exec): all three confirmed via `set` — `set t`
echoed each command line before running it; `set np` suppressed the `$`
prompt for subsequent commands; `set x` aborted the shell on the first
command error (a following `echo` never ran) while `set nx` continued past
the error. (`p`'s prompt *string* form `p="..."` not separately exercised,
only the on/off behaviour.)

- The `PROMPT` environment variable holds the prompt string; a leading `@`
  expands to the shell-nesting level (tracked in `_sh`), so nested shells
  show `1.`, `2.`, … prefixes. Shipped default prompt is `$`.
- Login (via `tsmon`) sets `PORT` (terminal), `HOME` (from the password
  file), `SHELL`, and `USER` automatically; single-user systems set them in
  a startup procedure file.

## Procedure files

A file of command lines, run by typing its name — the shell forks a child
shell to execute it, so built-ins inside it (`chd`, `setenv`, …) cannot
disturb the invoking shell. Use `profile` when you *want* the changes to
stick. Relative procedure-file lookups resolve against the data directory.

**A procedure file does not need the execute attribute.** `Live` (os9exec):
one with `----r-wr` — read and write, no execute bit at all —
ran correctly when invoked by name. The shell falls back to reading a
non-module as command text, and that path does not consult the execute bit
the way forking a real module does. So don't "fix" a working procedure file
by granting it `e`; do set `pr` (and `pe` only if a module) when someone
else must run it. Not separately confirmed on 6809, though the mechanism is
kernel-level rather than port-specific.

**Line endings are CR (0x0D), and a procedure file with LF endings fails
silently** — `Live` (os9exec). OS-9 does not treat LF as a terminator, so the whole
file is *one line*: the shell echoes its entire contents and executes
nothing, with no error message of any kind. Host-generated procedure files
must be converted (`tr '\n' '\r'`, or `flip -m` on the guest) before use.

## Naming convention: capitalized directories

OS-9 convention capitalizes directory names and leaves file names lowercase
— `CMDS/`, `SYS/`, `DEFS/` beside `startup`, `password`, `motd`. Not
enforced by the filesystem, but followed throughout the system disk; ignoring
it in shipped material reads as foreign. Also noted for the 6809 utility set
in `6809/utility-usage.md`.

## Control keys and line editing

Default assignments — every one remappable per-device via `tmode`/`xmode`:

| Key | Function |
|---|---|
| Ctrl-A | Recall previous input line, unexecuted, cursor at end — backspace and retype to edit, Return to submit. (This is the whole history mechanism: the line editor has no cursor movement, so there is nothing for an arrow key to drive. Do **not** read that as "the terminal has no arrow keys" — a CoCo has four, and its LEFT ARROW *is* Ctrl-H; see `6809/using-nitros9-repl.md`) |
| Ctrl-D | Redisplay the line being typed (hardcopy-terminal aid) |
| Ctrl-H / Backspace | Erase previous character |
| Ctrl-X | Discard the whole line being typed |
| Ctrl-W | Pause output; any key resumes (distinct from page pause below) |
| Ctrl-S / Ctrl-Q | XOFF/XON flow control, same as Unix. **SCF consumes both — a reading program never sees them**, so a stray `$13` in a byte stream pauses output with nothing in the data and no error to show for it (`xon=`/`xoff=` remap them per path) |
| ESC (or Ctrl-[) | End-of-file on terminal input; on a blank shell line, exits the shell |
| Ctrl-C | Interrupt signal (code 3). A program with no intercept handler dies; the shell moves the foreground program to the background |
| Ctrl-E | Abort signal (code 2) — the "actually kill it" key |

Ctrl-C/Ctrl-E work any time, not just at input prompts. Unix-habit
inversions (Ctrl-C ≠ kill, ESC ≠ harmless) are tabulated in
`unix-differences.md`; the arrow-key/ESC hazard is in
`using-os9exec-repl.md`.

**Tip — switching between OS-9 and Unix all day.** Two `tmode` settings
remove most of the friction, and both are worth making immediately:

| Want | Set | Why |
|---|---|---|
| Ctrl-D ends input, as in Unix | `tmode eof=04` | OS-9's EOF is ESC ($1B) |
| Backspace erases | `tmode bsp=7F` | modern terminals send DEL ($7F) for the Backspace key; OS-9 expects BS ($08), so out of the box Backspace inserts a literal character instead of erasing |

`Live` (os9exec): before `bsp=7F`, `echo hellox<DEL>` prints `hellox` plus a
stray $7F; after, the echo shows the BS-space-BS erase and it prints `hello`.
`bse=`/`bsb` tune the echo side separately — see the parameter table in
`common/utility-usage.md`.

Put them in the account's `.login`, which is read from its **data** directory,
to get them every session. Note `tmode` acts on the open **path**, so a change
outlives the process that made it — it persists for the rest of the session,
including across `logout`. That is what makes `.login` the right place for it,
but it also means a script or harness must not assume ESC is still EOF.

## tmode, xmode, page pause

- `tmode` changes the option bytes of an **open path** — immediate, and
  gone when that path closes. `xmode` (SCF/GFM devices) updates the
  **in-memory device descriptor** — takes effect at once and sticks
  across path open/close until reboot; not permanent (that takes editing
  the descriptor file or a new boot). Serial hardware settings
  (`baud`/`par`/`cs`/`stop`/`type`) need `deiniz` → `xmode` → `iniz`.
  `tmode baud=<n>` is a partial exception — it does write the open path's
  own baud byte without changing the hardware rate, and its argument is a
  literal bits-per-second value rather than the descriptor's code; see
  `common/utility-usage.md`'s `baud=` note.
  Settable: control-key assignments, echo, backspace behavior, page
  pause, EOF character, etc. — full parameter table in
  `common/utility-usage.md`.
- Page pause (`tmode pause` / `tmode nopause`): output halts after each full
  screen until a key is pressed. Lines longer than the screen width wrap
  without being counted, so the pause point drifts on wrapped output.

## Standard utility set

Names below are the Professional OS-9 v2.4 (68k) set; most exist on 6809 as
well, often with different option letters. `help <name>` (or `<name> -?`)
prints usage for any of them. **Per-command syntax and option letters:
`common/utility-usage.md` for 68k, `6809/utility-usage.md` for 6809** — read
the right one before invoking a utility with options rather than guessing
flags.

**Files and directories:** `attr` (show/change permissions —
output-string decoding and the `-e` privilege gotcha, both `Live`:
`common/utility-usage.md`'s `attr` entry), `build` (create
a small text file from console input, `?` prompt per line, EOF ends),
`copy`, `del`, `deldir` (recursive directory delete), `dir` (`-e` for full
listing), `dsave` (emit a procedure file that copies a directory tree),
`dump` (hex/ASCII file dump), `edt` (line editor), `list` (print text file),
`makdir`, `merge` (concatenate files to stdout), `pd` (print working
directory — 6809 spells it `pwd`, with `pxd` for the execution directory),
`pr` (paginated printing), `rename`, `touch`, `tr` (character
translate), `cmp` (binary compare: offset, hex values, ASCII per mismatch; `-b` buffer
size, `-s` silent summary),
`cfp` (apply a command template across many files), `grep`, `qsort`.

**`pd` and `cfp` have no syntax entry in either `utility-usage.md`** — the
sources behind those files don't cover them. Use `-?` or `help <name>` on a
live system rather than hunting for a table row that isn't there.

**Modules and memory:** `load` (make a file's modules memory-resident),
`link`/`unlink` (adjust a resident module's link count), `save` (write a
resident module back to a file), `ident` (decode a module's header: type,
language, attributes, CRC check), `fixmod` (recompute a patched module's CRC
and header parity), `mdir` (list the module directory; `-e` for details),
`mfree` (free memory report), `dump` (works on modules too).

**Processes:** `procs` (process list with owner ID, priority, state — shown
as `group.user` on 68k, a flat user number on 6809),
`kill`, `setpr`, `sleep`, `w`/`wait`, `ex`.

**Disks and system:** `format` (three phases: surface scan, identification
sector + allocation map, root directory), `free` (disk space), `dcheck`
(filesystem consistency), `os9gen` (build a bootable disk), `backup`
(disk-to-disk copy), `fsave`/`frestore` (incremental tape backup/restore),
`tape`/`tapegen`, `diskcache`, `iniz`/`deiniz` (attach/detach a device —
opening devices early at startup also avoids memory fragmentation), `devs`
(attached-device list), `irqs` (IRQ-poll table), `events` (event-table
list), `date` (`-j` Julian), `setime` (start the system clock — run it at
boot; multitasking scheduling depends on the clock; `setime -s` reads a
battery-backed clock), `tmode`/`xmode`, `tsmon` (watch terminals for
logins), `login`, `echo`, `break` (enter the ROM debugger, superuser),
`moded` (edit module option tables), `binex`/`exbin` (module ↔ S-record
conversion), `romsplit` (split images for ROM burning), `make`, `shell`.

Utilities live in `CMDS` and are found via the execution directory and
`PATH` — see `unix-differences.md` for why `chd` alone never makes a
program runnable.

---
Sources: Using Professional OS-9 v2.4 (shell, basic commands, utilities);
The OS-9 Primer (environment variables, built-ins); The OS-9 Guru §2.1–2.2;
OS-9 v2.4 Technical Reference Manual; Technical I/O Manual v2.4. The
`#<size>k` modifier behavior is additionally `Live` (os9exec).
Bare `chd` (to `$HOME`, the environment variable rather than the
password-file data directory) and bare `chx` (a no-op) are both `Live` (os9exec).
