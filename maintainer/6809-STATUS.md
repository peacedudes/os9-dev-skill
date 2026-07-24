# 6809 Reference — Status

**This file previously described a paused mid-synthesis phase ("resume
here"). That pause is over — the "not yet done" items from that phase are
now done.** Kept as a historical/confidence-tier note, not an active
resume point.

**Built:** `syscalls-and-module-format.md`, `assembly-and-tools.md`,
`coco-dragon-hardware.md` (this directory); `6809-level2-mmu.md` in the
sibling `os9-systems-dev` skill; `common/` files in `os9-dev` generalized
where 6809 confirmed shared OS-9-wide concepts (`unix-differences.md`,
`os9-mental-model.md`, `error-codes.md`); BASIC09 content consolidated
into a shared `basic09/basic09-language.md` (architecture-neutral) plus
short per-architecture delta files (`basic09-cheatsheet.md` for 6809,
`os9-68k-basic-cheatsheet.md` for 68k) — the tightening/worked-example
pass once listed as outstanding here is done, and superseded by that
consolidation.

**Confidence caveat, partially updated:** a working 6809 live-test
environment now exists — as of 2026-07-16 a full scripted REPL to a live
NitrOS-9 shell (`tools/nitros9repl.sh` in the os9exec repo — see
`using-nitros9-repl.md` in this directory), on top of the earlier
unattended XRoar boot and ToolShed host-side disk-edit technique. That
capability has verified a handful of real facts so far (the `setime<>>>/1`
startup-blocking behavior, SCF's Escape-is-EOF default, the DriveWire
DWINIT/poller gating) but has **not yet** been used to systematically
re-check the assembler,
debugger, syscall, or module-format claims already written in this
directory — those still rely on cross-referencing multiple independent
manuals against each other (`Manual`, real signal but weaker than `Live`)
and should stay tagged that way until a dedicated pass runs live tests
against them the way the 68k material was checked. Live
verification on the 68k side caught real errors this style of
cross-referencing missed (a module header offset, a C `int` size, an
INTEGER-overflow discrepancy between manual and live test, an infix-vs-
function-call syntax bug in LAND/LOR) — the same category of error is
still likely to be lurking here until that pass happens.

**First BASIC09-specific live-verification pass done, 2026-07-16.**
Against real Microware BASIC09 "6809 VERSION 01.01.00" via
`nitros9repl.sh`: INTEGER overflow wrap (`32767+1`→`-32768`, resolving the
previously-unsettled-without-real-hardware question in
`basic09-vs-68k-differences.md`), hex constant sign flip (`$FFFF`→`-1`),
BOOLEAN-in-numeric-expression compile-time error (`#067`), `RND(n>0)`
fractional-REAL behavior, `PRINT USING` boolean mixed-case (`"True"`), and
`SQR`/`SQRT` being the same function all confirmed identical to 68k —
architecture-neutral as expected. Two real 6809-specific divergences
found: **`REAL÷0` does NOT crash the process on 6809** (unlike 68k's
uncatchable trap) — it raises a catchable `Error #045` and drops into
Debug Mode; and **the 68k `DATE$` Y2K leading-digit bug does NOT
reproduce on 6809** (`DATE$` printed correctly), refuting an earlier
prediction that it would. See `basic09/gotchas.md` and
`basic09/basic09-vs-68k-differences.md` for details. Live speed
comparisons (interpreted 6809 vs. interpreted 68k vs. native `basic09c`)
are in `tools/benchmarks/basic09-vs-basic09c-differences.md` in the
os9exec repo.

**Assembler/debugger/module-format pass done, 2026-07-16/17 — full
assemble→run→confirm cycle achieved via `asm`; `rma` root-caused as a
real, unresolved bug, not chased further.** `Live` end-to-end:
the `asm` assembler correctly processes real MOD/EMOD 6809 source
(directives, `fcs`, `equ *`, `swi2`+`fcb` syscall encoding, PC-relative
addressing) — this is the concrete answer to "can you compile under 6809
through this REPL": **yes, completely, via `asm`**. A real assembled
test program was run and its output confirmed live (`I$WritLn`=$8C and
`F$Exit`=$06 behaviorally verified, not just syntactically). Found along
the way: `asm`'s object output writes to the *execution* directory
(`CMDS`), same as BASIC09's `PACK` — check there, not the current data
directory, before concluding a run silently failed. The debugger's `:`
register-display command and its entry-state `CC` E-flag convention are
`Live`. OS9Defs' `Prgrm`/`Objct`/`ReEnt` constants and the module
type/attribute byte encoding are `Source` (cross-validated against
`ident`'s own decode of real system modules).

**`rma` (the Relocating Macro Assembler — the tool
`assembly-and-tools.md`'s PSECT/VSECT/RLINK section describes) hangs
indefinitely on this disk/XRoar setup — root-cause investigation
exhausted reasonable black-box options, genuinely unresolved.** Confirmed
via 8+ minutes of `ps`/`lsof`-verified stable host-side connection (zero
drops) while XRoar's own CPU stayed active (~12%) — a real bug in `rma`
itself, this disk image, or XRoar's 6809-core emulation, not a REPL/tmux
plumbing issue (that theory was directly disproven, not just assumed).
Also ruled out: wrong syntax (matches RMA's own official Microware help
text exactly) and insufficient memory (the `#<size>k` fix that helps
undersized BASIC09 programs doesn't even reach `rma` — immediate `WHAT?`
from the shell first). Full detail and every ruled-out theory in
`using-nitros9-repl.md`'s own updated header. This means the RLINK
multi-file build path, and any syscall codes gated on it, remain
unverified through this REPL — a real, root-caused-as-far-as-practical
gap. Picking this back up should start with XRoar's `-trap`/`-trap-trace`
conditional tracing (needs a known trigger address — not cheaply
available without GDB) or the plain `l2_coco3.dsk` disk mentioned in
`feature-drivewire-virtual-serial-repl` as an alternate environment,
rather than re-running the same repro.

**`utility-usage.md` built, 2026-07-17 — VERIFICATION-BACKLOG.md item 1
(the biggest 6809 parity gap) done.** Card-extracted from the Level 2
Operating System Manual's full System Command Descriptions chapter
(~45 commands, ATTR through XMODE) plus four cross-check sources (two
Level 1 Users Manuals, two Farna CoCo Quick References); synthesized
into a 68k-`utility-usage.md`-style catalog. A handful of items were
additionally confirmed `Live` via `help <name>` on nitros9repl.sh:
`dcheck`'s option letters (including what `-s` does, previously
undocumented anywhere), `wcreate -s=<type>`'s full screen-type table,
`tmode`/`xmode`'s `baud=` bit layout and code table (the primary
source's own table was OCR-corrupted, and the cross-check sources'
version turned out subtly wrong too — live output is the corrected
one), `psc=` as the real parameter name (`pse=` was an OCR error),
`cobbler`'s continued existence at Level 2 (contradicting a Level 1
manual's claim it was superseded), and NitrOS-9's own `format` syntax
(a modern rewrite, documented separately from the vintage manual's
form since they don't match). Open ends: `ex`/`list`/`wmode` still need
their actual Level 2 manual entries pulled (extraction-task-split
oversight, not evidence they're missing from Level 2); `format`'s
vintage dash-prefixed density letters (`-sd`/`-dd`) remain unconfirmed
since NitrOS-9's own `format` doesn't use them at all. Card trail kept
at `docs/superpowers/plans/2026-07-17-6809-utility-usage/cards/` in the
os9exec repo.

**`gfx-windowing.md` built, 2026-07-17 — VERIFICATION-BACKLOG.md item 2
(GFX/GFX2/windowing API) done, the previously completely-uncovered CoCo
BASIC09 graphics story.** Card-extracted from the Level 2 Operating
System Manual's GFX/GFX2 chapter (Chapter 9, lines 19300-24175 — both the
Level 1 low-resolution `GFX` module and the Level 2 high-resolution
`GFX2` windowing/graphics module), cross-checked against an independent
second OCR of the same appendix reprinted in the BASIC09 Reference
Manual (Tandy). The cross-check reported no actual behavioral
disagreements with the primary source, only much heavier OCR noise
(notably on the module name `GFX2` itself, misread as `GEX2`/`GEN2`/
`GEXA`/etc. throughout). One genuine cross-reference win: `DWSET`'s and
`GPLOAD`'s numeric window/screen-format codes match `wcreate -s=<type>`'s
table in `utility-usage.md` byte-for-byte (resolution, color count, and
memory size all line up) — since that table is tagged `Live`, the GFX2
format codes carry that same weight by inference, without themselves
being independently confirmed `Live`. Open
ends: `GFX`'s `GCOLOR`/`GCOLR` function (name resolved via the Tandy
cross-check, but its full parameter list was never captured by either
source); `OWEND`, `GOSET`, and `COLGR` are all referenced only in passing
inside other functions' examples and have no documented entry anywhere
in this pass; `DEFBUFF` vs. `DEFBUF` spelling and `FONT`'s built-in font
group number (200 vs. 206) are unresolved disagreements between two
reads of the primary source itself. **`Manual` throughout** —
text-REPL testing can't observe pixel output, so this file is expected
to stay `Manual` longer than the rest of the 6809 corpus; the non-visual
mechanics (buffer/window bookkeeping,
error behavior) remain a legitimate future live-test target even though
the graphics themselves aren't. Card trail kept at
`docs/superpowers/plans/2026-07-17-6809-gfx-windowing/cards/` in the
os9exec repo.

**`syscalls-and-module-format.md`'s privileged-call register gap closed,
2026-07-17 — VERIFICATION-BACKLOG.md item 3 (per-call register contracts)
done.** Prior to this pass the file's user-mode `F$` ($00-$1D) and `I$`
($80-$90) tables already carried full register in/out (an undocumented
holdover from the earlier density rewrite) — the actual remaining gap was
narrower than the backlog text implied: the **privileged/kernel-internal
`F$` calls ($28-$52)** had codes and one-line descriptions only, no
registers. Closed by card-extracting the System Programmer's Manual's
Chapters 11.2 ("System Mode Service Requests," 11 universal privileged
calls) and 12.1 ("Level Two System Service Requests," 34 DAT/Level-2
calls) — both give full INPUT/OUTPUT register listings per call, a richer
source than the Rev F1 errata's condensed Appendix E. 40 of the 43
privileged-table rows now carry Params; hex codes themselves were **not**
re-derived from these chapters (their OCR has real code collisions, e.g.
`F$AllPrc`/`F$FModul` both reading `$4B`, `F$CpyMem`/`F$GPrDsc` both
reading `$18`) — the table's pre-existing, two-source `Manual` Code
column was trusted throughout instead. One incidental find: `F$GModDr`'s
existing user-mode row was missing two input registers (`Y`/`U`) that
Chapter 12.1 documents; added. **Still open:** `F$SSvc`($32),
`F$GCMDir`($52), `F$LDAXYP`($47), and `F$DATTmp`($45) have no
register-level entry in either chapter (or anywhere else checked) — codes
and descriptions only. The mixed-range calls `F$Alarm`/`F$NMLink`/
`F$NMLoad`/`F$VIRQ`, and codes `$1F`/`$20`/`$23`-`$26`, remain completely
undocumented beyond what was already there. Shingle-scanned clean (no new
verbatim runs introduced). Card trail:
`docs/superpowers/plans/2026-07-17-6809-syscall-registers/cards/` in the
os9exec repo.

**Level 1 vs Level 2 user-visible differences done, 2026-07-17 —
VERIFICATION-BACKLOG.md item 4.** Added a "Level 1 vs Level 2" section to
`utility-usage.md` consolidating what was previously scattered: windowing
(`wcreate`/`wmode`/`montype`/`tuneport`/`GFX2`) is Level-2-only, Level 1
has one physical screen and no windowing subsystem; per-program memory
limits are similar in practice (~56-60K both levels) but different in
mechanism (flat address space leftover vs. DAT-image reserved blocks —
cross-referenced to `os9-systems-dev`'s `6809-level2-mmu.md`); confirmed
directly against the Level 2 manual's own worked example that the `#n`/
`#nK` memory modifier does **not** diverge by level (was an open question
in the backlog item, now closed — no divergence exists). Also added two
special `DWSET` `format` values to `gfx-windowing.md` that were missing
from its format-code table: `$00` (process's current screen) and `$FF`
(current displayed screen, for procedures deliberately merging several
windows onto one physical display) — found while sourcing this item,
from the same Table 9.6 already used for the standard format codes.
Shingle-scanned clean against the Level 2 manual (one caught match fixed
by rephrasing during this pass).

**Scope decisions recorded, 2026-07-17 — VERIFICATION-BACKLOG.md item 5.**
O-FLEX and the Hi-Res Screen Dump Utilities marked out of scope (niche,
low value relative to size). OS-9 Pascal was briefly queued as a new
item 6, then reversed the same session after checking whether the actual
compiler was obtainable — real 1984 Microware Pascal disk images do
exist on `colorcomputerarchive.com` (same archive this project's manuals
already come from), but running proprietary binaries is a different act
than mining a manual, and the owner decided Pascal (and other niche
languages noted in passing — CIS COBOL, a Lisp) doesn't belong in this
project's scope. Priority stays on consolidating items 1-4, not new
languages.

**Gap-closing pass, 2026-07-17 — most of items 1-3/4's "still open" notes
resolved.** Checked sources beyond what the original passes used, and
found most of what looked like genuine gaps was actually an incomplete
search:
- `gfx-windowing.md`: `GCOLR`'s full syntax found in the BASIC09
  Reference Manual Rev G (`RUN GFX("Gcolr",[X,Y,]Color)` — a source the
  original GFX pass never checked); `OWEND` confirmed as a no-argument
  call from five converging worked examples across two manuals (not
  `DWEND`'s path-taking shape, as originally guessed); `DEFBUFF`'s
  spelling settled in favor of the double-F reading, re-confirmed against
  the primary source's own header/syntax/index together; `FONT`'s
  built-in group number settled at 200 from the primary source's own
  prose (not just its garbled numeric example). **`COLGR` turned out to
  be a false positive** — it's a BASIC09 variable name the source's own
  example programs declare (`DIM ...,COLGR: INTEGER`), not a function at
  all; there was never a real gap there. `GOSET` and `PALETTE`'s
  register-number range remain genuinely open after re-checking directly.
- `syscalls-and-module-format.md`: `F$LDAXYP` and `F$DATTmp` were
  actually in the Rev F1 Appendix E all along — the original search used
  a regex anchor that silently skipped entries with leading whitespace,
  a real bug in that pass, not a real source gap. `F$SSvc` and
  `F$GCMDir` (plus the whole mixed range — `F$Alarm`/`F$NMLink`/
  `F$NMLoad`/`F$VIRQ`) resolved from the OS-9 Technical Reference
  (Tandy), a source neither the original nor the gap-closing search of
  Chapters 11.2/12.1 had checked; its own per-call "Entry
  Conditions/Exit Conditions/Error Output" catalog turned out to cover
  calls neither of the other two appendices did. `F$GCMDir` also picked
  up a second independent source for its code in the process, upgrading
  it out of "single-source only." **Still genuinely open** after this
  pass: codes `$1F`/`$20`/`$23`-`$26` (corpus-wide search, zero hits
  anywhere); `ex`/`list`/`wmode`'s Level 2 manual entries (item 1, not
  touched this pass); 6809's own remaining syscall table (only
  `I$WritLn`/`F$Exit` are tagged `Live` — everything above is `Manual`,
  a different tier, see the "6809 (secondary priority)" section of
  `VERIFICATION-BACKLOG.md`).
  All edits shingle-scanned clean against every source touched (several
  near-verbatim phrasings caught and rewritten during this pass — see
  git history for `gfx-windowing.md`/`syscalls-and-module-format.md` if
  the specific wording matters).

**New cross-check resource, 2026-07-17: NitrOS-9 kernel source cloned
locally** at `os9/nitros9/source/` (outside any git-tracked repo,
`--depth 1`), the 6809 analog of `os9exec`'s own C source already
serving 68k facts — secondary cross-check only, never primary, never
extracted at length (owner-approved despite no confirmed license found;
see project memory `nitros9-kernel-source-crosscheck` for the full
provenance trail). First payoff: `F$SSvc`'s row above got two new,
manual-independent facts from `fssvc.asm` — the init table's `$80`
terminator byte and the system/user-dispatch-table split by the function
code's high bit. Also surfaced a caution: `fgcmdir.asm`'s own header
comment describes a different call's parameters entirely (visible
copy-paste error) — the actual instruction sequence is what should be
trusted, not comments, even in source that's otherwise reliable. This
resource is now available for future 68k↔6809-analog verification work;
not yet used beyond these two calls.

**Full NitrOS-9 source cross-check sweep, 2026-07-17 — all ~93 F$/I$
calls in `syscalls-and-module-format.md` checked against real kernel
code.** Done as 8 sequential Haiku batches (one at a time, not
parallel), each verifying documented register claims against the actual
instruction sequence rather than trusting header comments. Real findings
folded in:
- **`I$Write`/`I$ReadLn` had swapped codes** ($8A/$8B) — the biggest
  catch of the pass, found while chasing down a Haiku-reported "dispatch
  bug" that turned out to be a false alarm (see below). Settled
  definitively against `defs/os9.d`'s sequential `RMB` call-code
  definitions, the authoritative source for this — every other code in
  the table checked out against the same file.
- **`F$CpyMem`**: NitrOS-9 never reads X at all — only D (a DAT-image
  pointer, not a block number), Y (count), U (dest). Both this table's
  prior claim *and* the source file's own header comment agreed on the
  old 4-register shape, yet the code contradicts both — genuinely
  unclear whether this is decades of NitrOS-9 drift or the original
  manual was never quite right.
- **`F$GModDr`**: Y and U were documented as inputs; they're actually
  outputs — a real correction, not just an addition.
- **`F$GProcP`**: closed a long-standing hedge ("register letter too
  narrow for a full address") — it's Y, confirmed via a 16-bit transfer.
- **`F$SchBit`**: gained two previously-undocumented return values (D=run
  start, Y=run length).
- **`I$Create`/`I$MakDir`**: a Haiku batch flagged these as missing their
  documented attributes parameter — turned out IOMan's shared dispatcher
  only touches some registers and passes the rest straight through to
  the file manager (`rbf.asm`), which does read them. Not a
  disagreement, just a two-layer call needing a second look.
- **RESOLVED — `F$Alarm`**: NitrOS-9's `clock.asm` D-register mode
  selector (clear/system-wide/query/per-PID) is `Live`-confirmed real —
  `D=0`/`D=2` succeeded and `D=99` failed under identical (unset) X,
  proving D is inspected. See `syscalls-and-module-format.md`'s F$Alarm
  entry for the test detail. Still open: whether this is a NitrOS-9
  evolution over the 1984 Technical Reference or a manual gap even for
  original hardware — the live test settles *that D matters*, not *why
  the manual omits it*.
- **False alarm caught and disproven**: a batch reported I$SetStt's
  dispatch-table entry pointing at the Seek handler as a kernel bug.
  Traced by hand against `defs/os9.d`'s authoritative code numbering —
  it's intentional: IOMan shares one generic "resolve path, call file
  manager" stub across several calls whose IOMan-level handling is
  identical, with the file manager doing the actual differentiation via
  the preserved original call code. No bug. This — plus the `I$Write`/
  `I$ReadLn` swap it led to finding — is the clearest evidence yet that
  Haiku-reported DISAGREEMENTs need independent verification before
  being trusted, same as its CONFIRMS being generally reliable across
  ~80 other calls in this sweep.
- **`F$Load`/`F$IRQ`/`F$NMLink`/`F$NMLoad`/`F$IOQu`**: genuinely not
  located in the source tree despite real search effort at each one's
  expected location plus broader fallback searches — noted as open, not
  silently dropped.

Every edit shingle-scanned clean against the specific NitrOS-9 files it
drew from. The overwhelming majority of the ~93 calls (around 80)
simply confirmed what was already documented — this was a solidification
pass, not a rewrite.

**2026-07-19 — the rest of the "6809 (secondary priority)" backlog cleared
in one push, syscall table + debugger + `asm` options + GFX2 visual
verification.** Full detail in
`test/6809-live-verification/dogfood-report-syscalls-2026-07-19.md` and
`dogfood-report-debugger-asm-2026-07-19.md` (os9exec repo).

- **Syscalls**: `F$Link`, `F$UnLink`, `F$Fork`, `F$Wait`, `F$Time`,
  `I$Open`, `I$Close`, `I$Read`, `I$Write` now `Live` (14 of ~60 total,
  up from 5), tested success **and** failure paths as a re-runnable
  `PASS`/`FAIL` regression suite (`syscall-flink-ffork-fwait.a`,
  `syscall-ftime-iread-iwrite.a`). New facts: `F$Time`'s year byte is
  `year-1900`; `I$Write` does return `Y`; `F$Link` (resident-directory
  search only) and `F$Fork` (does its own filesystem load) fail with
  *different* codes against an unresolvable name (`E$MNF`/221 vs
  `E$PNNF`/216); `F$Wait` with no children fails `E$NoChld`/226.
- **Debugger**: essentially the entire command table is now `Live` —
  calculator mode, all Dot-navigation forms, `:reg` get/set, `S`
  (search), `$` (shell escape), `Q`, joining the already-`Live` `B`/`G`/
  `M`/`E`/`:`. `K` closed 2026-07-19 (both forms: `K expr` clears the one
  named, bare `K` clears all) — the command set is now fully `Live`.
  See `assembly-and-tools.md`'s Debugger section.
- **`asm` options (2026-07-19)**: `L`/`S` confirmed `Live` (exact
  documented listing and symbol-table format). `W40` truncates listing
  lines at exactly 40 columns and cuts `fcc` strings mid-content,
  confirming the column-50 comment-field warning (the `W80` default
  number itself is unexercised — no test line exceeded 80). `E` `-E`
  suppresses the `***** Error:` text but still flags the line with `E`
  in its info field and still counts the errors. `D5` produced 42 tiny
  pages for a 13-line source, confirming the page-depth mechanism. `N`
  drops the columnized layout entirely. `G` tested but genuinely
  inconclusive — no observable difference found on the directives
  tried. `U` likewise shows no observable effect, inconclusive. **`I` is
  a real bug**: every line gets an `ASM:` prefix, but the assembled
  module header comes out corrupted (`87CD3103` vs. the correct
  `87CD001D`) while still reporting `00000 error(s)` — don't use `I`
  assembling a file passed as a command-line argument. Only `C`/`F`/`M`
  (beyond the Motorola-mode note elsewhere in `assembly-and-tools.md`)
  remain untested.
- **Editor**: attempted, inconclusive — the on-disk tool's identity
  doesn't clearly match this section's documented `L`/`X`/`I n str`
  line-and-buffer syntax (`ed` is a different, GUI graphics-window
  editor entirely; `edt`/"6EDT" gave an ambiguous probe response). Left
  `Manual` rather than force a confirmation. Real open item for a future
  pass, not silently dropped.
- Also (same session, different file): the 6809 GFX2 visual-verification
  pass (`DRAW`/`GET`/`PUT`/`LOGIC`/`PATTERN`/`FONT`/`OWSET`/`CWAREA`) —
  see `gfx-windowing.md` and
  `test/6809-live-verification/dogfood-gfx-pixels-2026-07-18.md`.

**2026-07-19, later same day — second syscall batch (24/~60 total now
`Live`) plus the decisive RBF record-lock contention test.** Full detail:
`dogfood-report-syscalls-batch2-2026-07-19.md` and
`dogfood-report-lockcontention-6809-2026-07-19.md` (os9exec repo).

- **Syscalls**: `I$Create`, `I$MakDir`, `I$ChgDir`, `I$Delete`, `I$Seek`,
  `I$GetStt` (call confirmed; SS.SIZ's return-value convention is not —
  a guessed X:U readback didn't check out against a known file size),
  `F$Mem`, `F$Sleep`, `F$SPrior`, `F$CRC` now `Live`. `I$Seek` confirms
  the `Source`-flagged X:U 32-bit position convention live, not just
  from reading NitrOS-9's own code. Incidental: `F$Sleep(50)` returned
  with `remaining=23`, not `0` — noted, not chased. A third
  register-clobber bug hit writing these tests (`I$Seek`'s own
  convention needs `U`, which doubled as the test program's own
  data-area base pointer) — same class of bug as batch 1, now a
  recurring lesson for any 6809 test using `X`/`U` for real syscall
  data.
- **Decisive record-lock contention test — sharpens the lost-update
  finding, doesn't contradict it.** A holder `GET`s a record and
  deliberately holds it (real delay) before `PUT`; a concurrent waiter's
  `GET` on the same record blocked until the holder released, in both of
  two independent runs, reading back the released value, never the
  stale one. **NitrOS-9's record lock is real and does block — the
  lost-update result (457/584 out of 600) is a timing-dependent race in
  rapid release-then-reacquire cycles specifically, not an absent
  lock.** `file-managers.md`'s Record Locking section and the
  `rbf-lostupdate-6809-diverges-from-68k` project memory both updated to
  this more precise characterization.
- **Syscall batch 3 — 13 more calls `Live` (37 of ~60 total), plus two
  harness findings.** `F$ID`(re-confirmed)/`F$PrsNam`/`F$PErr`/
  `F$AllBit`/`F$DelBit`/`F$GPrDsc`/`F$GModDr`/`I$Dup`/`I$WritLn`/
  `I$DeletX` confirmed cleanly; `F$CmpNam`/`F$SchBit`/`F$GBlkMp`
  dispatch but produce results that diverge from a naive reading of the
  docs, left inconclusive rather than asserted; `F$GProcP` genuinely
  fails live (`err=00208`, uninvestigated). Five register-clobber/
  addressing bugs found and fixed in the test sources themselves.
  Harness finding 1: `asm` needs an explicit `-O=<name>` to persist a
  `CMDS` module — a bare `asm file.a` reports `0 errors` but writes
  nothing. Harness finding 2: **this NitrOS-9 disk has no `claude`
  account** (`list /dd/sys/password` shows only an unnamed UID-0 entry
  and `USER1`-`USER4`), and `nitros9repl.sh start` never logs in as
  anyone — **`login USER1` should be the first step of every 6809 test
  session going forward**. Also: the `CLAUDE` directory refuses
  brand-new file creates (`E$CEF`/218) despite 170,000+ free disk
  sectors and the same create working at the disk root — work around by
  creating fixtures at the root, not root-caused. See
  `dogfood-report-syscalls-batch3-2026-07-19.md`.
- **Syscall batch 4 — 8 more calls `Live` (45 of ~60 total), one real
  pattern resolved.** `F$Load`/`I$Attach`/`I$Detach` confirmed cleanly;
  `F$UnLoad` fails unexpectedly right after loading the same name
  (inconclusive); `F$SSWI`'s install is accepted but handler-invocation
  couldn't be confirmed (no documented handler-exit convention exists
  for it specifically). **`F$SRqMem`/`F$Move`/`F$FModul` are genuinely
  unimplemented on this kernel build** — `err=00208`=`E$UnkSvc`, the
  same code `F$GProcP` hit in batch 3 (then uninvestigated, now
  resolved): this is a real, repeatable "not implemented" signal on
  this build, specifically for calls whose docs already flag a
  Level-2/multi-address-space dependency, not a test bug. See
  `dogfood-report-syscalls-batch4-2026-07-19.md`.
- **Syscall batch 5 — swept essentially all remaining calls (70 of ~93
  total), the `E$UnkSvc` pattern now firmly established across 18
  calls.** `F$SUser`/`F$CpyMem`/`F$VIRQ`/`F$AllRAM`/`F$DelRam`/
  `F$NMLink`/`F$NMLoad` confirmed working; `F$VModul`/`F$SLink`/
  `F$BtMem`/`F$AllPrc`/`F$AllImg`/`F$SetImg`/`F$ResTsk`/`F$DATLog`/
  `F$DATTmp`/`F$LDAXY`/`F$LDAXYP`/`F$LDDDXY`/`F$LDABX`/`F$STABX`
  confirmed unimplemented. **`F$MapBlk` is a real exception — actually
  implemented**, unlike its documented Level-2 siblings. **F$Chain
  RESOLVED (2026-07-21): faithful, not a bug.** Its failure path produced
  a raw kernel error with no program output because `fchain.asm` unlinks
  the old primary module and frees the old DAT blocks before linking the
  new one, then `F$Exit`s on failure (Level-2) / condemns the process
  (Level-1) — the caller is torn down before the target resolves, so a bad
  name kills it with nothing to return to. os9exec's 68k `F$Chain` does the
  same; owner-confirmed intent. Do not re-flag. `F$DelPrc` deliberately
  never attempted (self-termination risk — no safe PID to pass).
  Deliberately still excluded: `F$Boot`, `F$AProc`/`F$NProc`,
  `F$GCMDir`, `F$IOQu`, `F$IRQ`, `F$IODel`, `F$SSvc`, `I$SetStt` — all
  have a real crash/hang/system-corruption risk profile distinct from
  "might just be unimplemented." One unexplained REPL connection stall
  after the `F$VIRQ` test, recovered with a clean restart — timing is
  circumstantial, not confirmed causal. See
  `dogfood-report-syscalls-batch5-2026-07-19.md`.
