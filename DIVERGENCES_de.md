# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/DIVERGENCES.md

---

# Divergences from Microware documentation

Places where observed OS-9 behaviour, or our own documentation, disagrees with
or isn't covered by Microware's published manuals. The manual is the
specification; each item is a question for Microware to settle.

## Behaviour vs. the manual

- **BOOLEAN prints `True`/`False`, not the documented `TRUE`/`FALSE`.** Both
  BASIC09 manuals (Rev H, and Tandy 1983) specify uppercase; a genuine Microware
  6809 BASIC09 v01.01.00 module prints mixed case. (Checked via
  `PRINT USING "B"`.) **The module was Microware's; the machine was not** - this
  was observed under emulation, and which runtime is not recorded here. Of every
  item on this page it is the cheapest to re-test on a real 6809, and doing so is
  exactly the contribution `CONTRIBUTING.md` ask