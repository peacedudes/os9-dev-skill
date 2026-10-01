# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/tools/DESIGN.md

---

# Skill-doc consistency checker - design

Covers both skills, os9-dev and os9-systems-dev. Entry:
`check_doc_consistency.py`. Run from the repo root:

```
python3 tools/check_doc_consistency.py            # scan both skills' references/
python3 tools/check_doc_consistency.py <dir>...   # scan given roots
python3 tools/check_doc_consistency.py --memory-dir <dir>  # + orphaned [[memory]] links
python3 -m unittest discover -s tools/tests       # the test suite (stdlib, no pytest)
```

**Scan both skills together, or cross-references false-positive.** The two
skills point at each other's files on purpose (os9-dev's INDEX.md cites
`6809-level2-mmu.md`, which lives in os9-systems-dev - a scope marker, not a
dependency; shared content lives in os9-dev, see README). Narrowing a run to one
root - `