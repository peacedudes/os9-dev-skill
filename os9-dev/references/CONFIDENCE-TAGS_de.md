# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/CONFIDENCE-TAGS.md

---

# Confidence tags

Shared by `os9-dev` and `os9-systems-dev`. Every factual claim in either
skill that isn't self-evidently a stable, published spec detail carries one
of these, inline, next to the claim it qualifies.

| Tag | Meaning |
|---|---|
| `Hearsay` | Stated directly by a person, not from any manual or test. **Lowest** confidence. |
| `Manual` | Derived from and cross-referenced across published manuals. Not run, not checked against code. |
| `Source` | Checked against real source code (os9exec's C, or NitrOS-9's open kernel source) - not run for this specific claim. |
| `Live` | Actually run and observed. **Always names where** - `Live` (NitrOS-9), `Live` (os9exec), `Live` (OS-9/68000). See below. |
| `Absent` | Actively searched for and confirmed **not to exist** - distinct from