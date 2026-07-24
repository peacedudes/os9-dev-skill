# Confidence tags

Shared by `os9-dev` and `os9-systems-dev`. Every factual claim in either
skill that isn't self-evidently a stable, published spec detail carries one
of these, inline, next to the claim it qualifies.

| Tag | Meaning |
|---|---|
| `Hearsay` | Stated directly by a person, not from any manual or test. **Lowest** confidence. |
| `Manual` | Derived from and cross-referenced across published manuals. Not run, not checked against code. |
| `Source` | Checked against real source code (os9exec's C, or NitrOS-9's open kernel source) — not run for this specific claim. |
| `Live` | Actually run and observed under os9exec or NitrOS-9. **Evidence about a reimplementation, not about OS-9.** |
| `Absent` | Actively searched for and confirmed **not to exist** — distinct from "nobody's checked yet". One line, a fact stamp. Add a clause only to state what happens instead (e.g. 6809 has no `events` utility because it uses `F$Send`/`F$Icpt`/`F$Sleep` signals rather than 68k's named-event objects) — never describe the syntax the absent thing *would* have had. |
| `Flag` | Two or more sources disagree; unresolved. |

`Absent` and `Flag` are status flags, not evidence tiers — they sit alongside
the others rather than replacing them.

## Ordering

`Hearsay` < `Manual` < `Source` < `Live`. **This ranks how well we know what
the runtimes do. It does not rank authority over what OS-9 is.** For that a
Microware manual is the specification and both runtimes are candidate defects
— see `SOURCE-AUTHORITY.md`.

Where stronger evidence **confirms** a weaker claim, replace the tag. Where it
**contradicts** one, combine — keep the higher tier plus `Flag`, so the
disagreement isn't silently erased (`Source, Flag` when a struct offset in
os9exec's code contradicts the manual).

**A `Live` observation does not clear a `Flag` against an authoritative
manual.** Running a reimplementation tells you what that reimplementation
does; it is not evidence that Microware's manual is wrong.

- `Live` clears a `Flag` only where **no authoritative manual speaks** — an
  emulator-internal detail, a harness behaviour, a question the manuals don't
  address.
- Where a manual **does** speak and a runtime disagrees, the `Flag` stays, the
  claim gets an entry in `DIVERGENCES.md`, and an inline `⚠ DIVERGENCE D-NNN`
  marker sits at the point of use.
- Only Microware, or a test on genuine OS-9 hardware, resolves a divergence.

Phrasing follows from this: write "os9exec and NitrOS-9 both do X, the manual
specifies Y" — not "the manual is wrong". Two community reimplementations
agreeing with each other is not the manual being wrong.
