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

## 1. 6809 needs the 68k treatment (highest content ROI) — UNBLOCKED, STARTED
Most 6809 claims are still `Manual`; only a handful are `Live`. The same
verification pass done on 68k would find as much on 6809 — byte-dumps,
symbol/behavior tests, gotcha hunting, div-zero/float/string-terminator checks,
etc. **No longer blocked** (2026-07-23): the RBF-hammer session that owned the
NitrOS-9/XRoar + DriveWire harness has closed, and the harness ran clean for a
full session. Keep 6809 live-verification on the primary model — Haiku
fabricated results before (memory `feedback_haiku-cant-drive-repl`).

**First pass done 2026-07-23** (memory `6809-verification-pass-2026-07-23`):
`PRINT USING "B8"` confirmed on real 6809 (manual wrong on both architectures);
`SAVE`/`PACK` `>pathlist` spurious errors proven to be an `os9exec` defect, not
OS-9 (→ emulator `ROADMAP.md`); net-new fact that `SAVE >rel` resolves against
CHD while `PACK >rel` resolves against CHX; 6809 `ident` `Ty/La` shown to be a
single packed `(type << 4) | language` byte, which settles the old
`$04`-vs-`$11` question against `$11`. The channel-garble `Flag` in
`using-nitros9-repl.md` was driven at both its stated triggers and reproduced
at neither — recorded there so the experiments aren't re-run blind.

**Still open — the bulk of the work.** The ~93-call 6809 syscall table, the
debugger command set, and most of `assembly-and-tools.md` remain `Manual`.
Good next batches: syscall spot-checks against the table's register columns,
then the `6809/STATUS.md` items that say "not yet systematically re-checked".

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

## 3. Wrap the accumulated tests into a runnable regression suite — 68k PHASE 1+2 DONE (2026-07-21)
**68k half done, in os9exec's own `test/` package** (`LiveVerifyCore`/
`LiveVerify`, `make live-verify`): a manifest-driven Swift runner
(`test/live-verification-manifest.json` + `SoloExecutor`/
`ChoreographyExecutor`) wrapping asm/c/bas/existing-repro-script recipes
plus real PACK+runb multi-process choreography. 5-entry proof-of-concept
batch landed (spans every recipe shape), each entry proven to fail once,
all reviewed (8 tasks, 3 real fix cycles + 1 whole-branch-review fix
cycle — see design/plan docs in os9exec's `docs/superpowers/specs/` and
`docs/superpowers/plans/`, dated 2026-07-21, and memory
`live-verify-suite-68k-phase1-2-done`).
**Phase 3 (open, next)**: scale from 5 to the remaining ~81 68k corpus
files (batches, same manifest schema, each oracle authored by running the
file live first — see the design doc's Phasing section). Sizable, multi-
session work; not started.
**6809 half (open, deferred by design, not blocked the same way as item
#1)**: deliberately out of scope for the 68k work above — two reasons,
both the user's call: (a) sequencing (6809 is under active investigation
by the concurrent session, matching item #1's harness-contention
blocker); (b) where 6809 test tooling should even live (this repo vs. the
NitrOS-9 fork) is an open design question, not yet answered. Revisit once
item #1 unblocks. The ~90 6809 `.a` files are still just orphan files.

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
