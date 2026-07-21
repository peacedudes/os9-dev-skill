# OS-9 skills improvement plan

Prioritized work to make the `os9-dev` and `os9-systems-dev` skills more
accurate and complete. Written 2026-07-21 after a large 68k live-verification
pass. Delete items as they're done; keep this list to open work only.

**Context:** the 68k *application* surface (C library, BASIC09, shell, assembly
entry-state) is now thoroughly `Live`-verified — that was the recent push and
it found ~6 real doc errors plus many upgrades. The gaps below are what's left.
The reusable method that worked: compile tiny C probes / BASIC09 procedures via
os9exec, byte-dump results (`PUT`/`fwrite` to `/h5` then `xxd` host-side),
survey `clib.l` symbols with `strings` then link-test every "absent", and use
`debug <prog>` for entry register state. Compile with `-F=/h5/<name>` to keep
output off the system disk. Never source from `h0/SYS/errmsg` (copyrighted).

---

## 1. 6809 needs the 68k treatment (highest content ROI)
Most 6809 claims are still `Manual`; only a handful are `Live`. The same
verification pass done on 68k would find as much on 6809 — byte-dumps,
symbol/behavior tests, gotcha hunting, div-zero/float/string-terminator checks,
etc. **Blocked only by harness contention:** the NitrOS-9/XRoar + DriveWire
harness is the concurrent RBF-hammer session's. The clone-isolation
(`NITROS9REPL_DISKDIR`/`_SESSION`/`_BECKER_PORT`/`_CHAN_PORT`, see
`6809/nitros9repl-setup.md`) makes it runnable alongside once that settles.
Keep 6809 live-verification on the primary model — Haiku fabricated results
before (memory `feedback_haiku-cant-drive-repl`).

## 2. Lift `os9-systems-dev` from `Manual` to `Source` — DONE (2026-07-21)
Every documented struct that HAS an os9exec anchor is now `Source`-verified
against os9exec's own C source (clean-room-safe): **Process Descriptor**
(`procid`), **module header / executable / device descriptor**
(`modhcom`/`mod_exec`/`mod_dev` in `module_from_book.h`, with compile-time
`offsetof` assertions), **path descriptor** (common `PD_` header + 128-byte
SCF options `struct _sgs`), and **Module Directory** (`mdir_entry` — four
32-bit big-endian fields; documented WITH os9exec's group-mirrors-address
simplification). What legitimately stays `Manual` has **no struct to check**:
System Global memory (`F$SetSys` is a self-described half-dummy), the scheduler
algorithm, driver/file-manager dispatch, and the Level-2 MMU — os9exec doesn't
emulate any of them. INDEX.md + kernel-internals.md updated to say exactly this.
Nothing left here; kept for the numbering that items below reference.

## 3. Wrap the accumulated tests into a runnable regression suite (durability)
The ~90 6809 `.a` files and the 68k live-verification programs (incl.
`bmode.c`, `pipe-abort-*`, `dmppar.a`) are orphan files, not a gate. A runner
(compile/assemble + run + check PASS/FAIL per file) would protect all this
verified behavior from silent regression. Note: the concurrent session appears
to be building 6809 test infra (`tools/nitros9-*.py`, `rl-*.sh`) — coordinate
so this doesn't duplicate theirs.

## 4. Extend the doc-consistency checker for structural rot — DONE (2026-07-21)
Added **cross-reference integrity** (an `INDEX.md` row naming a `.md` file that
doesn't exist anywhere in the skill tree, resolved by basename so bare/
tree-relative/sibling-qualified paths all work without hand-parsing "sibling X
skill" prose) and **orphaned `[[memory]]` link** detection (opt-in via
`--memory-dir <dir>`, since that path is machine-specific). Both scoped
narrowly — INDEX.md only, backtick-quoted `` `[[name]]` `` treated as
convention prose not a real link — to avoid the fragile general-prose
claim-matching this checker deliberately rejects. 50/50 tests green (12 new),
each proven to fail once before trusting green. Run for real with
`--memory-dir`, it immediately found 36 genuine orphaned `[[name]]` links
across ~15 memory files (mostly `feedback_` prefix drift) — a real maintenance
worklist, not fixed by this change. See `doc-consistency-checker` memory.

## 5. Maintain the `Live` verified-against baseline (recurring, not "done")
`CONFIDENCE-TAGS.md`'s baseline table must be re-stamped when the emulator
changes behaviour. The checker prints the stamp every run; keep it honest.
**Last re-stamped 2026-07-21** (`v0.0.0-482-g534315a` → `v0.0.0-504-g40eda43`,
22 commits, 4 touching `Source/`): found and fixed 2 stale gap claims this
same pass — `error-codes.md`'s E$Share entry still described delete-while-
open-for-write as unenforced (fixed by the concurrent session, `0ee76c1`),
and `68k/syscall-reference.md`'s F$Alarm entry still said "signal delivery on
firing not exercised" (fixed, `25991b4`, F$Sleep now correctly woken by its
own alarm). Re-check next time `git describe` in os9exec moves.

---

## Specific open items (smaller)
- **E$Share delete-open enforcement — DONE** (os9exec commit `0ee76c1`, by the
  concurrent RBF-hammer session): deleting a file held open for write now
  refuses with `E$Share` instead of orphaning its clusters. See memory
  `rbf-lock-hammer-in-progress`.
- **Single-precision float open question** (1 of 2 checker flags) — whether real
  68k OS-9's default `math` module is also single-precision, or it's an os9exec
  `math`-trap gap. Resolvable only against real 68k hardware.
- **Low-value 68k `Manual` leftovers** — `module-format.md`'s 6809-C
  type/language byte; the PSECT-inside restriction; `tmode`/`xmode` semantics
  (explicitly low-value to live-test on the emulator).
- **Second checker flag** is the 6809 nitros9repl timing note — resolve as part
  of item 1 (its file is the concurrent session's; hold until free).
