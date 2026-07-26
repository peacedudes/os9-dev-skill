# 6809 OS-9 Utility Usage: Syntax and Options

Per-command syntax and option reference for the OS-9 Level Two (6809/CoCo,
Dragon, Gimix) utility set, built from the Level 2 Operating System Manual
and cross-checked against the two Level 1 Users Manuals (OS-9 Users Manual
1983, Gimix OS-9 Users Manual 1983) and the Farna CoCo Quick References
(only the 2nd edition is actually CoCo-specific — see `Sources:` footer).
The primary source is OCR-scanned and locally dirty in places — where a
detail couldn't be resolved against a second independent source it's
flagged below rather than stated as plain fact. On any live system,
`help <name>` is ground truth. Notation: `[..]` optional, `{..}` repeatable.
One-line "what it's for" descriptions: `common/os9-tools-and-shell.md`'s
"Standard utility set" section — written from the 68k catalog but notes
most entries exist on 6809 too; this file is the 6809-specific syntax/option
layer underneath it.

## Conventions shared by many utilities (stated once, not repeated below)

- **`-x`** — resolve the named file against the current **execution**
  directory instead of the data directory (`del`, `dir`, `ident`, and
  others).
- **`#n` / `#nK`** — memory/buffer allocation modifier: `n` is 256-byte
  pages by default, kilobytes if `K` is appended. Used by `backup`,
  `copy`, `dsave`, `os9gen`, and as a `shell` invocation modifier. More
  memory generally means fewer diskette swaps on single-drive setups and
  faster transfers, up to a documented ceiling (56K for `backup`/`copy`).
- **`-s`** — several commands overload `-s` for "single-drive mode":
  prompts the user to swap source/destination media between read and
  write passes instead of requiring two drives (`backup`, `copy`,
  `os9gen`).
- Several core commands are **shell built-ins**, not files in `CMDS`:
  `chd`, `chx`, `kill`, `setpr`, `ex`. `help <name>` still works for them.
- `help <name>` reads from `SYS/Helpmsg`; `error <n>` decodes an error
  number by reading `SYS/Errmsg`. Neither is universal `-?` the way 68k's
  convention is — only `wcreate` is sourced here with its own `-?`.

## File and directory utilities

- `attr <path> [<permissions>]` — permission letters: `r`/`w`/`e` (owner
  read/write/execute), `p` prefix for public (`pr`/`pw`/`pe`), `d`
  (directory), `s` (non-shareable, single-user-at-a-time), `a` (suppress
  the attribute printout after a change). Minus-prefix any letter to turn
  it off; no permission argument displays current attributes. **68k
  inverts this** (`Live` (NitrOS-9), both sides): there `-e` *sets* and `-ne` clears,
  so the identical `attr f -e` has the opposite effect per target —
  `common/utility-usage.md`. `Live` (NitrOS-9): bare `attr` prints no usage text on
  6809, so the spelling cannot be checked from the guest. Only the
  owner (or user 0) may change a file's attributes. Can convert an
  emptied directory back to a plain file; cannot do the reverse — use
  `makdir` to create a directory.
- `build <path>` — prompts `?` per line, writes each to the file; a blank
  line (bare Enter) ends it.
- `copy <path1> <path2> [-s]` — raw block transfer, does not add line
  feeds or other text-editing codes (use `list` for that). Destination
  must not already exist; created automatically. `-s` = single-drive
  mode (destination must be a full pathlist). `#n`/`#nK` memory modifier
  applies.
- `del [-x] {<path>}` — requires write permission on each file. Cannot
  delete a directory file directly: either empty it and `attr` it back to
  a plain file first, or use `deldir`.
- `deldir <path>` — recursively deletes a directory and everything under
  it. Prompts `l` (list contents via `dir` first), `d` (delete), `q`
  (cancel). Processes nested directories bottom-up; aborts on the first
  missing write permission. Internally invokes `dir` and `attr`, so both
  must be reachable from the current execution directory.
- `dir [e] [x] [<path>]` — `e` = extended listing (size, sector address,
  owner, permissions, last-modified date/time), `x` = list the execution
  directory instead of the data directory. No path defaults to the
  current data directory. Output format auto-adjusts for 32- vs
  80-column terminals.
