# Overflow Lab Kit: buffer overflow tools for exploit development

A pwn practice kit for learning how a stack buffer overflow really works,
one controlled step at a time, in a lab you own. You build the classic
exploit development tools yourself, against a written spec: a cyclic
pattern generator, an offset finder, a bad-char checker, and a small crash
fuzzer. The kit ships the other half ready-made: intentionally vulnerable
lab targets (verified to crash, see `labs/README.md`) and an acceptance
test suite that grades your tools as you write them.

## Scope: lab only, no exceptions

This kit exists for authorized, self-contained practice:

- Your own binaries compiled from `labs/` in this repo.
- Legal lab environments: VulnHub VMs, TryHackMe / HackTheBox style labs,
  CTF targets, your own throwaway machines.

Never point any of this at a real-world target: not a website, not someone
else's server, not a "quick test" against a live service. The fuzzer only
talks to `127.0.0.1` by default and the lab targets bind locally. If a target
is not yours and not a lab, it is out of scope, full stop.

## The v1 boundary

Version 1 proves exactly one thing: **instruction-pointer control**. You find
where a crash happens, locate the exact offset of the saved return address,
and show you can place a chosen marker value (e.g. `0x42424242`) into the
instruction pointer.

That is where v1 stops:

- No shellcode.
- No payload delivery, no shells, no weaponization of any kind.
- No bypass work (ASLR / DEP / ROP) in v1.

Control proof in a lab binary is the skill. Everything past it is out of
scope for this version on purpose.

## Modules

| Piece | Where | What it does |
|---|---|---|
| Cyclic pattern tool | `tools/pattern.py` (spec: `SPEC.md` §1) | Creates a pattern whose every 4-byte window is unique, and finds the offset of a 4-byte value found in a crash. |
| Bad character tool | `tools/badchars.py` (spec: `SPEC.md` §2) | Generates the full byte range minus exclusions, and compares what you sent against a memory dump to find bytes that are mangled or that terminate the copy. |
| Fuzzer / crash harness | `tools/fuzz.py` (spec: `SPEC.md` §3) | Feeds growing buffers to a local target (stdin or TCP on localhost) and reports the smallest crashing size. |
| Lab targets | `labs/` | Three intentionally vulnerable C programs to practice against (stdin, argv, TCP server). |
| Acceptance tests | `tests/run_tests.py` | Checks the tools against the spec. Unimplemented tools report SKIP, so the suite runs from day one. |

The tools themselves are implemented by the learner against `SPEC.md`.
`tools/TOOLS.md` maps each tool to its spec section.

## Build order

Implement in this order, it is the order a real overflow workflow uses them:

1. **pattern** (`create` first, then `offset`)
2. **offset** lookup (part of `tools/pattern.py`)
3. **badchars** (`generate`, then `compare`)
4. **fuzz** (stdin mode, then TCP mode)

## Getting started

```sh
# 1. Build the lab targets (see labs/README.md for what actually built)
make -C labs

# 2. Run the acceptance suite (tools start as SKIP until you write them)
python3 tests/run_tests.py

# 3. Implement the tools against SPEC.md, re-running the tests as you go
```

## The workflow these tools chain into

```
fuzz.py     -> find the smallest input size that crashes the target
pattern.py  -> send a cyclic pattern of that size; read the 4 bytes that
               land in the instruction pointer; `offset` tells you exactly
               where the saved return address sits in your input
badchars.py -> before any payload thinking: learn which bytes survive the
               target's copy unchanged and which ones kill the string
v1 stops    -> overwrite the instruction pointer with a marker value at
               the offset you found. Control proven. Done.
```

See `SPEC.md` for the exact CLI contract for each tool.
