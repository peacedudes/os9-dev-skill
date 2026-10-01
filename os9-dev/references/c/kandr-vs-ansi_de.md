# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/c/kandr-vs-ansi.md

---

# K&R vs ANSI C: OS-9 Microware Compiler

The Microware OS-9 C compiler is a **K&R-era implementation**. Modern ANSI C
will often fail to compile. Most of these are just "this is K&R C" facts -
the two that actually bite in practice (and are specific to this compiler, not
general K&R background) are the function-definition syntax you need to write
anything at all, and the `\n` escape sequence, which is called out
separately below.

**Provenance note:** rows marked *(6809 manual)* below are `Manual`,
sourced from the 1983 6809 C Compiler manual's own "Differences From The
K & R Specification" section and not independently re-confirmed against a
68k Ultra C toolchain - treat them as "this is what the 6809-vintage
compiler did," not as a guaranteed 68k fact, unless another row or
`os9-c-cheat