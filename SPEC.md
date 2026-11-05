# Overflow Lab Kit: tool specifications

This is the contract the tools in `tools/` are implemented against, and the
contract `tests/run_tests.py` checks. General rules for all tools:

- Python 3, standard library only.
- Normal output goes to stdout. Errors and usage text go to stderr.
- Exit codes: `0` success, `1` "worked, but the answer is negative"
  (not found / differences found / no crash), `2` usage or I/O error.
- Lab targets only (see `README.md` scope). Nothing in this kit is for use
  against real-world systems.

---

## 1. tools/pattern.py: cyclic pattern create + offset

A cyclic pattern is a long string built from repeating 3-character triples
chosen so that **every 4-byte window in the string is unique**. When a
program crashes with 4 pattern bytes in its instruction pointer, those 4
bytes can only occur at one place in the pattern, so their position is the
exact offset of the overwritten return address.

### 1.1 Pattern construction (exact)

Three character sets, used in this order:

```
UPPER  = ABCDEFGHIJKLMNOPQRSTUVWXYZ
LOWER  = abcdefghijklmnopqrstuvwxyz
DIGITS = 0123456789
```

Generate triples by nesting the sets, UPPER outermost, DIGITS innermost:

```
for U in UPPER:
    for l in LOWER:
        for d in DIGITS:
            emit U + l + d
```

So the pattern begins `Aa0 Aa1 Aa2 ...` (spaces added here only for
readability). The maximum useful length is `26 * 26 * 10 * 3 = 20280`
characters; beyond that, triples repeat and 4-byte windows stop being
unique. Every 4-byte window in the full 20280 characters is unique.

### 1.2 `create <length>`

```
$ python3 tools/pattern.py create <length>
```

- Prints exactly `<length>` pattern characters followed by a single
  newline to stdout. Nothing else on stdout.
- `<length>` must be a positive integer. If it is missing, not an integer,
  or `<= 0`: usage error to stderr, exit `2`.
- If `<length>` > 20280: error to stderr explaining the max, exit `2`.
  Do not print a partial or repeated pattern.

Worked examples (verified against the construction above):

```
$ python3 tools/pattern.py create 30
Aa0Aa1Aa2Aa3Aa4Aa5Aa6Aa7Aa8Aa9

$ python3 tools/pattern.py create 60
Aa0Aa1Aa2Aa3Aa4Aa5Aa6Aa7Aa8Aa9Ab0Ab1Ab2Ab3Ab4Ab5Ab6Ab7Ab8Ab9
```

### 1.3 `offset <value>`

```
$ python3 tools/pattern.py offset <value>
```

Searches for 4 pattern bytes in the full 20280-character pattern and prints
their offset. `<value>` is accepted in three forms:

1. **Register hex value**: 8 hex digits, with or without a `0x` prefix
   (e.g. `0x61413161` or `61413161`). This is a 32-bit value read from a
   register (EIP/RIP low half) after a crash. Registers hold the value,
   memory holds the bytes, and x86 is **little-endian**: the byte in memory
   at the lowest address is the *least* significant byte of the value.
   So the bytes to search for are the value's 4 bytes in little-endian
   order: `0x61413161` -> bytes `61 31 41 61` -> the string `"a1Aa"`.
2. **Raw 4-character string**: exactly 4 printable characters (e.g. `Aa9A`),
   searched for literally, in the order given.
3. **4-byte hex dump**: same syntax as form 1. By the rule above, a hex
   string is always treated as a register value and byte-reversed
   (little-endian) before searching. If you copied bytes from a memory
   dump in display order, use form 2 with the literal characters instead.

Disambiguation rule: an argument of exactly 8 hex digits (optional `0x`
prefix) is form 1/3. Anything else of length 4 is form 2. Anything else is
a usage error (stderr, exit `2`).

Output:

- Found: print the offset as a single decimal integer on its own line,
  exit `0`.
- Not found: print exactly `not found`, exit `1`.

Worked examples (all verified):

