# Confidence tags

Shared by `os9-dev` and `os9-systems-dev`. Every factual claim in either
skill that isn't self-evidently a stable, published spec detail carries one
of these, inline, next to the claim it qualifies.

| Tag | Meaning |
|---|---|
| `Hearsay` | Stated directly by a person, not from any manual or test. **Lowest** confidence. |
| `Manual` | Derived from and cross-referenced across published manuals. Not run, not checked against code. |
| `Source` | Checked against real source code (os9exec's C, or NitrOS-9's open kernel source) — not run for this specific claim. |
| `Live` | Actually run and observed. **Always names where** — `Live` (NitrOS-9), `Live` (os9exec), `Live` (OS-9/68000). See below. |
| `Absent` | Actively searched for and confirmed **not to exist** — distinct from "nobody's checked yet". **Always names what it is absent from**, exactly as `Live` names where it ran: `Absent` (6809), `Absent` (the v2.4 manuals), `Absent` (this SDK). One line, a fact stamp. Add a clause only to state what happens instead (e.g. 6809 has no `events` utility because it uses `F$Send`/`F$Icpt`/`F$Sleep` signals rather than 68k's named-event objects) — never describe the syntax the absent thing *would* have had. |
| `Flag` | Two or more sources disagree; unresolved. |

`Absent` and `Flag` are status flags, not evidence tiers — they sit alongside
the others rather than replacing them.

## `Live` names the implementation it was run on

"OS-9" is not one system, so "we ran it" is not one claim. A `Live` tag
therefore carries the implementation in parentheses, outside the tag's own
backticks, and a claim confirmed on more than one lists each:
`Live` (NitrOS-9, os9exec).

## `Absent` names its scope for the same reason

An absence is exactly as implementation-specific as a presence, so an unscoped
`Absent` is the same defect as a bare `Live`. "There is no `ident`" is a very
different claim from "there is no `ident` **in this SDK**" — the first tells a
reader their own OS-9 lacks a utility that Microware ships and their machine may
well have. Write the second.

The failure mode to avoid is stating a local absence as a general one. A
reader arrives with a real system, and a flat "X does not exist" that is only true
of one disk image or one toolchain is both discouraging and, from where they are
sitting, wrong. Where you can, say what *is* there instead of what is not: naming
the utility that does the job on the reader's system is more use than recording
that yours did not have it.

| Qualifier | What it is |
|---|---|
| `OS-9 L1` / `OS-9 L2` | Microware OS-9/6809, Level One / Level Two |
| `OS-9/68000` | Microware OS-9/68000 (add `+881` where the maths coprocessor matters) |
| `OS-9000` | Microware OS-9000, itself multi-target — name the target too where it matters |
| `NitrOS-9` | The open-source 6809/6309 reimplementation |
| `os9exec` | This project's own 68000 emulator and kernel reimplementation |

The list is open — name any implementation precisely rather than forcing it
into an existing bucket. A Microware system and a clone are recorded the same
way: neither is the unmarked default, because that is exactly the distinction
a reader needs to weigh the claim.

**Every `Live` tag in both skills is qualified.** A bare one is a defect —
it means the implementation went unrecorded, not that the claim holds
everywhere. One known exception is left deliberately: `os9-tools-and-shell.md`'s
`attr` cross-reference, where the underlying work spans a 6809 and a 68k
finding and picking either would invent provenance. Leaving it bare is the
honest state; resolve it by re-running, not by guessing.

**A claim carrying only clone qualifiers is evidence about a reimplementation,
not about OS-9.** Where such a claim and a Microware manual disagree, the
manual is the specification and the runtime is the candidate defect. That is
unchanged by this notation; naming the runtime makes it checkable rather than
assumed.

## Ordering

`Hearsay` < `Manual` < `Source` < `Live`. **This ranks how well we know what
the runtimes do. It does not rank authority over what OS-9 is.** For that a
Microware manual is the specification and both runtimes are candidate defects.
Microware-published documentation is authoritative, including manuals issued
under licence by Tandy/Radio Shack, Dragon Data or Motorola; third-party books
are not, however good.

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
- Where a manual **does** speak and a runtime disagrees, the `Flag` stays and
  the claim records **both readings at the point of use** — what the manual
  specifies and what the runtime does — rather than picking one.
- Only Microware, or a test on genuine OS-9 hardware, resolves a divergence.

Phrasing follows from this: write "os9exec and NitrOS-9 both do X, the manual
specifies Y" — not "the manual is wrong". Two community reimplementations
agreeing with each other is not the manual being wrong.
