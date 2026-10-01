# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/INDEX.md

---

# Reference Index - read the matching row(s) before answering

Topic -> target -> file. Keywords are deliberately dense; scan for yours.

**Directory convention.** `common/` holds what applies to both targets - but
where a value differs, **68k is the default** and the 6809 delta is called
out inline or lives under `6809/`.

**So an unqualified value in `common/` is a promise that it holds on both
targets.** When writing here, either verify that or mark the scope inline -
an unmarked 68k-only fact is indistinguishable from a verified shared one,
and the reader has no way to tell which they are looking at. This is not
hypothetical: `common/` carried "super-user = group 0" bare in four places,
which is true on 68k and false on 6809 (flat user ID 0) - a privilege guard
written from the bare cl