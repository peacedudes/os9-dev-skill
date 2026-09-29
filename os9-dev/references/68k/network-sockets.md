# OS-9/Internet: Networking and Socket Programming

**`Manual` throughout - no call in this file has been run from C.** The
network itself works: `Live` (os9exec), the SDK's own prebuilt `tcprecv` and
`tcpsend` moved a file over `127.0.0.1` byte-identical, and the disk carries
`ftp`, `telnet`, `inetd` and their daemons. What is out of reach is *linking*
the API: a C program calling `socket()` fails at link time (full detail in
the sources note at the end). Treat every signature, return value and error
code below as unverified.

**The BSD resemblance is the trap.** This API is a deliberate *subset* of BSD
sockets, so anything familiar-looking invites filling the gaps from general
Linux/BSD knowledge - and that inference will read as confirmed when it is
nothing of the kind. Where this file is silent, the silence is a gap in the
documentation, not permission to assume the BSD behaviour. When answering from
this file, say which calls it actually documents and which you are inferring.

OS-9/Internet is Microware's TCP/IP stack - a BSD-flavored sockets API layered
on OS-9's own module/driver architecture, not a bolt-on. This file assumes
general TCP/IP and BSD sockets knowledge; it covers only what's specific to
this implementation: the module architecture, the actual supported API
surface (a deliberate subset of BSD), the config-file/compiled-database
system, and the admin/diagnostic tooling.

**68000-only, no 6809 support.** OS-9/Internet is a separate, later add-on
product, not part of the base OS-9 kernel - this file documents version 1.4
(Microware, July 1992, Product Number INT-68-NA-68-MO - the "68" in the part
number is the product line, not a version digit), which requires OS-9/68000
v2.3 or later. The source manual never mentions the 6809 anywhere and its
own product number identifies it as 68K-specific; there's no evidence a 6809
port ever existed.

---

## System architecture

The stack is built from cooperating OS-9 modules, not a monolithic kernel
subsystem:

| Module | Role |
|---|---|
| **SOCKMAN** | Socket manager - the only thing user programs talk to (via `socklib.l`). Dispatches calls into the protocol modules and exposes a standard calling interface plus timer services, so a new protocol module can be added later without touching SOCKMAN or the existing ones. |
| **TCP / UDP / IP** | Each a separate subroutine module. SOCKMAN binds to and calls them on the program's behalf. |
| **IFMAN** | Interface manager. Unlike a normal OS-9 file manager, IFMAN is *passive* - it only holds per-interface configuration data; it has no active I/O path. Protocol modules call the device drivers directly, using IFMAN's data to know how. |
| **Device drivers** | One per NIC (`le0`, `le1`, `ENP0`, ...) - ordinary OS-9 drivers at the bottom of the stack. |

Call path: **user program -> SOCKMAN -> TCP/UDP/IP protocol module -> IFMAN
(lookup only) -> device driver -> hardware.**

**Memory:** the stack uses its own allocator (`mbuf`), not general kernel
memory. IFMAN/SOCKMAN carve one contiguous block out of the kernel at startup
via `mbinstall`, then satisfy every further Internet-related allocation from
that pool - faster, and keeps network traffic from competing with
application memory.

**Supported subset:** `AF_INET` only (no other BSD address families);
`SOCK_STREAM` (TCP) and `SOCK_DGRAM` (UDP) only. Non-blocking I/O and
out-of-band data are not fully supported in this version. There is no
`select()` - `_ss_sevent()` is the OS-9 replacement, letting a process wait
on multiple socket paths at once (BSD `select()` was judged impractical to
implement directly on OS-9).

---

## Socket structures

Defined in `in.h` / `netdb.h`:

| Structure | Fields | Returned by |
|---|---|---|
| `sockaddr_in` | `sin_family` (=`AF_INET`), `sin_port`, `sin_addr` (an `in_addr`), `sin_zero[8]` (padding) | - (constructed by caller) |
| `in_addr` | `s_addr` (32-bit address, network byte order) | - |
| `hostent` | `h_name`, `h_aliases`, `h_addrtype`, `h_length`, `h_addr` | `gethostby*()`, `gethostent()` |
| `servent` | `s_name`, `s_aliases`, `s_port` (network order), `s_proto` | `getservby*()`, `getservent()` |
| `protoent` | `p_name`, `p_aliases`, `p_proto` | `getprotoby*()`, `getprotoent()` |
| `netent` | not confirmed in source (functions exist; exact field list inferred by analogy to `hostent`, not attested) | `getnetby*()`, `getnetent()` |

