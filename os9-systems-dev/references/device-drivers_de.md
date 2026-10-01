# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-systems-dev/references/device-drivers.md

---

# OS-9 Device Drivers

Baseline `Manual`, cross-referenced across multiple manuals. The Device
Descriptor field table is verified against the OS-9 Technical I/O Manual (§1,
device-descriptor module figure), which lists every field at exactly these
offsets - `M$Port` $30, `M$Vector` $34, `M$IRQLvl` $35, `M$Prior` $36,
`M$Mode` $37, `M$FMgr` $38, `M$PDev` $3A, `M$DevCon` $3C, `M$Opt` $46
(initialization-table size), `M$DTyp` $48 (device type, first field of the
init table) - and os9exec's device-descriptor structure agrees field for
field.

**The entry-point register conventions below are `Manual`**, short of real
hardware: os9exec, the 68k runtime available here, never runs an installed
driver's code (`os9-dev`'s `common/using-os9exec-repl.md`, "What os9exec
does not implement"), so they co