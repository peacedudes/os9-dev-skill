# Confidence tags

Shared by `os9-dev` and `os9-systems-dev`. Every factual claim in either
skill that isn't self-evidently a stable, published spec detail should
carry one of these, inline, next to the claim it qualifies.

| Tag | Meaning |
|---|---|
| `Hearsay` | Stated directly by someone (the project owner or any contributor), not from any manual or test. **Lowest** confidence — expect it to be overwritten by testing. |
| `Manual` | Derived from and cross-referenced across published manuals. Not run, not checked against real code. |
| `Source` | Checked against real source code (os9exec's own C source, or NitrOS-9's open kernel source) — not actually run for this specific claim. |
| `Live` | Actually run and observed, via os9exec or the NitrOS-9 REPL (`nitros9repl.sh`). **This is evidence about a reimplementation, not about OS-9.** Both runtimes are reverse-engineered by the user community and both have had real errors; os9exec in particular is still maturing. `Live` is the strongest tier this project can *produce* — it is not the strongest tier that exists. A Microware manual outranks it on any question of what OS-9 is specified to do. |
| `Absent` | Actively searched for and confirmed **not to exist** — distinct from "nobody's checked yet." Keep these to one line: a fact stamp, not a card. Only add a clause beyond the bare tag if it states a real "what happens instead" mechanism (e.g. 6809 has no `events` utility because it uses `F$Send`/`F$Icpt`/`F$Sleep` signals instead of 68k's named-event objects) — never describe the syntax/options/behavior the absent thing *would* have had. |
| `Flag` | Two or more sources disagree; unresolved. |

## Ordering and combination

`Hearsay` < `Manual` < `Source` < `Live`. **This ordering answers "how well do
we know what the runtimes do." It does NOT answer "what is OS-9."** For that
question a Microware manual is the specification and both runtimes are
candidate defects — see `SOURCE-AUTHORITY.md` for what counts as Microware's
word.

When stronger evidence **confirms** a weaker claim, replace the tag — don't
stack `Manual` on top of a now-redundant `Hearsay`. When stronger evidence
**contradicts** a weaker claim instead, combine: keep the higher tier's tag
plus `Flag`, so the disagreement isn't silently erased (e.g. `Source, Flag`
when a struct offset checked against `os9exec`'s own code contradicts what the
manual says).

**A `Live` observation does NOT clear a `Flag` against an authoritative
manual.** This rule used to read the opposite way — "`Live` is the only tier
that actually resolves a `Flag` ... the `Flag` clears" — and that instruction
is why, at the time it was found, this repo held 540 `Live` claims against
only 5 recorded manual disagreements. Running a reimplementation and watching
it do something tells you what that reimplementation does. It is not evidence
that Microware's manual is wrong.

So:

- `Live` clears a `Flag` only where **no authoritative manual speaks** — an
  emulator-internal detail, a harness behaviour, a question the manuals do not
  address.
- Where an authoritative manual **does** speak and a runtime disagrees, the
  `Flag` **stays**, and the claim gets an entry in `DIVERGENCES.md` plus an
  inline `⚠ DIVERGENCE D-NNN` marker at the point of use. The checker enforces
  that link in both directions, so a divergence cannot be quietly filed away
  where a reader of the reference file would never see it.
- Only **Microware, or a test on genuine OS-9 hardware**, resolves a
  divergence. Neither runtime can, however many times it is run.

Phrasing matters too: write "os9exec and NitrOS-9 both do X, the manual
specifies Y" — not "the manual is wrong." Two community reimplementations
agreeing with each other is not the manual being wrong; it is a divergence,
and which side is in error is Microware's call.

`Absent` and `Flag` are status flags, not evidence tiers — they can sit
alongside `Hearsay`/`Manual`/`Source`/`Live` rather than replacing them.

This list isn't rigid — add a new tag sparingly, only for a real
recurring case that doesn't fit, not for one-off phrasing.

## What `Live` is verified against

A `Live` observation is only as current as the build that produced it, and both
emulators are moving targets — this project fixes their bugs (e.g. the `pSysTask`
keyboard-abort and `F$Event` hang fixes both landed 2026-07-21 and changed
observable behaviour). So a `Live` claim carries a **date** (`Live, 2026-07-21`),
and the build identity behind the current `Live` tier is stamped below. When a
behaviour-changing emulator commit lands, re-check the `Live` claims it could
affect and bump the relevant stamp; **a `Live` claim dated before a fix that
touches its area is suspect until re-run.**

**Current baselines** (bump when you re-verify against a newer build):

| Platform | Build identity (as of 2026-07-23) | How to read it |
|---|---|---|
| 68k (os9exec) | `git describe` in the os9exec repo — `v0.0.0-555-g50f32a2` (suite 148/0) | the `g<hash>` suffix is the exact commit; re-stamp after any `Source/OS9exec_core` change that alters behaviour |
| 6809 (NitrOS-9) | EOU disk `eou_ide-v0.3` under **XRoar 1.11** + DriveWire (`drivewire-cli`); host-side module builds via **lwasm 4.24** | disk image + emulator version together define the observable system |

This is a coarse stamp, not a per-claim version: the date on each `Live` claim is
the fine-grained marker, and this table maps "the current dates" to concrete
builds. **Don't** retrofit a version onto every historical claim — that's noise;
re-date a claim only when you actually re-run it.