```
$ python3 tools/pattern.py offset Aa9A
27

$ python3 tools/pattern.py offset 0x61413161
4
# bytes in memory: 61 31 41 61 = "a1Aa", which starts at index 4

$ python3 tools/pattern.py offset 6Ai7
260

$ python3 tools/pattern.py offset 0x68423368
1000
# bytes in memory: 68 33 42 68 = "h3Bh", which starts at index 1000

$ python3 tools/pattern.py offset ZZZZ
not found
```

---

## 2. tools/badchars.py: bad character discovery

String-copy bugs (strcpy and friends) mangle or stop at certain byte
values: `0x00` always terminates a C string copy, and targets often also
stop at `0x0a` (newline) or `0x0d` (carriage return), or transform bytes.
Before trusting any byte in an input, you send the full range and compare
what actually arrived in memory.

### 2.1 `generate [--exclude LIST] [--out FILE]`

```
$ python3 tools/badchars.py generate [--exclude 00,0a,0d] [--out bytes.bin]
```

- The byte set is `0x01` through `0xFF` (255 bytes). `0x00` is never
  included; it cannot survive a string copy by definition.
- `--exclude LIST`: comma-separated hex bytes to remove, case-insensitive,
  each item optionally `0x`-prefixed (e.g. `00,0a,0d`, `0x0A, 0x0d`).
  Duplicates are ignored. Listing `00` is accepted and is a no-op.
- Always prints the resulting bytes to stdout as one escaped string:
  every byte as `\xNN` with two lowercase hex digits, then a newline.
- `--out FILE`: additionally writes the raw bytes (not the escaped text)
  to FILE. I/O failure: error to stderr, exit `2`.

Example:

```
$ python3 tools/badchars.py generate --exclude 00,0a,0d
\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0b\x0c\x0e\x0f\x10...
# 253 bytes: the full 0x01..0xFF range minus 0x0a and 0x0d
```

### 2.2 `compare <sent.bin> <dump.bin>`

```
$ python3 tools/badchars.py compare sent.bin dump.bin
```

- `sent.bin`: the exact bytes you sent (e.g. produced by
  `generate --out sent.bin`).
- `dump.bin`: the bytes as they landed in the target's memory, saved from
  a debugger after the copy.
- Both files are read as raw bytes. Missing/unreadable file: stderr,
  exit `2`.

Semantics, walking the dump against the sent bytes position by position:

- **Mangled**: at a position present in both files, the byte differs.
  Report position, sent byte, dump byte.
- **Terminated**: the dump is a strict prefix-shortened copy: everything
  matched (or was mangled) up to some point, and the rest is absent. The
  **first missing byte** (the first sent byte with no counterpart in the
  dump) is the terminator candidate: the byte value the copy choked on.
  Report its position, its value, and how many bytes went missing.
- **Extra**: the dump is longer than what was sent. Report the extra byte
  count (should not happen in a plain copy; flag it if it does).

Output format (one line per finding, then a summary line):

```
MANGLED    position 4: sent 0x05, dump has 0xff
TERMINATED copy stopped at position 9: byte 0x0a is the first missing byte (246 bytes missing)
SUMMARY    1 mangled, 1 terminator candidate, 246 missing, 0 extra
```

If the dump is a byte-for-byte copy of the sent bytes:

```
OK all 255 bytes copied cleanly
```

Exit codes: `0` if the copy was clean, `1` if any difference was found,
`2` on usage or I/O error.

---

## 3. tools/fuzz.py: crash discovery harness (local lab only)

Feeds growing buffers of `A` bytes to a local lab target and reports the
smallest size that crashes it. Two transports, one growth strategy.

Growth strategy (both modes):

1. Try sizes from `--start` upward in `--step` increments until the target
   crashes or the size exceeds `--max`.
2. Refine: binary-search between the largest non-crashing size and the
   first crashing size for the **smallest crashing size**.
3. Report it on the final line, exactly: `smallest crashing size: <N>`

