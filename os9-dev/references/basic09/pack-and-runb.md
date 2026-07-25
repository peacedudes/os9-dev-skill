# PACK and RunB: Packed BASIC09 Modules

How BASIC09 procedures become standalone OS-9 modules and how they resolve
at run time. The manuals are thin here; most facts below are `Live`
on OS-9/68k (os9exec). Module-format background: `common/module-format.md`.

## PACK

- `PACK` converts a workspace procedure to a non-listable, non-editable
  form. **It is one-way** — the packed form can't be `LIST`ed, edited, or
  reloaded into the workspace. Always `SAVE` source first.
- **Output goes to the current execution directory (CHX)**, under the
  procedure name or an explicit `>pathlist`. If the file "didn't appear,"
  check CHX — it was written, just not where you were looking. (`asm`
  behaves the same way.)
- **`SAVE` and `PACK` do NOT redirect to the same place** — `Live` (6809).
  With a *relative* target, from the same workspace in the same session:
  `SAVE proc >name` lands in **CHD** (the data directory), `PACK proc >name`
  lands in **CHX**. The CHX rule above is `PACK`'s alone; `SAVE` follows
  ordinary data-file resolution. Use an absolute path for either when it
  matters.
- **Packing does not speed up in-workspace execution** — measured
  identical times packed vs. unpacked under interactive `basic`; BASIC09
  always executes I-code. The manual's 10–30% speedup claim applies to
  running under RunB (comment/name stripping), and is `Manual`, not
  yet measured.
- **Entry point when packing several procedures** — the biggest gotcha
  here:

| Form | Entry point of the output module |
|---|---|
| `PACK proc1,proc2` | The *first-listed* procedure |
| `PACK*` (whole workspace) | The *current* procedure (the one `DIR` marks with `*` — usually last loaded/touched) |

  Both outputs contain every packed procedure's code; only the entry
  differs. If the entry point matters, name the list explicitly.
- **`>pathlist` with a procname list prints a BASIC09 error and still
  works.** `Live` (68k): `SAVE proc >target` and `PACK proc >target` print
  `Error #000:043` while writing a correct file. **The codes are BASIC09's
  own, from its manual's Appendix C — 43 is "Unknown Procedure", 51 is
  "Line with Compiler Error"** — not OS-9 kernel codes. In particular this
  is **not** `E$BNam` (which is **235**); an earlier version of this entry
  blamed `F$PrsNam` and that attribution was wrong. A syscall trace shows
  `F$PrsNam` behaving exactly as the 2.4 Technical Reference specifies:
  BASIC09 walks the pathlist with repeated calls and the final `E$BNam` on
  the empty remainder is the documented multi-call terminator — and the
  call's *only* possible error — which BASIC09 consumes silently. Every
  syscall in the failing window returns a spec-conformant value, so on the
  evidence available **this is BASIC09's own `SAVE`/`PACK` argument
  handling, not a demonstrated os9exec defect.** `Absent`: whether the
  genuine 68k binary on real hardware prints it too is untestable here.
  The trigger is the **procname list**, not the path shape:

  | Form | 68k `os9exec` | Output |
  |---|---|---|
  | `SAVE proc >target` (rel *or* abs, space before `>` or not) | `Error #000:043` | correct, byte-identical to the clean form |
  | `SAVE proc` | clean `Ready` | correct |
  | `SAVE >target` | clean `Ready` | correct |
  | `PACK proc >target` | `Error #000:043` (twice) | valid module — `ident` gives Good CRC + Good parity, `Ty/La $202` |
  | `PACK >target` (no procname) | `Error #000:051` | **0-byte file — this one genuinely fails** |

  So: verify the file rather than trusting the message, but note the last
  row is a real failure, not a cosmetic one. **`Live` (6809): real NitrOS-9
  BASIC09 prints nothing at all** for `SAVE proc >rel`, `SAVE proc
  >/DD/abs/path` and `PACK proc >rel` — a different binary on a different
  architecture, so suggestive, not proof about the 68k line. (`> pathlist`
  with a space *after* the `>` is a separate thing — unrecognized syntax.)
  Resolution targets, 68k: relative `SAVE >name` resolves against **CHD**;
  `PACK`'s default output is the **execution** directory, so a relative
  `PACK >name` lands in `/h0/CMDS`.

## What a packed module is

A packed+saved procedure is an OS-9 **subroutine module**: type 2
(Sbrtn), language 2 (BASIC I-code). **How `ident` renders that is
architecture-specific — don't carry one form to the other.** On 68k the
header has separate `M$Type`/`M$Lang` bytes and `ident` shows `Ty/La
$0202`. On 6809 it is a single packed byte `(type << 4) | language`, so
the same module reads **`Ty/La $22`** (`Live`, with `At/Rv
$81` — re-entrant, revision 1). See `common/module-format.md` for the
encoding and what it settles about the 6809 C compiler's own value. It is not a
program module; something must interpret it.

