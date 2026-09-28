# OS-9 Mental Model

Modules, processes, I/O, and memory as one system. These concepts are
identical across 6809/68k/OS-9000; where a byte value or register is
architecture-specific it's marked inline. 68k values are the default here;
6809 byte layouts live in `6809/syscalls-and-module-format.md`.

## Modules: the unit of software is memory, not files

- Everything executable or data-bearing is a **module**: header (type,
  language, attributes, CRC) + body + trailing 24-bit CRC. Programs, device
  drivers, file managers, trap libraries, shared data — all modules.
- The kernel tracks resident modules by name in the **module directory**.
  "Loading" registers a module there; "running" forks a process from the
  registered copy. One resident copy serves every process running it.
- Header starts with a sync word — `$4AFC` on 68k (an illegal 68000
  instruction, so coldstart can cheaply scan ROM word-by-word for module
  boundaries); `$87,$CD` on 6809. 68k header is minimum 48 bytes; 6809's
  is 9 bytes. Full field layouts: `module-format.md`.
- **Position-independent and ROMable**: no absolute addresses; code uses
  PC-relative jumps and register-indirect data access. Load address is
  chosen at run time. Code can live in ROM; each process gets its own RAM
  data area — **reentrancy without an MMU**. Data modules are the
  deliberate exception (shared, mutable).

### Module directory lifecycle

Each entry: memory address, **link count**, group ID (modules loaded from
one file free together), parity. `F$Link` finds a resident module by name
and increments the count (no disk I/O); `F$Load` reads from disk when
absent, then links. `F$UnLink` decrements; at zero the module is freed
unless **sticky** (survives until an unlink drives the count to −1 or
memory pressure evicts it). Forking a program implicitly links it. Loading
a higher-revision module of the same name replaces the directory entry
immediately: running processes keep the old copy, new lookups get the new.

### Module types

The header type byte distinguishes program, subroutine, data, trap library,
system, file manager, device driver, device descriptor. The kernel checks
type before fork/link — forking a non-program returns an error. Every OS-9
capability is reachable both from the shell's utilities and directly via
system calls (`F$`/`I$`); the utilities are thin wrappers over the same
calls.

## The process model

- A **process** = shared program module + private data context (static
  storage, stack, parameter area), tracked by a kernel-owned process
  descriptor user code never touches.
- `F$Fork`: kernel locates/loads the module, allocates data memory sized
  from the module header (+ any extra requested), copies the module's
  data-initialization table in, patches position-dependent pointers, and
  returns the child PID. Child inherits current directories, environment,
  and open paths — never memory.
- **System state vs. user state**: kernel/supervisor mode (unrestricted,
  not time-sliced) vs. application mode (time-sliced). On 68k this maps to
  the CPU's own supervisor bit; a module's attribute byte declares which
  state it runs in.
- **Scheduler**: preemptive, priority + aging. Default timeslice 2 ticks
  (~20 ms). Aging is a single system-wide counter consumed at each process
  insertion, not a per-process wait-counter — a process queued earlier gets
  a more favorable scheduling constant than one queued later at the same
  priority, so low-priority work eventually runs. `D_MaxAge` is a priority
  threshold above which aging is switched off and that tier fully preempts
  everything below it while active. Full mechanism: `os9-systems-dev`
  skill's `kernel-internals.md`.

### Memory allocation facts that shape programs

- **Colored memory**: allocation can request a specific memory type (fast/
  slow/video/non-volatile RAM); uncolored requests get the highest-priority
  type available.
- **No MMU address translation** (on the classic line): a process's data
  area is one contiguous block; `F$Mem` expansion needs free memory
  immediately above it. Fragmentation is avoided, not repaired — drivers
  allocating at open time scatter allocations, so `iniz` devices early.
- Sticky ("ghost") modules save reload time but can be evicted when a
  large contiguous request needs the space.
- OS-9's small-footprint discipline (tiny headers, small default stacks, a
  lean C library) is inherited from 6809 Level 1's 64K world and never
  left; it's why OS-9 remained viable as an instant-on embedded/real-time
  OS (Microware still maintains it — microware.com). OS-9 v2.4 is the
  direct basis of CD-RTOS, the OS inside Philips CD-i players; this skill's
  sources establish that equivalence but contain no CD-i-specific disc
  format or driver API detail.

