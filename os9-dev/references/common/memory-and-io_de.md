# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/memory-and-io.md

---

# OS-9 Memory Model and I/O Architecture

Memory allocation/layout, then the mechanics of the file-manager/driver/
descriptor architecture (concept-level overview: `os9-mental-model.md`).
Disk-block-level RBF detail (identification sector, file-descriptor
fields, directory format, record locking) is in the sibling
`os9-systems-dev` skill's `file-managers.md`.

---

## Memory model

### Allocation units and block sizing

OS-9 allocates in multiples of a **16-byte minimum allocation unit** - the smallest independently-freeable chunk tracked by free-list bookkeeping. This is a logical granularity; actual physical allocation depends on memory protection:

| System type | Minimum allocatable block |
|---|---|
| MMU-equipped (memory protection) | Matches the MMU page size (e.g. 4K) - kernel allo