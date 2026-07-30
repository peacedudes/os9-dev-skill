# OS-9 Utility Usage: Syntax and Options

Per-command syntax and option reference for the Professional OS-9 v2.4
(68k) utility set. 6809 editions of the same-named utilities often differ
in options — on any live system, `<name> -?` or `help <name>` is ground
truth. Notation: `[..]` optional, `{..}` repeatable. One-line "what it's
for" descriptions: `os9-tools-and-shell.md`.

## Conventions shared by many utilities (stated once, not repeated below)

- **`-?`** — every utility prints its own function/syntax/options.
- **`-z` / `-z=<file>`** — read the operand list (file/module/device
  names) from standard input / from `<file>`. Supported by most utilities
  that take name lists; the glue for pipelines like
  `dir -u ! qsort ! attr -z ...`.
- **`-x`** — resolve the named file(s) against the current **execution**
  directory instead of the data directory (attr, binex, cmp, copy, del,
  dump, dir, fixmod, ident, makdir, merge, os9gen, rename, romsplit,
  save, touch, and others).
- **`-b=<num>k`** — memory/buffer allocation for the transfer (backup,
  cmp, copy, dsave, edt, free, frestore, fsave, merge, os9gen; default is
  typically 4K).

## File and directory utilities

- `attr [<opts>] {<path>} {<permissions>}` — permissions given as
  `-r -w -e -pr -pw -pe -s -d` to set, `-n<abbrev>` (e.g. `-npw`) to
  clear; unnamed bits unchanged; none given = display. **6809 inverts
  this** (`Live` (NitrOS-9, os9exec), both sides): there a bare letter sets and a minus-prefix
  clears, so `attr f -e` sets execute here and *clears* it on 6809 —
  `6809/utility-usage.md`. `-a` suppress
  attribute printout. Owner = same group ID; only owner/superuser may
  change. Can clear `d` on an emptied directory (never set it — only
  `makdir` creates directories). Bare `attr <path>` prints an 8-character
  string, `Live` (os9exec)-decoded: positions 1-4 are `d`/`s`/`pe`/`pw`
  (directory, sharable, public-execute, public-write) and 5-8 are
  `pr`/`e`/`w`/`r` (public-read, owner-execute, owner-write, owner-read),
  each either the letter or `-`; e.g. `----r-wr` = no directory/sharable/
  public-exec/public-write bits, public-read granted, owner has write+read
  but not execute. `attr -e` needs more privilege than the bare form —
  `Live` (os9exec): it failed `E$FNA`/214 in a session where the plain form
  succeeded on the same file.
- `build <path>` — prompts `?` per line, writes each to the file; empty
  line/EOF ends.