## Two current directories, not one

| | Command | Used for |
|---|---|---|
| **Data directory** | `chd` | Relative *data-file* paths; procedure-file lookup |
| **Execution directory** | `chx` | Relative *module/command* names when running something |

The single underlying rule: **an execute-mode open resolves against `chx`;
every other open resolves against `chd`.** A command search checks the
module directory (already resident?), then `chx`, then each `PATH` entry,
then the data directory (as a procedure file) — `Manual` (Microware's *OS-9
Advanced* training manual). `chd` alone never makes a program findable.
Prefer `PATH` over moving `chx`; `chx` matters when a tool forks co-located
sub-tools by bare name (compiler drivers do — see `c/os9-c-cheatsheet.md`).

A consequence of that last step, easy to miss: a file found and run this way
has **all** its modules loaded and the **first** one executed, so the name of
the file need not be the name of the module that actually runs — `Manual` (the
*OS-9 Intermediate* training manual). `mdir` is what tells you which name
became resident; `module-format.md` covers the ways a file name and a module
name come apart.

## I/O architecture: one path API, layered modules

Devices and files share one namespace and one API: `I$Open` returns a
**path number** (OS-9's file descriptor), then `I$Read`/`I$Write`/`I$Seek`/
`I$GetStt` behave identically whether the target is a disk file, terminal,
pipe, or tape. Swapping a file for a device is path redirection, not a code
change.

An I/O request flows **kernel → file manager → device driver**, with
**device descriptors** supplying per-device configuration:

| Module | Role |
|---|---|
| File manager | Logic for a whole device *class*, hardware-independent |
| Device driver | Register-level control of one hardware controller; no idea why bytes move |
| Device descriptor | Small data-only module naming a logical device (`/d0`, `/term`), its file manager, its driver, and hardware config (port address, IRQ, options) |

Descriptors are cheap tables: one driver serves many logical devices, one
physical port can carry several descriptors (e.g. terminal-mode and
printer-mode names for the same serial port). All three layers load/unload
at runtime — adding an interface never needs a reboot. (Microware docs
count "four levels" by including the kernel + its INIT/clock modules as
level one.)

Standard file managers:

| File manager | Device class |
|---|---|
| **RBF** | Random-access block devices — disks: hierarchical directories, segment allocation, record locking |
| **SCF** | Sequential character devices — terminals, printers, serial ports: line editing, echo, flow control |
| **SBF** | Sequential block devices — **tape drives**: block-oriented but non-random access |
| **PIPEMAN** | Pipes: FIFO buffer coordination between processes |

Line-oriented I/O (`I$ReadLn`/`I$WritLn`, CR-terminated records) is part of
the common path API, not a property of one file manager — it works on RBF
files, SCF terminals, and pipes alike.

## Conventions that bite

- **Big-endian**: 68k stores multi-byte values MSB first; parsing OS-9
  structures on a little-endian host requires byte swapping. (6809 also
  stores multi-byte values MSB-first.)
- **Text lines end in CR (0x0D), not LF** — family-wide. OS-9 C's `\n`
  compiles to CR (`\e` gives a true LF). RBF stores exactly the bytes
  written, no translation; SCF may append LF after CR on output as a
  terminal nicety, but never rely on translation for files.

## Why it matters — one-line index

| Concept | Consequence |
|---|---|
| Modules, not files | Dynamic loading, ROM placement, reentrancy without MMU |
| Link counts | One resident copy per program, dynamic-linker-style lifecycle |
| File manager / driver / descriptor split | New hardware = small driver + tiny descriptor, no kernel change |
| Path numbers | Disk, terminal, pipe, tape behind one I/O interface |
| Priority + aging | Preemption without starvation |
| Two current directories | Data lookup and command lookup are different searches |

---
Sources: OS-9 v2.4 Technical Reference Manual; Technical I/O Manual v2.4;
Disk File Organization manual; The OS-9 Guru; The OS-9 Primer; Using
Professional OS-9 v2.4; OS-9 Insights; a 1985 independent OS-9/68000
technical manual; OS-9 C Compiler manual. Module-header offsets and the
M$Attr bit layout are `Live` (os9exec) against a real compiled 68k module.