Progress lines go to stdout prefixed with `[*]`. If no crash is found up
to `--max`, print `no crash found up to <max>` and exit `1`. On a found
crash, exit `0`.

Common flags: `--start N` (default 100), `--step N` (default 100),
`--max N` (default 5000), `--timeout SECONDS` (default 2, per attempt).

### 3.1 stdin mode

```
$ python3 tools/fuzz.py stdin --target "labs/vuln1" [--start N] [--step N] [--max N] [--timeout S]
```

- Runs the target command (split with `shlex`, **no shell**), writes the
  buffer to its stdin, closes stdin (so line-reading targets see EOF and
  proceed), and waits up to `--timeout`.
- **Crash detection**: the process was killed by a signal (negative return
  code in Python, e.g. `-11` for SIGSEGV). Report the signal number/name
  with the crash size when known.
- A timeout is not a crash: kill the process, count the size as
  non-crashing, note it on a `[*]` line.
- Exit code of the harness: `0` crash found, `1` none found, `2` usage
  error (e.g. target not found / not executable).

Example (illustrative; exact refined size depends on the binary):

```
$ python3 tools/fuzz.py stdin --target "labs/vuln1"
[*] trying 100 bytes: ok
[*] trying 200 bytes: ok
[*] trying 300 bytes: CRASH (signal 11)
[*] refining between 200 and 300...
smallest crashing size: 264
```

### 3.2 tcp mode

```
$ python3 tools/fuzz.py tcp --host 127.0.0.1 --port 9999 [--prefix "STR"] [--suffix "STR"] [--restart "CMD"] [--start N] [--step N] [--max N] [--timeout S]
```

- `--host` defaults to `127.0.0.1`. This is a lab harness; localhost is
  the intended target. `--port` is required.
- Each attempt uses a **fresh connection**: connect (with timeout), send
  `prefix + b"A" * size + suffix` (prefix/suffix encoded latin-1, default
  empty), shut down the write side, briefly try to drain a reply ignoring
  all errors, close. Every socket operation is timeout-guarded and
  exceptions are handled; a failed send never crashes the harness.
- **Crash detection**: after an attempt, wait a moment (about 0.2s), then
  probe with a fresh connection attempt. If the probe cannot connect, the
  server died on that size: crash.
- **Refinement caveat**: a dead server cannot answer refinement probes.
  Two ways to handle it:
  - `--restart "CMD"`: the harness launches CMD (via shell) before the
    first attempt and relaunches it after every detected crash, waiting
    until the port accepts a connection (up to `--timeout` retries).
    With `--restart`, full binary-search refinement works over TCP.
  - Without `--restart`: report the first crashing size at step
    granularity and print a note that refinement needs `--restart` or
    manual server restarts between attempts.
- Harness exit codes are the same as stdin mode.

Example:

```
$ python3 tools/fuzz.py tcp --port 9999 --restart "labs/vuln3 9999"
[*] trying 100 bytes: ok
[*] trying 200 bytes: ok
[*] trying 300 bytes: server stopped responding (crash)
[*] refining between 200 and 300...
smallest crashing size: 264
```

---

## 4. How the tools chain (a real overflow workflow)

1. **Fuzz** the target (`fuzz.py`) to learn the smallest crashing size.
   You now know roughly where the saved return address lives.
2. **Pattern**: generate a pattern of the crashing size
   (`pattern.py create`), feed it to the target, and read the 4 bytes
   sitting in the instruction pointer at the crash. `pattern.py offset`
   converts those bytes into the exact input offset of the saved return
   address.
3. **Badchars**: send the full byte range (`badchars.py generate`) sized
   to reach (not pass) the return address, dump the buffer from a
   debugger, and `badchars.py compare` to learn which bytes are mangled
   or terminate the copy.
4. **v1 stops here**: place a marker value at the offset from step 2
   (e.g. `0x42424242`) and confirm the instruction pointer contains
   exactly that marker at the crash. Instruction-pointer control: proven.
   No shellcode, no payload. That is the v1 finish line by design.
