# OS-9 development skills

> **Pre-publication — not for distribution.** Circulated privately for review;
> no license is granted yet. A license will follow after review by Microware.
> See [LICENSE](LICENSE).

Two [Claude Code](https://claude.com/claude-code) skills for working with
Microware OS-9 — the real one, on 6809 and 68000.

| Skill | Covers |
|---|---|
| **`os9-dev`** | Application work: BASIC09, Microware C, 68k and 6809 assembly, the shell and utilities, modules, syscalls, error codes, driving the emulators |
| **`os9-systems-dev`** | Below the application line: device drivers, file managers, kernel internals, the scheduler, 6809 Level 2 MMU/DAT |

They are siblings and cross-reference each other; install both.

## Install

```sh
git clone <this repo> ~/Developer/os9/os9-dev-skill
ln -s ~/Developer/os9/os9-dev-skill/os9-dev         ~/.claude/skills/os9-dev
ln -s ~/Developer/os9/os9-dev-skill/os9-systems-dev ~/.claude/skills/os9-systems-dev
```

Nothing to build.

## Scope

These skills document the older end of the line — the v2.4-era 68000 system
and 6809 Level 2 — whose documentation was never centralized and now
circulates through preservation archives: manuals in varying states of OCR,
editions of the same book that don't quite agree, and files whose names
misdescribe their contents.

Some thirty published manuals, quick references and training guides stand
behind these files; `SOURCES.md` in each skill says which ones back which
file. Where two manuals disagree, both readings are recorded and marked
`Flag` rather than silently resolved in favour of one.

## Confidence

Claims were not only read but **run** — OS-9/68k under the
[os9exec](https://github.com/peacedudes/os9exec) emulator, OS-9/6809 as
NitrOS-9 under XRoar. Every claim carries an inline tag:

| Tag | Means |
|---|---|
| `Hearsay` | Someone said so. Lowest confidence; expect testing to overwrite it. |
| `Manual` | Cross-referenced across published manuals. Not run. |
| `Source` | Checked against real source code, but not run for this claim. |
| `Live` | Actually run and observed. |
| `Absent` | Searched for and confirmed not to exist — not merely unchecked. |
| `Flag` | Sources disagree; unresolved. |

**A `Live` claim is evidence about a reimplementation, never about OS-9
itself.** Both emulators are community-written reverse-engineered work and
both have had real errors. Where a runtime and a Microware manual disagree,
the manual is the specification and the runtime is the candidate defect; the
claim records both readings rather than resolving in favour of whichever one
happened to run. Only Microware, or real hardware, settles those.
`DIVERGENCES.md` collects the handful worth raising directly.
`SOURCE-AUTHORITY.md` says what counts as Microware's word — several excellent
books do not.

The 68000 material has been through a thorough live-verification pass and is
largely `Live`. So has the 6809 side: the assembler and debugger core, roughly
70 of the ~93 documented syscalls, and most of the GFX2 calling sequences.
CoCo/Dragon hardware and the 68k networking material are `Manual` only.
Nothing has been checked against real hardware. The tags say which is which on
any given line.

## Provenance

The line was drawn conservatively at every step.

All source material is public-domain or freely-published Microware/Tandy
documentation, or historical-preservation archives. **No proprietary Microware
source code was used anywhere in this chain.** Facts are stated as facts — a
register contract, an error number, a struct offset — but the prose around
them is written here rather than borrowed: no raw manual text reproduced, no
worked code example kept verbatim, no file mirroring a source's chapter
structure.

What was deliberately *not* used is recorded too, in `SOURCES.md`, with the
reasoning. An archive of genuine Microware 6809 source sits in the wider
project's resource collection and has never been opened for any purpose;
NitrOS-9's open kernel source is held to cross-check-only use and is never
extracted at length.

## Layout

```
os9-dev/
  SKILL.md              entry point
  SOURCES.md            which manuals stand behind which file
  references/
    CONFIDENCE-TAGS.md  the tag system above
    INDEX.md            topic -> file
    common/ 68k/ 6809/ basic09/ c/
os9-systems-dev/
  SKILL.md  SOURCES.md  references/
DIVERGENCES.md          where a runtime disagrees with a manual
SOURCE-AUTHORITY.md     what counts as Microware's word
```

**Shared content lives in `os9-dev`, which stands alone.** Anything both
skills need — the confidence tags, the provenance rules — belongs there.
`os9-systems-dev` may depend on `os9-dev` and cite its files by path;
`os9-dev` never depends on the sibling, and points at it only to mark
something as out of scope. Always name the skill when citing across the
split — a bare filename won't resolve from the other skill's directory.

The two root files are review material, not part of either installed skill;
nothing under `os9-dev/` or `os9-systems-dev/` may reference them.
