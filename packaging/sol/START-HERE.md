# Start here

Two reference collections for Microware OS-9 — the real one, on 6809 and
68000. Plain Markdown, no build, no dependencies, no framework. Any coding
agent can use them by reading the files.

## Using them with an agent

There is nothing to install. Put this folder somewhere your agent can read,
and tell it to start from `AGENTS.md`.

The material is written to be **opened on demand rather than read whole** —
together the files run to roughly 12,000 lines, which is worth keeping out of
a context window until it is needed. The routing is:

1. `AGENTS.md` — what the two collections cover, and which to use.
2. `os9-dev/SKILL.md` or `os9-systems-dev/SKILL.md` — the entry point for
   each. (The YAML header on those two files is metadata for one particular
   agent runtime; it is harmless to ignore.)
3. `references/INDEX.md` in each collection — the router. It maps **topic to
   file** and, separately, **symptom to cause**: when something has already
   failed and you don't know which topic owns the failure, the symptom table
   is the faster door.

## Every claim is tagged

`Hearsay`, `Manual`, `Source`, `Live`, `Absent`, `Flag` — defined in
`os9-dev/references/CONFIDENCE-TAGS.md`, which governs both collections.

The one that matters most: **`Live` means it was actually run and observed, and
it is evidence about the implementation that ran it, never proof about OS-9
itself.** Where a runtime and a Microware manual disagree, these files treat
the manual as the specification and the runtime as the candidate defect, and
record both readings rather than resolving in favour of whichever one happened
to execute. Tags name their implementation: `Live` (NitrOS-9) and `Live`
(os9exec) are different kinds of evidence and are never merged.

## If you work on NitrOS-9

Roughly 180 claims here are tagged `Live` (NitrOS-9) — observations from real
NitrOS-9 running under XRoar, over a DriveWire/becker-port channel, rather than
from an emulated 68k system. They are concentrated in:

| File | What was exercised |
|---|---|
| `os9-dev/references/6809/syscalls-and-module-format.md` | the largest group by far — roughly 70 of the ~93 documented syscalls, run and observed |
| `os9-dev/references/6809/assembly-and-tools.md` | the assembler and debugger core |
| `os9-dev/references/6809/gfx-windowing.md` | most GFX2 calling sequences |
| `os9-dev/references/6809/using-nitros9-repl.md` | driving the live system: the terminal channel, key codes, `tmode` |
| `os9-dev/references/6809/utility-usage.md` | per-command syntax, including where Level 1 and Level 2 differ |

Because NitrOS-9 is a reimplementation, a `Live` (NitrOS-9) line is a record of
what NitrOS-9 did — which is occasionally a place where it and a Microware
manual do not agree. Those are marked where they were noticed, and are offered
as observations rather than as bug reports; nothing here was checked against
real Microware hardware.

`DIVERGENCES.md` collects the separate case of documentation disagreeing with
itself or with observed behaviour. It is written as a list of questions for
Microware to settle, not as findings.

## Status

Pre-publication and circulated privately for review — see `LICENSE`. No
license is granted yet, and it should not be redistributed or posted publicly
while that notice stands.
