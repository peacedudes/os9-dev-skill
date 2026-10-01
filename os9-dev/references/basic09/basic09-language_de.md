# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/basic09/basic09-language.md

---

# BASIC09 Language Reference - shared, architecture-independent

Microware built BASIC09 as an interactive compiler with "the fast execution
speed typical of compiler languages plus the ease of use and memory space
efficiency typical of interpreter languages" (`Manual`, BASIC09 Reference
Manual Rev G, introduction; the 68k *OS-9 BASIC User Manual* says the same):
structured, typed, and compiled to I-code rather than interpreted line by line.

**This is the primary BASIC09 language reference.** BASIC09 is the same
language on 6809 and 68k OS-9 - same statements, same keywords, same
built-in functions, same control-flow constructs. Everything on this page
applies to both architectures identically. The only things that differ
between 6809 and 68k are numeric type widths/ranges/precision and a