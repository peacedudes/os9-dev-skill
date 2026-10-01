# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/basic09/pack-and-runb.md

---

# PACK and RunB: Packed BASIC09 Modules

How BASIC09 procedures become standalone OS-9 modules and how they resolve
at run time. The manuals are thin here; most facts below are `Live` (os9exec). Module-format background: `common/module-format.md`.

## PACK

**PACK is the last step of a build, not an editing operation** (`Hearsay` -
design intent; the manuals give the mechanics without the reason). It
compresses a finished procedure to minimal I-code for RunB - a stripped
BASIC09 with no editor or debugger - so that both the module and its
interpreter can live in ROM. Read the rest of this section against that: the
packed form is one-way because nothing downstream ever reads it back, and the
workspace copy is consumed because the copy you keep is the one you `SAVE`d.
Losing source to `PACK`