# OS-9 development skills

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

Nothing else to build. `tools/` holds a consistency checker used while
editing the docs; it isn't needed to use the skills.

## How this was assembled

OS-9's documentation was never centralized, and Microware is long gone. What
survives is scattered across preservation archives and hobbyist sites: manuals
in varying states of OCR, several editions of the same book that don't quite
agree, and files whose names lie about their contents. One manual circulating
in the 68k archives is actually a 6809 manual. Two files labelled `Gimix_*`
turn out to be a byte-identical duplicate and a second OCR pass of documents
already present under other names.

Some thirty of those published manuals, quick references and training guides
were read and cross-referenced against one another, and the findings condensed
into these files in their own words. No raw manual text is reproduced, no
worked code example is preserved verbatim, and no file mirrors any source's
chapter structure. `SOURCES.md` in each skill lists which manuals stand behind
which file. Where two manuals disagree, both readings are recorded and marked
`Flag` rather than silently resolved in favour of one.

That much is a literature review. The part that makes it worth trusting is
what came next: the claims were **run**. OS-9/68k under the
[os9exec](https://github.com/peacedudes/os9exec) emulator, OS-9/6809 as
NitrOS-9 under XRoar. Every factual claim carries an inline tag saying how
much weight it bears:

| Tag | Means |
|---|---|
| `Hearsay` | Someone said so. Lowest confidence; expect testing to overwrite it. |
| `Manual` | Cross-referenced across published manuals. Not run. |
| `Source` | Checked against real source code, but not run for this claim. |
| `Live` | Actually run and observed. |
| `Absent` | Searched for and confirmed not to exist — not merely unchecked. |
| `Flag` | Sources disagree; unresolved. |

Running things changed the picture more than once. Manuals turned out to be
wrong. So did the emulators — several bugs found this way were fixed upstream
rather than documented around. And so did earlier conclusions here: a pair of
confidently-written findings about signal handling were **retracted** after it
emerged that the tests behind them never exercised the mechanism they claimed
to. Those retractions are left in place, visible, instead of being quietly
deleted. A `Live` claim is only as good as the build it ran against, so each
one is dated and `CONFIDENCE-TAGS.md` stamps the exact emulator versions.

## What's solid, and what isn't

The 68000 material has been through a thorough live-verification pass and is
largely `Live`. **The 6809 material is mostly still `Manual`** — cross-checked
between manuals, but not yet run the same way. Both are useful; they are not
equally proven, and the tags will tell you which is which on any given line.
`os9-dev/references/VERIFICATION-BACKLOG.md` tracks what is still open.

Nothing here has been checked against real hardware. Everything `Live` is
emulated by necessity, and neither emulator is treated as an oracle — where
one disagrees with the documentation, that is recorded as a disagreement.

## Provenance

All source material is public-domain or freely-published Microware/Tandy
documentation, or historical-preservation archives. **No proprietary Microware
source code was used anywhere in this chain.** Material that was deliberately
*not* used is documented too, in `SOURCES.md`, along with the reasoning —
including one archive of genuine Microware source that has never been opened.

## Layout

```
os9-dev/
  SKILL.md              entry point
  SOURCES.md            which manuals stand behind which file
  references/
    CONFIDENCE-TAGS.md  the tag system above
    INDEX.md            topic -> file
    VERIFICATION-BACKLOG.md
    common/ 68k/ 6809/ basic09/ c/
os9-systems-dev/
  SKILL.md  SOURCES.md  references/
tools/
  check_doc_consistency.py   doc linter (stdlib only)
  tests/                     python3 -m unittest discover -s tools/tests
```

Run the checker over **both** skills at once — narrowing it to one root
reports the deliberate cross-skill references as broken:

```sh
python3 tools/check_doc_consistency.py
```
