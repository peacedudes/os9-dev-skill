# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/error-codes.md

---

# OS-9 Error Codes Reference

## Overview

OS-9 error reporting follows a standard convention.

### Error format: "Error #NNN:MMM"

Errors are reported as **Error #NNN:MMM** where:
- **NNN** is the class/module number (000 for kernel/core errors)
- **MMM** is the specific error code within that class

Example: `Error #000:216 (E_PNNF)` is class 000, code 216, symbolic name
`E$PNNF` (Path Name Not Found).

**The same error has two spellings, and only one of them is printed.** Source
and `DEFS` files declare `E$PNNF`; the runtime prints `E_PNNF` - `Live`
(os9exec), seen for `E_PNNF`, `E_CEF` and `E_DNE`. The tables below use the
`E$` form throughout, so searching for a name exactly as the machine printed it
will miss every row: substitute `$` for `_` before looking it up.

### Return convent