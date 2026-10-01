# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/common/os9-tools-and-shell.md

---

# OS-9 Shell and Utilities

Shell syntax, line editing, terminal configuration, and the standard utility
set. Architecture-independent unless a row says otherwise - except the
utility catalog at the end, which is the 68k set with 6809 noted alongside.

## Shell model

- The shell is an ordinary unprivileged program, not part of the kernel.
  Multiple shells run concurrently; the default shell can be replaced (e.g.
  `MShell`).
- Each shell has private state: current directories (`chd`/`chx`), prompt,
  options. Child shells start with defaults - a child's changes never
  propagate back to the parent.
- The login shell executes `.login`/`.logout` in its own context, so their
  environment changes persist for that shell. Any shell forked afterward is
  a separate instance.

## Command line a