- `copy [<opts>] <path1> [<path2>]` — `-a` abort on first error, `-f`
  overwrite write-protected destinations, `-r` overwrite existing, `-v`
  verify result, `-w=<dir>` copy multiple sources *into* a directory
  (`-p` suppresses the per-file listing in that mode), `-b=<size>` use a
  larger transfer buffer (e.g. `-b=20k`; bigger buffers speed up large
  copies — the manual's own examples lean on this), **`-n` don't duplicate
  the FD from the source, create a fresh one instead**. `Live` (os9exec):
  `-n` is what you want when copying *out of a host-native directory into
  an RBF image as a non-super user*. The default duplicates the source's
  whole file descriptor, including its owner; a host directory has no real
  OS-9 owner so os9exec synthesises `0.0`, and reproducing that on the
  destination is an owner change the caller is not entitled to make — the
  copy prints `E$PERMIT` while still transferring the data, so it looks
  half-broken and is easy to wave through as noise. `-n` skips FD
  replication and the error disappears at its source. `Manual` (*Using
  Professional OS-9* v2.4).
- `count [<opts>] {<path>}` — `-l` lines, `-w` words, `-c` characters,
  `-b` per-character frequency breakdown.
- `del [<opts>] {<path>}` — `-f` delete write-protected, `-p` prompt per
  file, `-e` zero the freed disk space (secure erase).
- `deldir [<opts>] {<path>}` — recursive; `-f` ignore write protection,
  `-q` no confirmation prompts.
- `dir [<opts>] {<path>}` — `-e` extended (owner, dates, size, perms),
  `-a` include dot-files, `-d` mark directories with `/`, `-n`
  directories themselves only, `-r` / `-r=<num>` recursive (to depth),
  `-s` unsorted, `-u` unformatted (for piping), `-x` list the execution
  directory.
- `dsave [<opts>] [<path>]` — emits a copy script for a whole tree; run
  it (or `-e` execute immediately). `-d`/`-d=<date>` copy only newer
  files, `-f`/`-r` force/overwrite via copy's flags, `-i` indent by
  level, `-l` this level only, `-m` omit makdir lines, `-v` cmp-verify
  (`-n` don't load copy/cmp), `-s` skip files on error, `-o`/`-o=<name>`
  also os9gen a bootfile onto the destination, `-a` skip dot-files.
- `edt [<opts>] <path>` — line-number editor (append at line, `c` change,
  `d` delete, `l` list — interactive).
- `list [<opts>] {<path>}` — print text file(s).
- `makdir [<opts>] {<path>}` — `-x` create under the execution directory.
- `merge [<opts>] {<path>}` — concatenate to stdout (redirect to
  combine).
- `pr [<opts>] {<path>}` — paginated/columnar printing: `-p=<n>` lines
  per page, `-d` page depth, `-k=<n>` columns, `-m` one file per column,
  `-c=<char>` column separator, `-l=<n>`/`-r=<n>` margins, `-o` truncate
  long lines, `-t` no title, `-u=<title>` title text, `-h=<n>` blank
  lines after title, `-n=<n>` line-number increment, `-x=<n>` first page
  number, `-f` newline padding instead of form feeds.
- `rename [<opts>] <path> <newname>`
- `touch [<opts>] {<path>}` — update modification date; `-c` don't
  create missing files, `-q` continue past errors.
- `tee {<path>}` — copy stdin to stdout plus every named path. **The
  OS-9 heredoc:** `tee >file`, type content, end with the EOF key (ESC
  by default; Ctrl-D after `tmode eof=04`) — quickest way to create a
  short file anywhere, RBF image or host directory alike.
- `cmp [<opts>] <path1> <path2>` — per-mismatch offset/values; `-s` stop
  at first difference, summary only.
- `grep [<opts>] [<expr>] {<path>}` — `-c` count only, `-l` filenames
  only, `-n` line numbers, `-v` invert, `-s` silent (exit status only),
  `-e=<expr>` explicit pattern, `-f=<path>` patterns from file.
- `qsort [<opts>] {<path>}` — sort lines; `-f=<num>` sort field (one
  only), `-c=<char>` field separator.
- `tr [<opts>] <str1> [<str2>] [<path1>] [<path2>]` — transliterate;
  `-d` delete matches, `-s` squeeze repeats, `-c`/`-v` complement of
  `<str1>`.
- `compress` / `expand [<opts>] {<path>}` — de/re-huffman text; `-n`
  write output file (else stdout), `-d` delete the original.
- `code` — prints the hex value of each key pressed (keyboard probe;
  exit with `q`).

## Module and memory utilities

- `load [<opts>] {<path>}` — make a file's modules resident. `-d` load
  from the **data** directory (default is the execution directory — the
  usual surprise), `-l` print the resolved pathlist.
- `link` / `unlink [<opts>] {<modname>}` — bump a resident module's link
  count up/down.
- `save [<opts>] {<modname>}` — write resident module(s) to file(s);
  `-f=<path>` all into one file, `-r` overwrite.
- `ident [<opts>] {<modname>}` — decode header + CRC check. `-m` module
  in memory (not file), `-q` one line per module, `-s` only report bad
  CRCs.
- `fixmod [<opts>] {<modname>}` — `-u` repair CRC/parity;
  `-ua=<att.rev>` set attribute/revision, `-up=<perm>` set access
  permissions, `-uo<g>.<u>` set owner, `-ub` fix sys/rev in packed
  BASIC09 subroutine modules.
- `mdir [<opts>] [<modname>]` — `-e` extended, `-a` show language
  field, `-t=<type>` filter by type, `-u` unformatted for piping.
- `mfree [-e]` — free memory; `-e` per-block detail.
- `dump [<opts>] [<path> [<addr>]]` — hex/ASCII; `-m` a resident module,
  `-s` treat offset as a sector number (RBF forensics), `-c` don't
  collapse duplicate lines.
- `moded [<opts>] [<path>]` — edit a module's option table
  (descriptors); `-d=<path>` field-description file, `-e=<path>` error
  file, `-f=<path>` load modules from file. Follow with `fixmod -u`.
- `binex [<opts>] [<path1> [<path2>]]` / `exbin` — module ↔ S-record;
  `-a=<hex>` load address, `-s=<n>` S-record type.
- `romsplit {<opts>} {<path>}` — split for ROM burners; `-q` four-way
  split.

## Process and environment

- `procs [<opts>]` — `-e` all users' processes, `-a` alternate columns,
  `-b` both.
- `kill {<procID>}`, `setpr <procID> <number>`, `sleep [-s] <num>`
  (ticks; `-s` seconds), `w` (wait for one child), `ex <path> [<args>]`
  (replace shell), `profile <path>`, `setenv <var> <value>`,
  `unsetenv <var>`, `printenv`, `logout` — argument shapes as shown; no
  further options.
- `login [<name>] [,] [<password>]` — authenticate against
  `SYS/password`.
- `shell [[set] <arglist>]` — options usable at invocation, via the
  `set` built-in, or per-line: `-p`/`-p=<str>`/`-np` prompt,
  `-t`/`-nt` echo input (off default), `-x`/`-nx` abort on error (on
  default), `-e=<file>`/`-ne` error-message printing (off default),
  `-v`/`-nv` report each directory searched, `-l`/`-nl` whether only
  `logout` may end a login shell (`-nl`: EOF ends it too).

## Devices, disks, system

- `iniz` / `deiniz [<opts>] {<devname>}` — attach/detach devices.
- `devs`, `irqs`, `events` — tables of attached devices / IRQ polling /
  active events. No options.
- `free [<opts>] {<devname>}` — free disk space.
- `dcheck [<opts>] <devname>` — filesystem check; `-r` interactive
  bitmap repair, `-y` repair answering yes to everything, `-d=<num>`
  print directory paths `<num>` deep.
- `format [<opts>] <devname>` — `-ss`/`-ds` sides, `-sd`/`-dd` density,
  `-t=<n>` cylinders, `-c=<n>` sectors/cluster, `-i=<n>` interleave,
  `-v=<name>` volume name (≤32 chars), `-np` skip physical format,
  `-nv` skip verify, `-nf` no fast verify, `-e` show verify time, `-r`
  no ready prompt. Requires the `fmt`-enabled descriptor (`/h0fmt`);
  plain `/h0` is format-inhibited.
- `os9gen [<opts>] <devname> {<path>}` — build/install a bootfile;
  `-e` extended (>64K or non-contiguous) boot, `-q=<file>` point sector
  0 at an existing file, `-r` remove the boot pointer.
- `backup [<opts>] [<srcpath> [<destpath>]]` — device-to-device image
  copy; `-r` continue past read errors, `-v` skip the verify pass.
- `fsave [<opts>] [<dir>]` — incremental tree backup to tape/device:
  `-l=<n>` backup level, `-d=<dev>` target (default `/mt0`),
  `-f=<path>` to a file, `-g=<n>`/`-u=<n>` only this group/user,
  `-m=<path>` date-log file, `-t=<dir>`/`-x=<n>` temp-index
  location/pre-extension, `-s` list what needs saving, `-e` no per-file
  echo, `-p` no first-volume prompt, `-v` no volume verify, `-j=<n>`
  minimum memory request.
- `frestore [<opts>] [<path>]` — restore from fsave media: `-s` restore
  all non-interactively (`-q` overwrite existing with it), `-a` force
  permission to overwrite, `-c` validity check only, `-d=<dev>` source,
  `-f=<path>` from file, `-i`/`-v` show backup identity (`-e` full
  pathlists), `-p`/`-t=<dir>`/`-x=<n>`/`-j=<n>` as for fsave.
- `tape {<opts>} [<dev>]` — positioning: `-r` rewind, `-b[=<n>]` skip
  blocks, `-f[=<n>]` skip tapemarks, `-w[=<n>]` write tapemarks,
  `-e=<n>` erase blocks, `-t` retension, `-o` off-line, `-s` report
  block size.
- `tapegen` — build a bootable tape (`-b=<bootfile>`, `-bz=<bootlist>`,
  `-t=<target>`, `-v=<volume>`, `-i=<file>`, `-d=<dev>`, `-c` check
  header, `-o` off-line after).
- `diskcache [<opts>] [<dev>]` — `-e`/`-d` enable/disable, `-l` status,
  `-t=<size>[k]` total cache limit.
- `setime [<opts>] [y m d h m s [am/pm]]` — `-s` from battery clock,
  `-d` don't echo the result.
- `date [<opts>]` — `-j` Julian, `-m` 24-hour time.
- `tsmon [<opts>] {/<dev>}` — watch terminals for logins; `-p` print an
  online prompt, `-l=<prog>`/`-r=<prog>` alternate login/shell program,
  `-d` statistics on ^\.
- `kermit <flags> [<dev>] [<file>…]` — file transfer. Flags are one bundled
  argument with no `-`, and two of them decide whether the command does what
  you meant (`Live`, os9exec; presence varies by disk):
  - **`l` (line) is required to aim at a device.** `kermit s /t1 file` sends
    over the *console* and silently ignores `/t1`; `kermit sl /t1 file` uses
    the named device. Neither errors — the giveaway is transfer traffic
    appearing on your own terminal.
  - **For binary use `i` (image), never `8` (8-bit quoting).** `8` is for
    links that are not 8-bit clean and corrupts data over a path that
    already is. `kermit sil /t1 mymodule` moves a module intact.
- `break` — halt into the ROM debugger (superuser, console).
- `make [<opts>] [<target>…] [<macros>]` — `-f=<path>`/`-f-` makefile
  (stdin), `-n` show without executing, `-t` touch dates only, `-u`
  rebuild regardless of dates, `-i` ignore errors, `-s` silent,
  `-b`/`-bo` disable built-in rules (all/object), `-d`/`-dd` debug
  verbosity, `-x` cross-compiler mode.

## tmode / xmode parameters

`tmode [<opts>] [<params>]` / `xmode <devname> [<params>]` — mechanism
(open-path-vs-device-descriptor scope, persistence rules) is in
`os9-tools-and-shell.md`; invocation specifics here: `-w=<path#>` selects
path 0/1/2 for `tmode` (required inside a procedure file); `type par cs
stop baud` only take via `deiniz <dev>` → `xmode …` → `iniz <dev>`. Same
parameter vocabulary for both; a parameter with no value resets to its
default; `=0` disables the feature.

| Parameter | Meaning (default) |
|---|---|
| `upc`/`noupc` | force upper-case echo / mixed case (default) |
| `echo`/`noecho` | input echo (on) |
| `lf`/`nolf` | auto line feed after CR (on) |
| `bsb`/`nobsb` | echo backspace as BS-space-BS (on) |
| `bsl`/`nobsl` | erase line by backspacing (video, on) / newline (hardcopy) |
| `pause`/`nopause`, `pag=<n>` | screen pause; page length in lines |
| `null=<n>` | NUL padding count after CR (0) |
| `tabs=<n>`, `tabc=<h>` | tab stop spacing (4); tab char (09) |
| `bsp=<h>`, `bse=<h>` | input/output backspace char (08) |
| `del=<h>` | delete-line char (18 = ^X) |
| `eor=<h>` | end-of-record char (0D = CR) |
| `eof=<h>` | end-of-file char (1B = ESC) — `eof=04` moves it to Ctrl-D |
| `reprint=<h>` | reprint-line char (04 = ^D) |
| `psc=<h>` | pause char (17 = ^W) |
| `abort=<h>` | interrupt char (03 = ^C) |
| `quit=<h>` | abort/kill char (05 = ^E) |
| `xon=<h>`, `xoff=<h>` | flow control chars (11, 13) |
| `bell=<h>` | alert char (07) |
| `normal` | reset everything above to defaults |
| `type`, `par`, `cs`, `stop` | serial hardware settings — **display-only in tmode**; change via the descriptor (`xmode`/`moded` + `iniz`) |
| `baud=<n>` | writes the open path's baud option byte, but not the hardware rate — see below |

Values are hex for character codes, decimal for counts.

### `baud=` — the argument is a rate, the stored byte is a code

"Display-only" is right about the **hardware**: making a device actually run
at a new rate takes `deiniz` → `xmode` → `iniz`. But `tmode baud=<n>` does
write the open path's own baud option byte, and a later `tmode` on that same
still-open path reads the new value back — `Live` (os9exec). The argument
there is **raw bits per second**, not the code index below.

The byte in the device descriptor is a **code**, and the two architectures
encode it differently. Reading one target's table for the other gives wrong
answers:

On **68k** the whole byte is a flat index into this rate table — `Source`
(os9exec):

| Code | bps | Code | bps | Code | bps |
|---|---|---|---|---|---|
| 0 | 50 | 8 | 1800 | 16 | 38400 |
| 1 | 75 | 9 | 2000 | 17–20 | unassigned |
| 2 | 110 | 10 | 2400 | 21 | 57600 |
| 3 | 134 | 11 | 3600 | 22 | 115200 |
| 4 | 150 | 12 | 4800 | | |
| 5 | 300 | 13 | 7200 | | |
| 6 | 600 | 14 | 9600 | | |
| 7 | 1200 | 15 | 19200 | | |

On **6809** the same byte packs rate *and* word length *and* stop bits, over a
shorter and differently-numbered rate list — see `6809/utility-usage.md`'s
`baud=` row. The 68k indexes above do not apply there.

---
Sources: Using Professional OS-9 v2.4, "The OS-9 Utilities" chapter
(syntax lines and option letters are the manual's facts; descriptions
are original wording). 6809 utility sets differ — verify options live
via `help`/`-?` there.