- `makdir <path>` — parent directory needs write permission. A new
  directory starts with only `.` and `..` entries and all permissions
  enabled; OS-9 convention (not enforced) capitalizes directory names.
- `merge {<path>}` — concatenates files to stdout in the order given, with
  no line-feed insertion (raw copy); typically used with output
  redirection to combine files or fan out to a device.
- `rename <path> <newname>` — write permission required; cannot rename
  devices or the `.`/`..` entries.
- `cmp <path1> <path2>` — binary byte-for-byte compare; reports each
  differing offset and the two byte values, stops at EOF on either file,
  and prints a final tally of bytes compared vs. bytes differing.
- `list <path> {<path>}` — copies text file(s) to stdout in the order
  given, stopping at EOF of the last one; up to 199 characters of
  filenames fit on one command line. Text-aware unlike `copy` (no memory
  or single-drive modifiers of its own), so it's the usual way to print
  or page a file. The manual explicitly warns against pointing it at an
  executable module/program file — doing so can lock or crash the
  system — with "use DUMP instead" as its own stated alternative.

## Module and memory utilities

- `load <path>` — reads module(s) from a file into memory, registering
  each one's name in the module directory as it goes. When a same-name,
  same-type module is already resident, whichever copy — the one
  already there or the one just loaded — carries the higher revision
  number is the one that stays; loading an older revision over a newer
  resident one is a no-op.
  A pathlist with no drive name resolves against the current **execution**
  directory (the 6809 default, same surprise as 68k).
- `link <modname>` / `unlink {<modname>}` — `link` bumps a resident
  module's link count (module must already be loaded — use `load` first);
  `unlink` decrements it, and OS-9 deallocates the module once the count
  reaches zero. A module the caller both loaded and linked may need
  `unlink` twice. Treat both as **someone else's responsibility unless
  you were the one who ran `load`/`link` on that module in the first
  place** — decrementing a stranger's reference, or one `procs` shows
  still active elsewhere, yanks memory out from under a program that's
  still relying on it.
- `ident [-m] [-v] [-x] [-s] <path>` — `-m` = target is a module already
  in memory (not a file), `-v` = skip CRC verification, `-x` = resolve
  against the execution directory, `-s` = single-line-per-module format
  (edition byte, type/language byte, CRC status, name — `.` if the CRC
  verifies, `?` if not). The full (non-`-s`) format adds overall size,
  and for anything runnable (a program or a driver), also breaks out
  where its code begins and how much static storage it needs. Works
  across every module packed into a multi-module file, not just the
  first.
- `mdir [e]` — lists resident module names; `e` = extended (block number,
  in-block offset, size, type, revision, re-entrant flag, link count —
  all hex). Not every listed module is a runnable program; check the
  type byte before trying to execute an unfamiliar one.
- `mfree` — no options. Lists free memory blocks: block number, physical
  (extended) start/end address, size in blocks and in kilobytes. Block
  size is 8K. Free blocks for user data don't need to be physically
  contiguous — the MMU maps scattered blocks into a logically contiguous
  space.
- `modpatch [-s] [-w] [-c] <patchfile>` — patches modules already resident
  in memory. Shell-level flags: `-s` suppress echoing patchfile command
  lines, `-w` suppress warnings, `-c` compare/validate only, no write.
  The patchfile itself has its own single-letter command language:
  `l <modname>` (link the target module), `c <offset> <old> <new>`
  (replace one byte, offset is zero-based from module start, fails if
  `<old>` doesn't match what's there), `v` (recompute the CRC — required
  before the module is loadable again), `m`/`u` (mask/unmask IRQs while
  patching interrupt-handling code). In-memory patches may need the
  module re-initialized (or the system rebooted) to take effect, and
  don't survive a reboot at all unless saved with `save` and folded back
  into a boot file via `os9gen` or `cobbler`.
