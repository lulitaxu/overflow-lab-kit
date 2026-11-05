# Lab targets

Three intentionally vulnerable C programs to practice against. They are
deliberately unsafe; that is their only job. Build and run them only in
your own lab (VM, container, throwaway machine). vuln3 binds a TCP port:
keep it on a lab network / localhost-only setup.

## The targets

| Binary | Source | Bug | Input channel | Stack buffer |
|---|---|---|---|---|
| `vuln1` | `vuln1.c` | `gets()` with no bounds check | stdin (one line) | 256 bytes |
| `vuln2` | `vuln2.c` | `strcpy()` of `argv[1]` | command-line argument | 128 bytes |
| `vuln3` | `vuln3.c` | `strcpy()` after `recv()` | TCP, one connection at a time | 256 bytes |

vuln3 takes the port as an optional argument: `./vuln3 [port]`
(default 9999). It loops forever, one connection at a time, until something
kills it. Something will.

## Build

```sh
make            # builds what this machine supports, notes what it skips
make clean
```

Flags (see the Makefile for the full commentary):
`-fno-stack-protector -no-pie -z execstack -g -O0`, so offsets are stable
and the overflow reaches the saved return address instead of tripping a
canary.

### What actually built on the machine that produced this kit

- Toolchain: gcc 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1), x86_64.
- **64-bit: built.** `vuln1`, `vuln2`, `vuln3` all compile and link
  (vuln1 gets one expected linker warning: "the `gets' function is
  dangerous and should not be used". Yes. That is the point of the lab.)
- **32-bit: NOT built.** `-m32` fails at link time on this machine
  (`cannot find Scrt1.o` / `crti.o`): no multilib is installed. The
  Makefile probes for it and skips the `_32` targets with a note instead
  of failing. On a machine with multilib (e.g. `gcc-multilib` on
  Debian/Ubuntu, or Arz's Arch box with the multilib repo enabled), the
  same `make` builds `vuln1_32`, `vuln2_32`, `vuln3_32` as well.
- Your machine may differ. The Makefile adapts; this section records what
  happened on the build machine, not a promise about yours.

## Crash verification (done on the build machine, 2026-11-05)

Each target was fed an oversized input and the crash observed directly.
Exit code 139 = 128 + 11 = killed by SIGSEGV.

### vuln1 (stdin)

```sh
$ echo "hello" | ./vuln1
vuln1: send me a line
vuln1: you sent: hello            # exit 0

$ python3 -c "import sys; sys.stdout.write('A'*400)" > /tmp/in400.txt
$ ./vuln1 < /tmp/in400.txt
vuln1: send me a line
Segmentation fault                # exit 139
```

### vuln2 (argv)

```sh
$ ./vuln2 hello
vuln2: you sent: hello            # exit 0

$ ./vuln2 "$(python3 -c "print('A'*400, end='')")"
Segmentation fault                # exit 139
```

### vuln3 (TCP server)

```sh
$ ./vuln3 9999 &
vuln3: listening on port 9999

# sanity: small messages are served, the server keeps accepting
#   client sends "hello"          -> log: received 5 bytes / copied: hello
#   client sends "second message" -> log: received 14 bytes / copied: second message

# crash: one fat message
$ python3 -c "
import socket
s = socket.create_connection(('127.0.0.1', 9999), timeout=3)
s.sendall(b'A' * 400)
s.close()"
# server log: received 400 bytes, then the process dies
# server exit code: 139 (Segmentation fault)
```

**Verified crashing input: 400 bytes for all three targets** (the exact
minimum differs per binary; finding it is what `fuzz.py` is for).

## A bug found while verifying: stack layout can eat your overflow

The first version of vuln3 declared both the 4096-byte staging buffer and
the 256-byte target buffer as stack locals. It did **not** crash at 400
bytes: the compiler had placed the staging array between `buf` and the
saved return address, so the overflow landed harmlessly in the staging
array and the server kept running.

Fix: the staging buffer is `static` (BSS), keeping the stack frame to
just `buf`. After the fix, the same 400-byte message segfaults the server
(exit 139), as recorded above.

Lesson worth keeping: an overflow overwrites whatever the compiler
actually placed after your buffer, not what you imagine the layout to
be. Check the disassembly / crash, not your assumptions.
