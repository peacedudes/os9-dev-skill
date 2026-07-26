# OS-9 Inter-Process Communication: Patterns and Gotchas

Mechanism-level call signatures (`F$Send`, `F$Icpt`, `F$Event`/`Ev$*`,
`F$DatMod`, etc.) are in `68k/syscall-reference.md`. This file is the practical
layer on top: how these mechanisms actually get used, and where they bite.

---

## Signals

One process can asynchronously interrupt another via signal — a narrow channel that flags
exceptional conditions or serves as a general-purpose notification when unmasked.

**Codes:**

| Code | Meaning | Interceptable? |
|---|---|---|
| 0 | Kill | No |
| 1 | Wake-up | No |
| 2–4 | Keyboard/modem (Ctrl-E abort, Ctrl-C interrupt, hangup) | Yes |
| 5–255 | Microware-reserved | Yes |
| 256+ | User-defined | Yes |

**68k-specific ceiling:** the `256+` user-defined tier assumes a 16-bit
signal code (68k passes it in `d1.w`). **6809 signal codes are 8-bit**
(carried in the `B` register — see
`6809/syscalls-and-module-format.md`'s Signals section) and top out at
255; there is no 6809 equivalent of the `256+` tier, and this table's
`5–255` boundary doesn't carry over unchanged either — 6809 sources
disagreed on paper about where the reserved/user-definable split starts
within 0–255 (4 vs. 128), but `Live` (NitrOS-9): a process installed an `F$Icpt`
handler, then `F$Send`'d itself code 50 (deep in the disputed range) and
code 200 (undisputed range); both delivered identically, the handler
received the correct code in `B` both times, with no rejection or special
handling for either. **The kernel does not enforce a reserved/user
boundary anywhere in 4–255 on delivery** — "reserved" is a Microware
naming/documentation convention only, not a behavioral one, on 6809.

A process with no intercept handler for a given signal is killed by it —
**except** for codes 0 and 1, which always act on their built-in meaning
regardless of handler state.

**Dispatch:** active processes run intercept routines immediately. Sleeping/waiting processes move to active queue, run the intercept, then resume the original wait via queued call.

**Delivery is queued, not dropped:** a signal sent to a process that already
has one pending is *not* discarded — signals queue and deliver in send
order. Queued delivery costs roughly **10x** more than unqueued delivery, so
a hot path that signals heavily should be aware it's paying for the queue.
The kernel also exposes an undocumented convenience here: on entry to an
intercept routine, **d0 holds the number of currently-queued signals**
(including the one just delivered) — a value of 1 means nothing else is
waiting, so a handler can drain the whole queue in one invocation instead of
re-entering per signal.

**Masking:** the mask level (`P$SigLvl` in the process descriptor) suppresses intercept calls while nonzero. `F$SigMask` with d1=1 increments, d1=-1 decrements, **d1=0 clears entirely**. Footgun: 0 "unmasks everything" inside nested code—nest with ±1 always. Overflow/underflow past 255/0 is silently ignored.

Entering an intercept routine auto-masks (sets `P$SigLvl` to 1). The
non-recursive (fast) path stores its one saved state in system state;
recursive intercept calls instead spill onto the user stack. Saved state
covers all MPU registers (72 bytes), or 168 bytes total if the FPU is
active.

**Mainline pattern:**
```
mask → do work → sleep (auto-unmasks) → service queued signals → repeat
```
`F$Sleep` auto-unmasking prevents deadlock — a process masked before sleeping would never wake to service the signal it's waiting for otherwise.

**Async safety inside a handler:** the intercept routine auto-masks on entry (not re-interruptible), so it must be short — no atomicity beyond single instructions. Keep mainline data safe:

1. Use algorithms with no shared mutable state.
2. Mask signals around mainline critical sections.
3. Use single-instruction atomic ops: `move`, `addq`, `subq`, `bset`, `bclr`, `tas`. 68k additionally has `cas` (atomic compare-and-swap, singly-linked) and `cas2` (doubly-linked).

**Send restrictions:** most signals can be sent to any process, but Kill is
restricted to same user/group — only the super-user (group 0) can Kill
across groups. Sending to PID 0 broadcasts to every process sharing the
sender's user/group, excluding the sender itself; `kill 0` at the shell uses
exactly this convention.

**Nesting-counter overflow (theoretical):** mixing `longjmp()` with an
`F$RTE` exit that skips `F$SigReset` can in principle overflow the signal
intercept nesting counter — but only after roughly 4 billion unmatched
calls, so this is a real but remote edge case, not a practical concern.

Ctrl-C delivers signal 3 (interrupt) and Ctrl-E signal 2 (abort) — the
inverse of Unix reflexes. Full control-key table and remapping:
`os9-tools-and-shell.md`; Unix-habit traps: `unix-differences.md`.

---

## Alarms

Two distinct flavors, not two configurations of the same thing:

| Flavor | Delivers | Constraints |
|---|---|---|
| User-state (`A$Set`, `A$Cycle`, `A$AtDate`, `A$AtJul`) | A signal to the requesting process | Normal process context |
| System-state | Runs a subroutine at kernel priority | Cannot sleep, wait, or fork; stack is biased into the system process descriptor (~1K of free space there) |

**Auto-cleanup gotcha:** the kernel auto-deletes a process's pending alarms
when that process exits — convenient in general, but wrong for a
*persistent* system-state alarm meant to outlive the process that set it
(e.g. a disk-motor shutdown timer). Workaround: make the `F$Alarm` call as
the **system process** itself, not the process that wants the timer.

**Patterns:**
- **Guard** — set an alarm before an otherwise-unbounded wait; it fires a
  timeout signal that breaks the wait. Classic pattern: arm an alarm, issue
  a blocking `I$Read`; if the alarm fires first, the read returns an error;
  if the read completes first, cancel the alarm.
- **Ticker** — multiple alarms at different intervals simulate thread-like
  concurrency inside a single process, each driving a different piece of
  work.

**Time-of-day sensitivity:** a time-of-day alarm is sensitive to clock
corrections — if the system clock is adjusted, the alarm fires at the
corrected time, not at the originally-scheduled offset. This means "alarm at
5:00" and "alarm in 1 hour" can diverge if the clock changes in between.

---

## Events (the one synchronization primitive)

OS-9's **event** is a counter that processes block on until it reaches a target value/range — one mechanism covering mutex, condition variable, and counting semaphore (a binary mutex is an event constrained to (1,1); a condition variable is wait/signal on an event). Unlike Unix/POSIX's three separate concepts, one API (`F$Event`) covers all three.

**Wait/Signal are atomic w.r.t. time-slicing** — this prevents races on guarded resources:
- *Wait* suspends until the event's value is within the target range, then adds a wait increment.
- *Signal* adds a signal increment and checks whether any waiter can now proceed.

Both operations live behind a single `F$Event` syscall specifically to
minimize the number of kernel calls a synchronization operation needs.
Example: modeling exclusive access to one resource with value=1, wait
increment=-1, signal increment=+1 — a plain binary semaphore, expressed as
an event.

**Readers/writers:** implemented by managing separate reader and writer
semaphores plus a control semaphore (three semaphores total) — allowing
multiple concurrent readers, or one exclusive writer, never both at once.

**ISR note:** since Wait/Signal are direct kernel primitives, signaling an
event from an interrupt handler to release a waiting process is a fast,
direct path — prefer it over routing the same wakeup through a signal when
you're in interrupt context and cycles matter.

**Relative-value variants:** `_os_ev_waitr()`/`_os_ev_setr()` behave like
`_os_ev_wait()`/`_os_ev_set()` but treat the min/max range and the returned
value as offsets from zero rather than absolute values — convenient for code
that thinks of an event as a signed delta rather than an absolute counter.

---

## Pipes

A pipe is a FIFO memory buffer where one writer's output becomes one reader's input. The Pipe File Manager (PIPEMAN) coordinates access via a null driver, buffer size overridable via the `S_ISIZE` option to `_os_create()`. **Default buffer size — an os9exec-vs-manual divergence:** the OS-9 manuals document a **90-byte** default (`Manual`, real PIPEMAN), but **os9exec's default is 4096 bytes** — `Source`: `DEFAULTPIPESZ 4096+SAFETY` in `os9exec_nt.h`, where 90 is os9exec's `MINPIPESZ` (its *minimum*, not its default). `Live` (os9exec): a C program writing 256-byte chunks to a pipe with no reader got exactly **16 chunks = 4096 bytes** accepted before the write failed. Since a C `write()` wraps `I$Write` roughly 1:1, that is the real buffer size and not a language-level batching artifact. On os9exec, don't assume the manual's 90 bytes; it uses 4096. (Real OS-9's own default may well be 90 — this is a clone divergence, neither an oracle.)

**Unnamed pipes** are created fresh by `I$Open` and shareable only across processes related by `F$Fork` inheritance — how the shell builds pipelines with `!`. Two unrelated processes each opening `/pipe` get two separate, unconnected pipes.

**Named pipes** (`/pipe/<name>`) are file-based, allowing unrelated processes to connect: `I$Open` searches a linked list for that name and returns the *existing* path (like `I$Dup`) if found. A named pipe persists while open, making it useful for temporary-data handoffs between unrelated processes.

**Shell-style construction:** the shell builds a pipeline with `F$Fork`,
giving each child redirected stdin/stdout and closing the unused ends to
establish one-directional flow between them.

**Close behavior differs by kind:**

| Pipe kind | On close |
|---|---|
| Unnamed | Path count decrements; at 0 paths, memory returns to the system |
| Named | Path count decrements; a non-empty named pipe stays open, waiting for a reader — memory returns only once it's empty |

**Blocking and deadlock:**
- Writing to a **full named pipe** blocks until space frees (unless the
  writer is interrupted by a signal). **`Live`** (os9exec): a C writer to a
  named pipe with no reader blocks once the ~4KB buffer fills; the block is
  interruptible by Ctrl-C/Ctrl-E (see `common/using-os9exec-repl.md`).
- For an **unnamed pipe**, a writer that fills the buffer with no reader
  attached gets **`E_WRITE`** rather than blocking. **`Source`+`Live`**
  (os9exec): `pipefiles.c` returns `E_WRITE` when the pipe is unnamed and its
  path count is below 2 (nobody else attached); confirmed live — a C writer to
  an unnamed pipe got `E_WRITE` after 4096 bytes. The stronger *cyclic*
  deadlock (several mutually-write-blocked processes sharing one unnamed pipe,
  all detected and one given `E_WRITE`) needs a multi-process setup and is
  still `Manual` — a dedicated follow-up.
- **Creating a named pipe that already exists:** the `FAM_NOCREATE` open flag
  makes this fail outright; without it, behavior is file-manager-dependent
  and may truncate the existing pipe — pass `FAM_NOCREATE` if you specifically
  need "fail, don't clobber" semantics.
- **`OPEN` on a not-yet-existing named pipe fails outright — `CREATE` is
  what actually establishes it.** `Live` (os9exec): a process `OPEN`ing a named pipe
  nobody has ever touched crashes uncaught with `Error #000:216 (E_PNNF)`
  the moment it's forked, not a clean error the program can catch. If a
  reader might run before any writer has created the pipe, it must
  `CREATE` (or otherwise ensure the pipe exists) rather than assume `OPEN`
  will find/make it.
- The shape that *isn't* automatically caught: a process holding the write
  end of one pipe while blocked reading from another, in a cycle with
  another process doing the reverse. Nothing in the pipe mechanism itself
  detects a cross-pipe cycle like this — avoid it by closing unused path
  ends promptly, or using non-blocking reads when a process legitimately
  juggles more than one pipe.

**EOF is "empty AND no other writers":** `I$Read`/`I$ReadLn` sleep if insufficient data is ready. EOF recognized only once the pipe is empty *and* reader count equals total user count. Partial reads before EOF return fewer bytes (not an error).

**Why pipes over signals:** longer messages (not capped at 16 bits), natural queuing, pending-data checks, and (named pipes) coordination between unrelated processes. Reader/writer can use different transfer sizes. Plain `Read`/`Write` faster than `ReadLn`/`WritLn` (no CR scan).

---

## Data modules (shared memory)

Created via `F$DatMod`; accessed by pointer or register-indirect addressing once linked (see `memory-and-io.md` for allocation mechanism). A data module is mutable, shared, *live* state — not code.

OS-9's shared-memory IPC mechanism for processes needing to see the same live data (vs. pipes which move data, or signals/events which coordinate timing without payload). Common pattern: data module holding shared state plus an event for coordination — usually paired, not separate.

---

## Record locking (RBF files — a fifth sync primitive, easy to miss)

Unlike everything above, this one needs **no call at all** to work. RBF
(the disk file manager) locks byte ranges on its own as a side effect of
ordinary `Read`/`Write` on a path opened for **update** (`r+`/`w+`-style,
not read-only or write-only): a `Read` locks the bytes it just returned;
the next `Write` on that path releases them. Anything else touching those
bytes meanwhile just blocks — same wait/wake plumbing as the rest of this
file, nothing new to learn there.

**Why it's worth knowing, not just trusting:** it's not only a safety net,
it's a design opportunity most programmers never exploited because it was
never explained well.
- **Lost-update races vanish for free.** Two processes each doing
  "read a record, modify it, write it back" on the same file cannot
  corrupt each other's update — the read's auto-lock plus the write's
  auto-release serializes them, with zero explicit locking calls. Design
  a shared data file as read-modify-write on purpose and you get real
  concurrency safety at no cost.
- **A plain growing file can behave like a persistent pipe.** A write
  landing at current EOF takes the **EOF lock** — a "ghost lock" placed
  where no data exists yet, not a lock on the file's actual content, which
  stays fully readable throughout. Its only job is to stop a reader from
  mistaking "caught up to the current end" for "the writer is done": it
  hits the ghost and waits right at the edge instead of reading past what's
  really there. Unlike a real pipe the data also survives after both
  processes exit — useful for a slow producer/consumer pair (e.g. a
  spooler) that wants that.

One easy trap: only **update-mode** opens ever lock or wait on anything —
read-only and write-only paths are both invisible to the mechanism. This
is deliberate, not an oversight: a write-only appender takes *no* lock,
specifically so two independent processes can log to the same file and
interleave freely. If either opened for update instead, its first write
would EOF-lock the file and the other process's next write would block
until the first one closed — exactly the mutual exclusion this design
avoids between plain appenders.

Explicit control exists too (`SS_Lock` to lock/release a range by hand,
`SS_Ticks` to bound how long to wait for a conflicting lock) but is rarely
needed — the automatic behavior above covers most real designs. **Deep
mechanics, exact byte-range rules, and the assembly-level implementation**:
sibling skill `os9-systems-dev`, `file-managers.md` → Record Locking.

## Reentrancy note for C programs using any of the above

Microware C generates reentrant code by default, with one exception: **system-state code (drivers, file managers)** must avoid globals/statics and stdlib calls (no per-process isolation at that privilege level). Use parameters or path-descriptor storage instead.

---

Sources: OS-9 Insights (edition 3), cross-checked against the OS-9 v2.4
Technical Reference Manual's IPC chapter for exact signal-code values and
alarm semantics; `_os_ev_waitr`/`_os_ev_setr` and `FAM_NOCREATE` from
Microware Training & Education seminar manuals.