- `os9gen <devname> {<path>}` *(CoCo/Dragon Level 2 — this is the
  general-purpose boot-file builder)* — reads module pathlists (keyboard
  or redirected from a file, one per line, blank line/EOF ends the list),
  copies each into a temporary `Tempboot`, then deletes any existing
  `OS9Boot` and renames `Tempboot` onto it, recording the boot file's
  start/size in the disk's Identification Sector (LSN 0). The OS-9 kernel
  itself lands on Track 34; insufficient contiguous space there aborts
  with an error. `os9gen` needs a **freshly formatted** diskette — a
  fragmented `OS9Boot` is refused as unbootable. `#n`/`#nK` speeds the
  copy. `rename` must be present in the execution directory or already
  resident, since `os9gen` calls it internally to finish the swap. `config`
  is an alternative, guided way to build a custom system diskette for the
  same purpose.

## Process and environment

- `kill <procID>` — shell built-in. Callers may only kill their own
  processes; user 0 (superuser) can kill anything. A process blocked on
  I/O won't die until that I/O completes — if `procs` still shows it
  after `kill`, it's probably waiting on terminal input, not stuck.
- `setpr <procID> <priority>` — shell built-in. Priority is decimal 1
  (lowest) to 255 (highest); same same-user-ID-or-superuser rule as `kill`.
- `procs [e]` — snapshot of running processes (state changes fast, so
  it's a point-in-time view). Default shows only the caller's own
  processes; `e` shows every user's. Columns: user ID, process ID,
  priority, state, memory size (256-byte pages), primary module name,
  standard-input path.
- `pwd` / `pxd` — no arguments. `pwd` traces the full path down from
  root to wherever the **data** directory currently points; `pxd` traces
  that same path for the **execution** directory instead — each process
  keeps the two independently.
- `ex <modname> [<parameters>]` — shell built-in that **replaces** the
  shell in place (no new process forked), so any commands after it on the
  same line never run. Used to conserve memory when the shell's own
  process image would otherwise be duplicated — e.g. chaining straight
  into BASIC09 without keeping a resident shell around. If the
  replacement process itself later exits and no other shell is running
  on another device or window, OS-9 is left with zero processes and
  needs a hard reboot; the manual's own recovery trick for a
  now-shell-less device is to start a fresh one bound to it from a shell
  that's still alive elsewhere — `shell i=/term&` reinitializes `/term`
  after an `ex` there dead-ended it. The Level 2 manual's own syntax line
  gives a bare `ex filename`, with no modifiers clause at all; the two
  Level 1 manuals document a fuller `ex <modname> [<modifiers>]
  [<parameters>]` form. Likely just the Level 2 manual being terser about
  a command that passes its trailing arguments straight through to
  whatever it chains into, not a removed capability — nothing in either
  source suggests EX itself grew or lost an option between levels.
- `shell [<arglist>]` — the command interpreter itself: reads lines from
  stdin until EOF, then exits. Separators: `;` sequential, `&` concurrent
  (background), `!` pipe. Redirection: `<` input, `>` output, `>>`
  stderr, plus the less-common `<>` (stdin→stdout), `<<>>` (stdin→stderr),
  `>>>` (stdout→stderr). `#n`/`#nK` sets memory allocation for the
  invoked program. Built-in per-invocation parameters include `chd`,
  `chx`, `kill`, `setpr`, `i=<device>` (spawn an immortal process bound to
  a device), and `w` (block until a background child exits).
  **Append is `>+`** (`>-` truncates, plain `>` fails if the file exists) —
  see `common/os9-tools-and-shell.md` for the full redirection table.
- **Shell+ conditionals — `IF`/`THEN`/`ELSE`/`ENDIF`, and they are not
  baseline.** `Source` (NitrOS-9 `level1/cmds/shellplus.asm`, keyword and
  conditional tables): Shell+ adds `IF`, `THEN`, `ELSE`, `ENDIF` (spelled
  `FI` equivalently), `CLRIF`, plus `GOTO`, `ONERR`, `PAUSE`, `INC.`,
  `DEC.`, `PATH=`, and `L`/`-L`, `V`/`-V`. An unrecognised keyword prints
  `WHAT?`, so a script relying on these fails loudly rather than silently
  on a shell that lacks them — but **do not assume they exist** on an
  arbitrary OS-9/6809 system. Whether a given Microware-shipped shell has
  them is unconfirmed here; write portable material against the plain
  separators, or accept a visible failure.
- **`set x` (abort-on-error) is `Live` (os9exec) but was found
  unreliable on NitrOS-9** as the sole content of a procedure file
  (2026-07-25, while building the 6809 conformance suite). Treat
  abort-on-error as target-specific and verify before depending on it;
  the 68k entry in `common/os9-tools-and-shell.md` stands and is not
  contradicted by this.

## Devices, disks, system

- `iniz {<devname>}` — attaches and initializes a device driver; does
  **not** re-initialize a device already installed. Commonly run from
  `startup` so device static storage allocates early (top of memory),
  reducing fragmentation. Don't `iniz` a non-shareable device you're
  swapping in for `/p` — that path needs different handling.
- `deiniz {<devname>}` — the `iniz` counterpart; issues `I$Detach` for
  each device and frees its memory. Used together with `iniz` to remove a
  device or to bracket an `xmode` change on hardware settings `xmode`
  itself can't touch live (see the parameter table below).
- `free <devname>` — reports remaining space in 256-byte sectors,
  alongside the volume's label, when it was created, and its cluster
  size. On the Color Computer specifically, a cluster is always exactly
  one sector.
- `dcheck [-b] [-p] [-s] [-w=<path>] [-m] [-o] <devname>` — walks the
  directory/file tree, builds its own allocation bitmap from each file's
  segment list, and compares it against the disk's stored map: reports
  orphaned (allocated-but-unowned) clusters, duplicate allocations
  (a cluster claimed twice), and descriptor-sector inconsistencies.
  `-b` suppresses the orphaned-cluster listing, `-p` names the full
  pathlist for every questionable cluster it finds, `-s` shows only a
  file/directory count summary,
  `-w=<path>` sets where its `DCHECK<pp>0`/`DCHECK<pp>1` scratch files
  land (default the current data directory, `<pp>` = process number in
  hex), `-m` keeps those scratch files instead of deleting them, `-o`
  prints the valid option list. `Live` (all six letters, including `-s`'s
  meaning) — the primary source's own listing had these OCR-uncertain (a
  stray `-8`/`-0`), and the Level 1 manuals/Farna quick references had
  already agreed on the letters themselves without stating what `-s`
  does. Needs exclusive disk
  access to be trustworthy, and can't walk more than 39 levels of nested
  directories.
