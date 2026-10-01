# (DE) Übersetzung – automatische Platzhalter

Dies ist eine automatische Übersetzungsplatzhalter-Datei. Originalpfad: os9-dev-skill/os9-dev/references/68k/network-sockets.md

---

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
nothing of the kind. Where this file 