**Every lookup function's return value points into static storage that the
next call overwrites** - copy anything you need to keep before calling again.

---

## Socket API - behavior deltas from stock BSD

Function names and general semantics match BSD; only the OS-9-specific
behavior is worth calling out:

| Call | OS-9-specific behavior |
|---|---|
| `socket()` | Standard `AF_INET`/`SOCK_STREAM`/`SOCK_DGRAM` creation; returns a path number. Full error/signature detail unverified. |
| `bind()` | Wildcard (all-zero) address binds to any local interface. Binding port 0 or another invalid combination returns `EADDRINUSE`. |
| `listen()` | `SOCK_STREAM` only - `SOCK_DGRAM` gets `EOPNOTSUPP`. Requires a prior `bind()`; calling on an unbound socket returns `E_ILLFNC` (an OS-9 code, not a BSD one). Full pending-connection queue returns `ECONNREFUSED` to the connecting client. |
| `connect()` | Standard TCP connect; 0/-1 return. |
| `accept()` | Returns a new path number for the accepted connection; original listening socket keeps listening. |
| `read()`/`write()` | Work directly on `SOCK_STREAM` paths - byte count is a maximum, not a minimum (short reads return immediately with whatever's available). This is the BSD/Unix convention, and a deliberate departure from ordinary OS-9 file I/O semantics. `readln()`/`writeln()` are **not** supported on sockets. |
| `recv()` | Blocks unless the path is non-blocking (`EWOULDBLOCK` then). Requires a connected path - `ENOTCONN` if not connected, `E_BMODE` (OS-9 code) if not even bound. Returns actual byte count, not padded to the buffer size. |
| `recvfrom()` | Like `recv()` but works on an unconnected/datagram path and can report the sender's address. |
| `send()` | Requires a connected path. Blocks if the send buffer is full (`EWOULDBLOCK` if non-blocking - wait on buffer space via `_ss_sevent()`). A message too large for one atomic transmission returns `EMSGSIZE` and sends nothing. |
| `sendto()` | Like `send()` but takes an explicit destination and works on unconnected/datagram paths. |
| `shutdown()` | Closes one direction of a full-duplex connection; the other keeps working. A path shut down for reading returns `ESHUTDOWN` from further `recv`/`recvfrom`. Full parameter detail unverified. |
| `getsockname()` / `getpeername()` | Standard local/remote address retrieval; caller pre-sets the buffer-length field, gets the actual size back. |
| `getsockopt()` / `setsockopt()` | `SOL_SOCKET`-level and per-protocol options; unknown/unsupported option returns `ENOPROTOOPT`. |

**Errors beyond BSD `errno`:** calls can also return ordinary OS-9 errors
(`E_PERMIT`, `E_PTHFUL`, `E_MEMFUL`, etc.) alongside the BSD-style codes
above - the manual only calls out the "interesting" ones per function, not
an exhaustive list.

### Byte-order and address conversion

`htonl()`/`ntohl()`/`htons()`/`ntohs()` exist for portability but are defined
as no-op macros on a big-endian target like the 68000 - host and network
byte order are already the same, so there's nothing to swap.

| Function | Direction |
|---|---|
| `inet_addr()` | dot-notation string -> 32-bit address (network order); -1 on malformed input |
| `inet_ntoa()` | `in_addr` -> dot-notation string (static storage, overwritten each call) |
| `inet_network()` | dot-notation string -> network number only (not a full host address) |
| `inet_netof()` / `inet_lnaof()` | split an `in_addr` into network-number / local-host-number parts |
| `inet_makeaddr()` | inverse of the split above - network number + host number -> `in_addr` |

`inet_addr()`'s numeric parsing follows C literal conventions: no prefix is
decimal, a leading `0` is octal, `0x`/`0X` is hex - worth knowing since a
config value like `010.0.0.1` doesn't mean what it looks like.

### Database lookup functions

`gethostby{name,addr}()`, `getservby{name,port}()`, `getnetby{name,addr}()`,
`getprotoby{name,number}()`, plus a `get*ent()`/`set*ent()`/`end*ent()` family
for each (enumerate-all / reset-to-start / explicitly unlink). All of them
query the **compiled `inetdb` module**, never the text config files directly
(see below) - and all implicitly link the calling process to `inetdb` on
first use, so an explicit `link()` isn't required; only the `set*ent()` and
`end*ent()` calls manage linkage explicitly.

---

## Configuration files and `inetdb`

Four plain-text config files, all sharing one parsing convention (fields
separated by any run of whitespace/tabs, `#` starts a trailing comment):

| File | Per-line fields |
|---|---|
| `hosts` | address, official hostname, aliases, comment |
| `networks` | official network name, network number, aliases, comment |
| `protocols` | official protocol name, protocol number, aliases, comment |
| `services` | official service name, `port/proto` (e.g. `ftp 21/tcp`), aliases, comment |

These text files are **not** read at runtime. `idbgen` compiles all four into
a single data module, `inetdb`, and every lookup function above queries that
module instead - which is what lets a diskless/ROM-booted system have a full
network configuration with no filesystem at all. Any edit to the text files
requires re-running `idbgen` and reloading `inetdb` to take effect.

---

## Network installation and administration

- **`ifgen`** generates a device descriptor from a template `if_devices`
  file - the admin edits `if_devices` with the interface's Internet address,
  broadcast address, and hardware parameters, and `ifgen` produces the actual
  descriptor module.
- **`ipconfig`** is a compiled data module holding static IP routing: a
  gateway flag (set = this host routes/forwards; clear = ordinary host), a
  host-routes table, and a network-routes table (each null-entry-terminated).
  Loaded by the IP module at startup to seed initial routing.
- **`routed`**, once running, listens for routing broadcasts from other
  `routed` instances and updates the live routing table dynamically -
  static `ipconfig` entries matter less once it's up. **`ispstart`** is a
  lighter alternative that just opens a socket and initializes the stack,
  for setups that don't want a full `routed`.
- **`mbinstall`** carves out the `mbuf` pool from kernel memory (reducing
  free RAM accordingly) and must run before any other Internet utility.
- **Broadcast address** convention: the host portion of the interface's
  address set to all-ones (by convention, `.255`).
- **Ethernet hardware address storage** is board-specific and lives in
  battery-backed RAM: VME/147 at `0xFFFE0778`, VME/167 at `0xFFFC1F2C` - both
  formatted as 3 Motorola vendor-ID bytes (`08 00 3E`) followed by a 3-byte
  board serial number (matching the label on the CPU board).

### Ethernet driver diagnostics

- **`lestat`** - stats for the AM7990 LANCE driver: interface state, address,
  tx/rx counters, CRC/collision/overflow/framing error counts.
- **`iestat`** - richer stats for the Intel i82596 driver (VME/167), plus
  chip-specific queue-state and timing info. Two throttle parameters, `t_on`/
  `t_off` (bus-hold/bus-release time in µs × CPU MHz), stop the chip from
  monopolizing the bus.
  - Non-zero **`rmiss`** = the chip dropped incoming packets because the receive
    queue was full - the CPU isn't draining it fast enough; raise `max_rfd`
    in the driver descriptor.
  - Non-zero **`dropped`** = outgoing packets the driver queued but the chip's
    command queue was full for - raise `max_cbl`.
  - Non-zero **`lcol`**/**`lcar`** (late collision / lost carrier) point at a bad
    transceiver cable; non-zero **`babl`** (babble) points at a bad Ethernet
    cable or terminator.

---

## `ftp` utility

- Invoked as `ftp [hostname] [options]` - with a hostname it connects
  immediately; without one it drops into an interactive prompt where `open
  hostname` connects later.
- Transfer parameters: **Mode** (only `stream` is implemented), **Type**
  (`ascii` or `binary`), **Form** (only `non-print`), **Structure** (only
  `file`) - all fixed except Type, unlike full BSD `ftp`'s wider option set.
- Session toggles: verbose responses, completion bell, per-file confirm
  prompt (batch transfers), remote wildcard globbing, hash-mark progress
  output, active vs. passive (`PORT`) mode.
- A local filename argument starting with `!` is instead run as a shell
  command, with `ftp` reading/writing its stdin/stdout. Remote filenames are
  glob-expanded only for `mget`/`mput`/`mdelete`/`mdir`/`mls` - using the
  *remote* server's own expansion rules, not the client's.

---

Sources: OS-9 Internet Software Reference Manual. `Manual` throughout -
no call run from C. `Live` (os9exec): a C program calling `socket()` fails at
*link* time (`Symbol 'socket' unresolved`, `l68: error`) with `cc`'s default
libraries, and still does with `LIB/net.l` or `LIB/unet.l` added. The SDK
disk does carry `LIB/socket.l` and three `netdb*.l` libraries, but they do
not begin with a ROF's `$DEADFACE` sync word (`socket.l` starts `2D00 D5BC`),
and `l68` rejects them: `file '/dd/LIB/socket.l' is not a relocatable
module`. Which linker reads that format is not established here. Error-handling conventions cross-referenced
against `68k/syscall-reference.md` and `common/ipc.md`.