- `format <devname> [<options>]` — three-phase: physically initializes
  and divides the media into sectors, reads/verifies every sector
  (excluding any marked defective), then packs the three boot-critical
  structures — free-space map, root directory, identification sector —
  into Track 0's earliest sectors. Unlike elsewhere on the disk, a defect
  in one of those specific sectors is fatal rather than something the
  format pass can just route around. `-r` skips the
  ready-prompt and proceeds unattended. Vintage manual-documented forms:
  `-1`/`-2` (or, per the Level 1 manuals and Farna references, `-ss`/
  `-ds`) select single- vs. double-sided; density appears as both a bare
  `S`/`D` and as `-sd`/`-dd` across sources — the letter-vs-dash
  convention is unsettled between documentation generations. Track count
  is a bare decimal number (in quotes in at least one source, e.g.
  `'35'`); sector interleave is written `:<n>:`. A volume name up to 32
  characters, in double quotes, can be supplied or is prompted for, and
  is later visible via `free`. A write-protected target aborts with
  error 242. On a hard disk, drop `tmode -pause` first (restore with
  `tmode pause` after) or `format` will stall waiting for a keypress
  every time the screen fills during verification. `Live` (NitrOS-9, a
  modern rewrite — this syntax does not necessarily match vintage
  Microware `format`): `Format <devname> [R]
  [L] [E] ["name"] [1|2] ['cylinders'] [:interleave:] [/clustersize/]` —
  `R` ready (skip the prompt), `L` logical-format only, `E` enhanced
  format (20 sectors/track instead of 18, needs a matching `dmode`
  change first), bare `1`/`2` for sides (confirms that half of the
  vintage claim), quoted cylinder count (also confirms the vintage
  manual's quoting), `:n:` interleave (also confirmed), plus a
  `/clustersize/` option not documented in any of the vintage sources.
  No dash-prefixed density letters appear in NitrOS-9's own help text at
  all — `-sd`/`-dd`/`-ss`/`-ds` may be vintage-Microware-only.
- `os9gen`, `cobbler`, `config`: see the Module and memory utilities
  section and the CoCo/Dragon-specific section below, respectively —
  three overlapping ways to (re)build a bootable system diskette.
- `date [t]` — displays the current date; `t` also shows the time. Use
  `setime` to change it. Two quick-reference-documented display variants
  exist beyond the plain form (Julian, 24-hour/military) but are not
  confirmed against the Level 2 manual's own `date` entry.
- `setime [y m d h m s [am/pm]]` — sets system date/time and starts the
  clock; multitasking depends on the clock actually running (some boot
  configurations start it automatically via a startup-time clock module
  instead of requiring an explicit `setime`). Year is four digits (`Live` (NitrOS-9),
  interactive prompt displays `yyyy/mm/dd hh:mm:ss` template; prior
  claim of 2-digit year was incorrect). Month/day/hour/minute are 1–2
  digits; seconds are optional. Delimiters: space, colon, semicolon, or
  slash, freely mixed. If the clock is never set, file "last modified"
  timestamps can't be trusted.
- `echo <text>` — writes its argument to stdout; avoid shell-special
  punctuation in the text. Common uses: messages in procedure files, or
  pushing a raw control-code sequence at a terminal (e.g. redirected to
  `/p` or a specific `/term`).
- `error {<n>}` — looks up one or more numeric error codes (1–255)
  against `SYS/Errmsg` and prints their text.
- `help {<name>}` — looks up command syntax/usage in `SYS/Helpmsg`; an
  unrecognized name prints "Help not available" for that name and moves
  on to the rest of the argument list.

## CoCo/Dragon-specific utilities

These utilities are tied to Color Computer / Dragon (or Gimix) hardware
specifics rather than being generic OS-9 Level 2 facts — don't assume
they generalize to every 6809 board.

- `cobbler <devname>` — builds `OS9Boot` directly from whichever modules
  are currently loaded (no patchfile/module-list step, unlike `os9gen`).
  Writes the kernel to Track 34 and excludes those sectors from the
  allocation map. Needs a large-enough contiguous run, so use it only on
  freshly formatted media — on an already-used disk it can destroy the
  existing boot file without being able to replace it, leaving the disk
  unbootable. Typical flow: change any device defaults you want baked in
  with `xmode` first, then run `cobbler`. `Live` (NitrOS-9): the Level 1 manuals
  describe `cobbler` as a Level-1-only tool superseded by `os9gen` on
  Level 2, but the Level 2 manual itself documents a `cobbler` command,
  and it's present and working on the Level-2-descended NitrOS-9 system
  (`Cobbler
  <devname> [-e]`, `-e` = permit fragmented boot, simpler than the
  vintage flow described above) — the Level-1-only claim is wrong, at
  least for NitrOS-9's descendant of Level 2.
- `config` — fully interactive (no command-line parameters at all);
  walks the user through building a custom system diskette from chosen
  drivers/commands, screen-adjusting for 32- or 80-column display.
  Module files it operates on are typed by extension: `.dd` (device
  descriptor), `.dr` (driver), `.io` (I/O subroutine), `.hp` (help),
  `.dw` (window descriptor), `.dt` (terminal descriptor). Its main
  advantage over `backup` + selective deletion is producing zero
  fragmentation.
- `display {<hex>}` — takes one or more hex byte values and writes the
  corresponding ASCII/control characters to stdout; the standard way to
  script cursor/screen-control sequences at a terminal.
- `montype [c|r|m]` — tells the system what kind of display is attached:
  `c` composite/color-TV (the default if `montype` is never run), `r`
  RGB monitor, `m` monochrome/black-and-white. Affects color rendering
  only on compatible hardware.
- `tuneport [/p | /t1] [-s=<n>]` — tunes a serial port's delay-loop value
  against its current baud rate. Interactive mode shows the current baud
  rate and delay value, sends test data, and prompts for a new delay
  value repeatedly until Enter is pressed with no new value; `-s=<n>`
  sets a value directly without the interactive loop. A tuned value is
  only in-memory — make it stick across boots by adding the `tuneport`
  invocation to `startup`, or by baking it into a new boot file with
  `cobbler`.
- `wcreate <devname> <xpos> <ypos> <xsize> <ysize> <fg> <bg> [<border>] [-s=<type>] [-z] [-?]`
  — creates a display window (`W`, `W1`, `W2`, …). `xpos`/`ypos` are the
  decimal coordinates of the window's upper-left corner; `xsize` is
  1–80 columns, `ysize` is 1–24 lines. `fg`/`bg` set foreground/
  background color; `border` is optional and defaults to black **unless**
  `-s=<type>` is given, in which case a border color becomes mandatory.
  `-s=<type>` picks the screen mode; `Live` (NitrOS-9), the CoCo3/OS-9 standard
  type codes are: `1` = 40-column text (2K), `2`
  = 80-column text (4K), `5` = 80-column 2-color graphics (16K), `6` =
  40-column 4-color graphics (16K), `7` = 80-column 4-color graphics
  (32K), `8` = 40-column 16-color graphics (32K) — all screens are 24–25
  text lines or 192–200 graphics lines tall, and a graphics screen needs
  the `StdFonts` file merged in before it can display text (else
  characters show as a placeholder glyph). This resolves what the two
  cross-check quick references had stated slightly differently. `-z`
  reads window parameters from redirected stdin instead of the command
  line (`Live` (NitrOS-9) name — a cross-check source's `-@` was wrong).
  `-?` prints a help message.
- `wmode` `Manual` (Farna 2nd-ed only — not in the primary Level 2
  manual) — re-applies `wcreate`-style parameters to an already-created
  window, but does **not** touch anything governed by `xmode`/`tmode` —
  those still need their own separate invocation.
- `devs`, `irqs`, `events` — `Absent`. These are Professional OS-9/68000
  utilities (attached-device table, IRQ polling table, active
  named-event listing) documented in `common/utility-usage.md`. 6809 has
  no `events` counterpart because its own IPC primitives are
  process-directed signals (`F$Send`/`F$Icpt`/`F$Sleep` — see
  `6809/syscalls-and-module-format.md`'s Signals section) rather than
  68k's named-event-object model (`F$Event` with `Ev$Signl`/`Ev$Wait`
  subfunctions — see `68k/syscall-reference.md`).
- `tape`, `tapegen`, `diskcache` — `Absent`.
- `code` — `Absent`.

## Level 1 vs Level 2: user-visible differences

The manual states outright: **Level 1 commands and Level 2 commands are
not interchangeable** — don't run one system's command set against the
other. Beyond that blanket warning, the concrete differences a user
actually notices:

- **Windowing is Level-2-only.** Level 1 has one physical screen and no
  windowing subsystem at all — `wcreate`/`wmode`/`montype`/`tuneport`
  and the whole `GFX2` module (see `6809/gfx-windowing.md`) don't exist
  there; Level 1 programs use the `GFX` module's single full-screen
  low-resolution graphics instead. Level 2's multiple windows are a
  memory-mapping trick (see `os9-systems-dev`'s `6809-level2-mmu.md` for
  the DAT mechanism underneath) — several windows can share one physical
  screen simultaneously, which is what `DWSET`'s special `format=$FF`
  ("current displayed screen") value is for: a procedure file
  deliberately placing more than one window on the same screen, as
  opposed to the normal case of a program targeting its own window
  (`format=$00`, "process's current screen").
- **`montype`** (monitor-type selection: composite/RGB/monochrome) only
  makes sense on Level 2/CoCo3 hardware capable of more than one video
  mode — it isn't a Level 1 concept and doesn't appear in Level 1
  documentation.
- **`wmode`'s own manual coverage is thinner than its windowing
  siblings.** `wcreate`, `montype`, and `tuneport` all have their own
  entries in the Level 2 Operating System Manual; `wmode` doesn't — it's
  sourced here from the Farna CoCo quick reference only (see `## Devices,
  disks, system`). Functionally it still reads as Level-2-only, same as
  the rest of the windowing set, just not documented in this particular
  manual.
- **Per-program memory limits are similar in practice, different in
  mechanism.** Both levels cap a single program around 56-60K of usable
  RAM after reserving space for ROM/vectors/video — Level 1 because
  that's literally all the flat 64K address space has left over; Level 2
  because even though DAT gives each task its own *isolated* 64K logical
  space, a chunk of every task's map still has to mirror interrupt
  vectors and kernel entry points unless the hardware does automatic
  task-switching (see `os9-systems-dev`'s `6809-level2-mmu.md`, IRQ-masking
  section). So the
  practical per-program ceiling barely moves between levels — what Level
  2 actually buys is running several such programs *simultaneously* in
  physically separate memory, not a bigger ceiling for any one of them.
- **The `#n`/`#nK` memory modifier is identical on both levels** — `n`
  256-byte pages, or `nK` 1024-byte increments, added to whatever a
  command's own module header requests. Nothing here diverges by Level;
  `Manual` (the Level 2 manual's own worked example: `copy #8` and
  `copy #2K` given as equivalent, both 2048 bytes).

## tmode / xmode parameters

`tmode [.<pathnum>] [<params>]` / `xmode <devname> [<params>]` (SCF-type
devices only — video, printer, RS-232, window) — same open-path-vs-
device-descriptor scope/persistence mechanism as 68k (see
`common/os9-tools-and-shell.md`). 6809-specific: `tmode`'s path number
defaults to standard input; inside a procedure file, specify `.1`/`.2`
explicitly, since the procedure file's own redirection has already
claimed `.0`. Permanence for `xmode` changes means editing the
descriptor file and relinking, or baking the change into a new boot file
via `cobbler` (68k instead uses `moded`+`fixmod` or a reboot). Both
commands share the same parameter vocabulary and auto-adjust their own
display for 32- vs. 80-column terminals. Naming a parameter bare, with
nothing after it, snaps that one setting back to its factory default;
giving it `=0` instead switches the feature off entirely.

**One real difference that matters:** `tmode` can only *display*
`type`/`par`/`cs`/`stop`/`baud` (the underlying serial hardware settings)
— it cannot change them. `xmode` can change them, but only across a
`deiniz <dev>` → `xmode …` → `iniz <dev>` cycle; changing them on an
already-open device has no effect until that cycle runs. `Manual`, and
single-sourced on the 6809 side (the genuinely-CoCo Farna 2nd edition;
the "1st edition" file also cited in this document turns out to be
OS-9/68000 material, not an independent 6809 source — see `Sources:`
footer — so this is not doubly cross-checked).

| Parameter | Meaning (default) |
|---|---|
| `upc`/`-upc` | force upper-case echo (lowercase auto-converts) / mixed case (default) |
| `bsb`/`-bsb` | echo backspace as BS-space-BS (default) / echo a single backspace only |
| `bsl`/`-bsl` | erase line by backspacing (video, default) / print a new line (hardcopy) |
| `echo`/`-echo` | input echo (default on) |
| `lf`/`-lf` | auto line feed after CR (default on) |
| `pause`/`-pause` | screen pause when full, resume on space bar (default on) |
| `null=<n>` | NUL padding count after CR (decimal, default 0) |
| `pag=<n>` | screen page length in lines, for `pause` |
| `bsp=<h>` / `bse=<h>` | input / output backspace char (hex, default 08) |
| `del=<h>` | delete-line char (hex, default 18) |
| `bell=<h>` | alert/bell char (hex, default 07) |
| `eor=<h>` | end-of-record / CR char (hex, default 0D) |
| `eof=<h>` | end-of-file char (hex, default 1B / ESC) |
| `reprint=<h>` | reprint-current-line char (hex) |
| `dup=<h>` | duplicate-last-line char (hex, default 01) |
| `psc=<h>` | pause char (hex, default 17 / Ctrl-W — `Live` (NitrOS-9); the primary manual's OCR rendered this as `pse=`, which is wrong) |
| `abort=<h>` | terminate char (hex, normally Ctrl-C) |
| `quit=<h>` | quit char (hex, normally Ctrl-E) |
| `xon=<h>` / `xoff=<h>` | flow-control chars (hex, default 11 / 13) |
| `tabs=<n>` / `tabc=<h>` | tab stop spacing (default 4) / tab char (hex, default 09) |
| `baud=<h>` | baud-rate/word-length/stop-bit byte, `Live` (NitrOS-9) — the primary manual's own table was OCR-corrupted; the cross-check sources' version was close but not quite right either — this supersedes both): bits 0–3 baud code — `0`=110, `1`=300, `2`=600, `3`=1200, `4`=2400, `5`=4800, `6`=9600, `7`=19200 (ACIAPAK driver only), `8`=32000 (SIO driver only); bit 4 reserved; bits 5–6 word length (`00`=8-bit, `01`=7-bit); bit 7 stop bits (`0`=1, `1`=2). Live examples: `baud=22` (hex) = 1 stop bit, 7-bit words, 600 baud; `baud=86` = 2 stop bits, 8-bit words, 9600 baud |
| `type=<h>` | ACIA init byte (hex, default 00): bits 5–7 select parity (000 none, 101 MARK, 111 SPACE, 011 even, 001 odd — even/odd only on ACIA-pak/Mod-pak hardware), bit 4 toggles auto-answer modem support. Device-specific meanings: on TERM-VDG, bit 0 enables true lowercase; on TERM-WIN, `type=80` marks it as a window device. |
| `par`, `cs`, `stop` | parity / character size / stop bits — **display-only via `tmode`**, must go through the `deiniz`→`xmode`→`iniz` cycle to actually change |
| `normal` | reset every parameter above to its default |

Values are hex for character codes and the `baud`/`type` bitfields,
decimal for counts (`null=`, `pag=`, `tabs=`).

## Open gaps from this extraction pass

- `ex` and `list` now carry their real Level 2 manual entries (lines 7459
  and 8119 of the primary source). `wmode` remains `Manual` (Farna
  2nd-edition only — see `## Devices, disks, system` and
  `## Level 1 vs Level 2`).
- `tape`, `tapegen`, `diskcache`, `devs`, `irqs`, `events`, and `code` are
  `Absent` — see `## Devices, disks, system`. A source-mislabeling
  discovery came out of that search (see `Sources:` footer) — worth
  keeping in mind for any future 6809 mining pass that reaches for the
  Farna "1st edition" file.
- Several Level 1-only utilities with no Level 2 equivalent surfaced
  during cross-checking (`binex`/`exbin`, `dump`, `login`/`tsmon`,
  `printerr`, `save`, `sleep`, `tee`, `verify`) — worth their own pass if
  Level 1 coverage becomes a priority; not folded in here since this
  file's scope is the Level 2 utility set specifically.
- FORMAT's density option letters (`-sd`/`-dd` vs. bare `S`/`D`) — `Manual,
  Flag` between the vintage sources, and unresolved even after a `Live` (NitrOS-9)
  check: NitrOS-9's own `format` doesn't use dash-prefixed letters for
  density at all, so this may be purely a vintage-Microware-only detail
  no longer testable on the emulator available here. `wcreate`'s
  `-s=<type>` numbering and `dcheck`'s option letters, by contrast, are
  now `Live` (NitrOS-9) — see above — and no longer open.

---
Sources: OS-9 Level 2 Operating System Manual (System Command
Descriptions chapter) is primary; OS-9 Users Manual 1983 and Gimix OS-9
Users Manual 1983 (both Level 1) and the Farna OS-9 Quick References were
used as independent cross-checks to resolve OCR ambiguity in the primary
source and to surface Level 1/Level 2 differences. All text here is
paraphrased, not quoted. **Caveat on one cross-check source:** the file
catalogued in this corpus as the Farna "1st edition" CoCo quick reference
is mislabeled — its own title page identifies it as documentation for
Professional OS-9/68000, not CoCo/6809 (found while chasing the
`devs`/`irqs`/`events`/`tape`/`code` gap: its entries for those commands
describe the 68k versions already in `common/utility-usage.md`, not an
independent 6809 source). Only the genuinely CoCo-specific 2nd edition,
plus the 1982 Tandy CoCo quick reference, were treated as 6809
cross-checks for that gap. A handful of items (`dcheck`'s options,
`wcreate -s=<type>`, the `tmode`/`xmode` `baud=`/`psc=` parameters,
`cobbler`'s existence, and NitrOS-9's own `format` syntax) are
additionally tagged `Live` (NitrOS-9), confirmed against a real NitrOS-9 session.
NitrOS-9's utilities are a modern rewrite — flag any live divergence you
find as such, not as a manual error.
