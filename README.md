# OS-9 development skills

> **Pre-publication — not for distribution.** Circulated privately for review;
> no license is granted yet. See [LICENSE](LICENSE) for why, and
> [LICENSE.pending](LICENSE.pending) for the terms intended to replace it.
> [NOTICE](NOTICE) credits the sources and is in force regardless.

Two reference collections for working with Microware OS-9 — the real one, on
6809 and 68000. Plain Markdown: no build, no dependencies, no framework. Any
coding agent can use them by reading the files; [Claude
Code](https://claude.com/claude-code) can additionally load them as skills.

| Skill | Covers |
|---|---|
| **`os9-dev`** | Application work: BASIC09, Microware C, 68k and 6809 assembly, the shell and utilities, modules, syscalls, error codes, driving the emulators |
| **`os9-systems-dev`** | Below the application line: device drivers, file managers, kernel internals, the scheduler, 6809 Level 2 MMU/DAT |

They are siblings and cross-reference each other; keep both.

## Using it

Put the folder anywhere your agent can read files. There is nothing to build.

**Any agent** — point it at [`AGENTS.md`](AGENTS.md), which says what the two
collections cover and how to route within them. The material is written to be
**opened on demand rather than read whole**: together the files run to roughly
12,000 lines, which is worth keeping out of a context window until it is
needed. Each collection's `references/INDEX.md` maps *topic to file* and,
separately, *symptom to cause* — when something has already failed and you
don't know which topic owns it, the symptom table is the faster door.

**Claude Code**, additionally — expose the two directories as skills, so they
load themselves when a task matches:

```sh
ln -s "$PWD/os9-dev"         ~/.claude/skills/os9-dev
ln -s "$PWD/os9-systems-dev" ~/.claude/skills/os9-systems-dev
```

Copying in place of symlinking works equally well. That step is specific to one
runtime and is entirely optional — every other agent just reads the files. The
YAML header on the two `SKILL.md` files is metadata for that runtime; it is
harmless to ignore.

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
them is written here rather than borrowed: no manual text reproduced at
length, no worked code example kept verbatim, no file mirroring a source's
chapter structure. Short quotations do appear — a clause or a sentence, each
attributed to chapter and page — where the manual's exact wording *is* the
evidence: what it specifies on a disputed point, or one of its own errors
preserved so the citation can be checked.

What was deliberately *not* used is recorded too, in `SOURCES.md`, with the
reasoning. An archive of genuine Microware 6809 source sits in the wider
project's resource collection and has never been opened for any purpose;
NitrOS-9's open kernel source is held to cross-check-only use and is never
extracted at length.

## Working on this

Two gates must be green before anything lands, and a tracked pre-commit hook
enforces both:

```sh
git config core.hooksPath tools/hooks     # re-run this after every fresh clone
python3 tools/check_doc_consistency.py    # presence, hygiene, cross-file drift
python3 tools/tests/test_check.py         # the checker's own test suite
```

**The hook is tracked but the config that arms it is local**, so a fresh clone
has no hook until you run that first line. The checker enforces more than
presence: no calendar dates, commit hashes or host paths in reference files;
well-formed confidence tags, and none inside code fences; no blanket `Live` or
`Source` claim without a stated exception; every hex-dump decode-table claim
checked against the dump above it; cross-file enumeration drift; and any error
symbol absent from the error-code table.

Conventions worth knowing before editing a reference file:

- **Every claim carries a confidence tag**, and a `Live` tag always names the
  implementation it ran on — `Live` (os9exec), not a bare `Live`.
- **Reference files carry no dates, hashes, host paths or narrative** about
  their own history. A correction states the rule positively and puts its
  provenance in the tag and the `Sources` footer — never in a story about what
  the file used to say.
- **Cross-check before you correct.** Anything that looks like a contradiction
  gets checked against the skill's own `Live` claims, and against a manual or a
  running system, *before* an edit. Overwriting an established fact on one
  session's reading is this project's known regression pattern.
- **An example ships only if it was run.** An unrun example is `Manual` at
  best. Where something could not be run, say which claim went unchecked.
- **Shared content lives in `os9-dev`**, which stands alone (see Layout below).

`tools/make-bundle.sh` builds a distributable zip from `git archive HEAD`: only
committed files can appear, it refuses a dirty tree, it runs both gates first,
and it aborts if maintainer material reaches the staging tree.

## Layout

```
os9-dev/
  SKILL.md              entry point
  SOURCES.md            which manuals stand behind which file
  references/
    CONFIDENCE-TAGS.md  the tag system above
    INDEX.md            topic -> file, and symptom -> cause
    common/ 68k/ 6809/ basic09/ c/
os9-systems-dev/
  SKILL.md  SOURCES.md  references/
AGENTS.md               entry point for any agent
NOTICE                  attribution: Microware and every other source
DIVERGENCES.md          where a runtime disagrees with a manual
SOURCE-AUTHORITY.md     what counts as Microware's word
tools/                  the checker, its tests, the pre-commit hook, make-bundle.sh
```

**Shared content lives in `os9-dev`, which stands alone.** Anything both
skills need — the confidence tags, the provenance rules — belongs there.
`os9-systems-dev` may depend on `os9-dev` and cite its files by path;
`os9-dev` never depends on the sibling, and points at it only to mark
something as out of scope. Always name the skill when citing across the
split — a bare filename won't resolve from the other skill's directory.

`DIVERGENCES.md` and `SOURCE-AUTHORITY.md` are review material rather than part
of either collection; nothing under `os9-dev/` or `os9-systems-dev/` may
reference them, so that each collection stays self-contained wherever it is
installed.
