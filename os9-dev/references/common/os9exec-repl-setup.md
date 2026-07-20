# Bootstrapping an os9exec-style 68k REPL harness

For building your *own* text-driven harness against os9exec (or a fork/
variant of it) — not this repo's exact tooling specifically. Operating a
harness once it exists: `using-os9exec-repl.md`.

## Why 68k is simpler than 6809 here

os9exec **is** the CPU + OS-9 kernel — a software implementation, not a
hardware emulator running real firmware. No ROM, no separate machine
emulator, no video/keyboard console to bridge around. Its stdin/stdout
genuinely are the OS-9 console, so a plain PTY/pipe harness (tmux, `pexpect`,
raw `fork`+pty) works directly — contrast the 6809 side (`nitros9repl-setup.md`),
which needs an out-of-band serial bridge because XRoar's console is a GUI
window.

## Requirements

- **Build os9exec**: `make` (native macOS/Linux); Windows via
  `make OS=Windows_NT CC=x86_64-w64-mingw32-gcc` (genuine PE, no Wine).
- **A disk image** — host-native directory *or* RBF image, containing at
  minimum a bootable shell and `SYS/errmsg`. `OS9DISK=<path>` mounts the
  data disk; `OS9H0`…`OS9HZ` mount `/h0`…`/hz`.
  **Copyright wall, not a technical one**: genuine OS-9/68k binaries
  (Microware's shell, compilers, utilities) are proprietary. There is no
  free substitute to bundle — the caller must supply their own legally-held
  disk image or SDK. A host directory populated with your own files works
  identically to a real image for basic testing.
- **Boot invocation**: `OS9DISK=<path> ./os9exec [-r] shell <bootfile>` —
  `shell` is the boot *program*, `<bootfile>` is its argument (booting a
  startup file directly, without `shell` in front, fails `E_FNA`). `-r`
  disables baud-throttled output (full host speed; keep throttled only if
  a test genuinely depends on real-time pacing). `OS9STOP=1` in the host
  environment lets a `stop` typed inside OS-9 shut the emulator down
  cleanly — without it there's no graceful exit path from inside the guest.

## Harness shape

- **Gated send + raw-key fallback**, same pattern any OS-9 REPL needs:
  type command + Enter, wait for a recognized prompt regex, return only
  new output. The gate **goes silent inside any sub-program with its own
  prompt** (BASIC09 `B:`/`E:`, `debug`'s `dbg:`, `vi`) — switch to raw
  ungated keystrokes there, poll for the expected prompt to return.
- **Always `grep -a` captured output.** OS-9 programs emit raw control
  bytes; plain `grep` decides the stream is binary and silently replaces
  real output with `Binary file matches` — a failing program's error text
  vanishes and a batch run looks like it passed.
- Terminal wants **CR-only** line endings on input if bypassing a
  line-buffered pty layer.

## Gotchas inherent to os9exec/OS-9-68k (not this repo's scripts)

- **Never point `OS9DISK` at a path starting with `./`.** Every ordinary
  file open silently breaks while module loading still works — boot
  proceeds, the shell won't exec anything (`not accessible` even for
  absolute paths), and `SYS/errmsg` fails to open. Looks exactly like a
  missing C-library trap handler; rule out the leading `./` first. Bare or
  absolute paths both work.
- **Never boot straight into `login`** as the boot program — it prints its
  banner and exits the emulator with no error. Boot to `shell` or a tsmon
  chain instead; `login <user>` from an interactive shell works fine.
- **The `cio` trap handler divides the binary population.** Most archived
  OS-9/68k programs were linked against Microware's proprietary `cio`
  C-I/O trap handler and die immediately without it
  (`**** Can't install trap handler **** / **** cio ****`). Classify by
  searching binaries for the NUL-terminated module name `cio\0` (not a
  bare substring). A binary compiled with a public compiler (e.g. gcc2)
  plus a POSIX-wrapper header set needs no trap handler at all.
- **Fork-by-name resolves against `chx` (execution directory), not
  `PATH`.** `PATH` is purely the interactive shell's own search list — a
  program that `F$Fork`s a helper by bare name fails with a
  can't-find-current-directory-style error if `chx` isn't pointed at
  wherever that helper lives, even with a perfect `PATH`. A fresh
  account's `chx` should stay on the shared command directory; extend
  `PATH` for personal directories instead of moving `chx` there — moving
  it breaks *ordinary* interactive command lookup too, not just
  fork/compiler sub-tool resolution.
