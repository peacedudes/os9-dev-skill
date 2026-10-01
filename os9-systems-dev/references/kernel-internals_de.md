# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-systems-dev/references/kernel-internals.md

---

# OS-9 Kernel Internals

Baseline `Manual`, cross-referenced across multiple manuals.

**Authority ceiling on the Process Descriptor offsets.** The field *offsets*
here are not published in any authoritative Microware manual in this corpus:
the 68k manuals describe the process descriptor only in prose (state,
priority, paths, memory list), and the one `P$` offset table that exists - in
the 6809 *System Programmer's Manual* - is the 6809 descriptor, a different
and smaller layout. These offsets trace to the Guru book (Dayan;
third-party, so not Microware's word) as reflected in os9exec's
reconstructed `procid` struct, against which they are `Source`-confirmed
byte-for-byte. Microware manuals and the Guru corroborate the field *names
and semantics* (`P$SigLvl`, `P$Signal`, `P$State`), but th