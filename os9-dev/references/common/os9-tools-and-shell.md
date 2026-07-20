# OS-9 Shell and Utilities

Shell syntax, line editing, terminal configuration, and the standard utility
set. Architecture-independent unless a row says otherwise.

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
| `<path` `>path` `>>path` | Redirect stdin / stdout / **stderr**. `>>` is NOT append — it redirects the standard error path. Output modifiers: `>path` fails if file exists (create only); `>+path` appends to existing or creates; `>-path` truncates existing or creates. Combine freely: `cmd >out >>err`. `Live`: tested on NitrOS-9. |
| `#n` or `#nK` | Raise the process's memory allocation (both forms are kilobytes on 68k). Ignored if smaller than the module-header default; applies to that one command only. C programs use the extra purely as stack. Classic use: `basic09 #32k` when a program blows the default workspace |

Wildcards `*` (any string) and `?` (one character) are expanded by the shell
itself via `F$CmpNam`; the program receives matched names only.

## Built-in commands

| Built-in | Effect |
|---|---|
| `chd <dir>` / `chx <dir>` | Set current data / execution directory (see `unix-differences.md` for the two-directory model). `chd` with no argument returns to the home (login) directory; `chx` with no argument is a no-op |
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

## Control keys and line editing

Default assignments — every one remappable per-device via `tmode`/`xmode`:

| Key | Function |
|---|---|
| Ctrl-A | Recall previous input line, unexecuted, cursor at end — backspace and retype to edit, Return to submit. (This is the history mechanism; there are no arrow keys) |
| Ctrl-D | Redisplay the line being typed (hardcopy-terminal aid) |
| Ctrl-H / Backspace | Erase previous character |
| Ctrl-X | Discard the whole line being typed |
| Ctrl-W | Pause output; any key resumes (distinct from page pause below) |
| Ctrl-S / Ctrl-Q | XOFF/XON flow control, same as Unix |
| ESC (or Ctrl-[) | End-of-file on terminal input; on a blank shell line, exits the shell |
| Ctrl-C | Interrupt signal (code 3). A program with no intercept handler dies; the shell moves the foreground program to the background |
| Ctrl-E | Abort signal (code 2) — the "actually kill it" key |

Ctrl-C/Ctrl-E work any time, not just at input prompts. Unix-habit
inversions (Ctrl-C ≠ kill, ESC ≠ harmless) are tabulated in
`unix-differences.md`; the arrow-key/ESC hazard and the `tmode eof=04`
remedy are in `using-os9exec-repl.md`.

## tmode, xmode, page pause

- `tmode` changes the option bytes of an **open path** — immediate, and
  gone when that path closes. `xmode` (SCF/GFM devices) updates the
  **in-memory device descriptor** — takes effect at once and sticks
  across path open/close until reboot; not permanent (that takes editing
  the descriptor file or a new boot). Serial hardware settings
  (`baud`/`par`/`cs`/`stop`/`type`) need `deiniz` → `xmode` → `iniz`.
  Settable: control-key assignments, echo, backspace behavior, page
  pause, EOF character, etc. — full parameter table in
  `utility-usage.md`.
- Page pause (`tmode pause` / `tmode nopause`): output halts after each full
  screen until a key is pressed. Lines longer than the screen width wrap
  without being counted, so the pause point drifts on wrapped output.

## Standard utility set

Names below are the Professional OS-9 v2.4 (68k) set; most exist on 6809 as
well. `help <name>` (or `<name> -?`) prints usage for any of them.
**Per-command syntax and option letters: `utility-usage.md`** — read it
before invoking a utility with options rather than guessing flags.

**Files and directories:** `attr` (show/change permissions — bare `attr <path>`
prints an 8-character string, `Live`-decoded 2026-07-19: positions 1-4 are
`d`/`s`/`pe`/`pw` (directory, sharable, public-execute, public-write) and
5-8 are `pr`/`e`/`w`/`r` (public-read, owner-execute, owner-write,
owner-read), each either the letter or `-`; e.g. `----r-wr` = no
directory/sharable/public-exec/public-write bits, public-read granted,
owner has write+read but not execute. `attr -e` needs more privilege than
the bare form — `Live`: it failed `E$FNA`/214 in a session where the plain
form succeeded on the same file), `build` (create
a small text file from console input, `?` prompt per line, EOF ends),
`copy`, `del`, `deldir` (recursive directory delete), `dir` (`-e` for full
listing), `dsave` (emit a procedure file that copies a directory tree),
`dump` (hex/ASCII file dump), `edt` (line editor), `list` (print text file),
`makdir`, `merge` (concatenate files to stdout), `pd` (print working
directory), `pr` (paginated printing), `rename`, `touch`, `tr` (character
translate), `cmp` (binary compare: offset, hex values, ASCII per mismatch; `-b` buffer
size, `-s` silent summary),
`cfp` (apply a command template across many files), `grep`, `qsort`.

**Modules and memory:** `load` (make a file's modules memory-resident),
`link`/`unlink` (adjust a resident module's link count), `save` (write a
resident module back to a file), `ident` (decode a module's header: type,
language, attributes, CRC check), `fixmod` (recompute a patched module's CRC
and header parity), `mdir` (list the module directory; `-e` for details),
`mfree` (free memory report), `dump` (works on modules too).

**Processes:** `procs` (process list with group.user, priority, state),
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
`#<size>k` modifier behavior is additionally `Live` on os9exec.
`chd`-with-no-argument behavior: `Hearsay`, not yet `Live`.
