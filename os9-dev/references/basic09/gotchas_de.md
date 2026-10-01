# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/basic09/gotchas.md

---

# BASIC09 Gotchas - all targets unless noted

A digest of the traps, one to three lines each, with a pointer to the full
treatment. Nothing here is the only statement of a fact except where a bullet
carries its own detail.

## Porting between targets

Full per-target detail: `basic09-per-target.md`.

- **INTEGER overflow wraps silently** at each target's width, no error, no
  warning. The wrap *mechanism* is identical across targets, so porting code
  that relies on the *width* breaks without any visible symptom - the #1
  silent-bug source here.
- **Hex constants change sign meaning across targets.** 6809 `$8000`-`$FFFF`
  are negative (16-bit); the same literal on 68k is a large positive 32-bit
  value. Never compare one across the boundary without an explicit cast.
- **REAL precision di