**RunB** is that interpreter: a runtime-only BASIC09 (~half the size, no
edit/debug). Per the manual, code under RunB can trap Ctrl-C/Ctrl-Q via
`ON ERROR GOTO`, which interactive `basic` cannot.

## How a packed module is found (three distinct contexts)

1. **`RUN <name>` typed inside interactive `basic`:** workspace first,
   then current *data* directory, then *execution* directory, then OS-9
   module link/load (`Manual` order).
2. **From the OS-9 shell** — `runb <name>`, or the bare name (the shell
   auto-detects BASIC I-code and forks RunB with the name as argument).
   Either way the module resolves via OS-9's standard order: **F$Link
   (already resident?) then F$Load, which searches only CHX** — not
   `PATH`. Bare-name invocation additionally needs RunB itself resolvable
   the same way: preload it (`load runb` in a startup file — resident
   modules are findable regardless of CHX) or have `runb` present in the
   CHX directory.
   **Only a bare name resolves — never a pathname.** `runb /path/to/mod`
   and `/path/to/mod` both fail with `Error #000:043` regardless of
   residency. Invoke by bare name from a CHX where it resolves.
3. **`RUN <sibling>` inside a running packed module:** resolves via
   **F$Link against the module directory**. Loading a packed group file
   registers every member procedure as a resident module by name; sibling
   calls link to those.

## Residency contamination (context 3 hazard)

Modules registered by running a packed group file **stay resident after
the program ends — and after `BYE`** (`mdir` from the shell shows them). A
later run of a *different* packed file reusing the same procedure names
resolves sibling `RUN`s against the stale residents, silently changing
results. For experiments that matter, run in a fresh emulator/system
instance and audit `mdir` when results look impossible.

Related, os9exec-specific: older os9exec builds intercepted `F$Link` for
names matching emulator-internal commands (`move`, `dir`, `copy`, …), so a
packed procedure named e.g. `move` crashed at its `RUN` with varying
errors (BASIC09 043, `E_ILLINS`, `E_BUSERR`). Fixed (a genuine resident
module now wins over an internal command); on an old build, check the
procedure's name against the internal-command list before suspecting the
program.

## Command-line arguments

Arguments after the module name bind positionally to the entry procedure's
`PARAM` list (`Live`, strings and numerics):

- `runb report hello` + `PARAM n$:STRING` → `n$="hello"`.
- Numeric conversion works: `runb calc 42` + `PARAM n:INTEGER` → 42.
- Each whitespace-separated token maps to one PARAM slot in order; a
  STRING param never swallows more than one token.
- **PARAM syntax:** per-variable type suffixes (`PARAM a$:STRING,
  b$:STRING`) are a compile error (`#000:011`). Group like `DIM`:
  `PARAM a$, b$: STRING`, one PARAM statement per type.

## `**** Can't install trap handler ****` triage

This banner + `Error #000:216 (E_PNNF)` has several distinct causes:

1. **First `LOAD`/`RUN` touching numeric variables → the `math` trap
   module (TRAP #15) isn't reachable.** Fix: `load math` (put it in the
   startup file); the lazy-linking mechanism is in
   `basic09-per-target.md`. **`Live`**: `load`'s `-s` flag silently fails
   to make `cio`/`math` resident — `load -s cio csl math` in `/h0/startup`
   left only `csl` in `mdir` after a fresh boot, and `load -s math` alone
   fails the same way, while a plain `load math` succeeds every time.
   Whether this is os9exec's command handling or the real Microware
   `load`'s `-s` path is unestablished. Workaround: plain `load math` /
   `load cio`, no flag, once per session.
2. **`cio`/`csl` genuinely not resident** (check `mdir`): `load cio`. A
   binary linked against the proprietary `cio` handler dies with this
   banner on any disk lacking it — see `common/using-os9exec-repl.md` for
   classifying and rebuilding cio-locked binaries.
3. **os9exec-specific intermittent failure** where `mdir` shows the module
   *is* resident: an emulator-level race (timing-sensitive, historically
   correlated with baud-rate pacing). Restart the emulator session; if it
   recurs, it's an os9exec bug, not your program.

The mechanism behind all three: installing a trap handler resolves the
handler module via the same F$Link-then-F$Load(CHX) path as everything
else; when that fails, the requesting module prints its own "can't
install" banner and aborts.

---
Sources: BASIC09 Reference Manual (Rev H) and OS-9 BASIC User Manual
(Rev G) for PACK/RunB semantics and the RUN search order; everything
marked `Live` was confirmed by direct experiment on os9exec
(OS-9/68k v2.4 environment).
