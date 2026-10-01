# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/6809/gfx-windowing.md

---

# 6809 BASIC09 Graphics: GFX and GFX2

Reference for BASIC09's two CoCo/Dragon graphics subroutine packages, invoked
via `RUN GFX(...)` / `RUN GFX2(...)`: `GFX` is the Level 1 low-resolution VDG
package, `GFX2` is the Level 2 high-resolution graphics/windowing package.
Built from the Level 2 Operating System Manual's GFX/GFX2 chapter and
cross-checked against an independent second OCR of the same appendix
reprinted in the Tandy BASIC09 Reference Manual. Both sources are
OCR-scanned and locally dirty - curly quotes, `l`/`1`/`I`, and `O`/`0`
routinely garble, and the module name itself is misOCR'd in most of the
Tandy source's worked examples (`GEX2`, `GEN2`, `GEXA`, etc.). Where the two
sources agreed it's `Manual`; disagreements are tagged `Manual, Flag` inline
rather than silently picked.