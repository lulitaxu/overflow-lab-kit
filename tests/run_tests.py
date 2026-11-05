#!/usr/bin/env python3
"""
Acceptance tests for the Overflow Lab Kit tools.

Run from anywhere:

    python3 tests/run_tests.py

The tools in ../tools are implemented by the learner against ../SPEC.md.
Until a tool exists and behaves per spec, its tests report SKIP (with a
"not implemented yet" note) instead of FAIL, so this suite is runnable
from day one. Tests that only exercise the test oracle below always run
and must PASS; they pin down the known-answer values from SPEC.md.

Exit code: 0 when nothing FAILs, 1 otherwise.
"""

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")
LABS_DIR = os.path.join(ROOT, "labs")
PY = sys.executable or "python3"

RESULTS = []


def record(status, name, msg=""):
    RESULTS.append(status)
    line = "[%s] %s" % (status, name)
    if msg:
        line += " - " + msg
    print(line)


# ---------------------------------------------------------------------------
# TEST ORACLE - reference implementation, for TESTING ONLY.
#
# This is an independent implementation of the cyclic pattern from
# SPEC.md section 1, kept inside the test file so the tests can check
# Arz's real implementation in tools/ against known truth. It is
# deliberately NOT part of the tools. Do not copy it into tools/:
# writing that logic yourself is the exercise.
# ---------------------------------------------------------------------------
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGITS = "0123456789"
ORACLE_MAX = 26 * 26 * 10 * 3  # 20280


def oracle_pattern(length):
    parts = []
    total = 0
    for u in _UPPER:
        for lo in _LOWER:
            for d in _DIGITS:
                parts.append(u + lo + d)
                total += 3
                if total >= length:
                    return "".join(parts)[:length]
    return "".join(parts)[:length]


def oracle_offset_of_4(pattern4):
    return oracle_pattern(ORACLE_MAX).find(pattern4)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tool_path(name):
    p = os.path.join(TOOLS_DIR, name)
    return p if os.path.isfile(p) else None


def run_tool(name, args, timeout=60):
    """Run a tool via its SPEC CLI. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [PY, os.path.join(TOOLS_DIR, name)] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Oracle self-checks (must PASS from day one)
# ---------------------------------------------------------------------------

def test_oracle_known_answers():
    name = "oracle: known-answer pattern values from SPEC.md"
    try:
        p60 = oracle_pattern(60)
        assert p60 == ("Aa0Aa1Aa2Aa3Aa4Aa5Aa6Aa7Aa8Aa9"
                       "Ab0Ab1Ab2Ab3Ab4Ab5Ab6Ab7Ab8Ab9"), p60
        assert oracle_offset_of_4("Aa9A") == 27
        # 0x61413161 little-endian -> bytes "a1Aa" -> offset 4
        assert oracle_offset_of_4("a1Aa") == 4
        assert oracle_pattern(ORACLE_MAX)[1000:1004] == "h3Bh"
        record("PASS", name)
    except AssertionError as e:
        record("FAIL", name, str(e))


def test_oracle_uniqueness():
    name = "oracle: every 4-byte window unique over a 2000-char pattern"
    try:
        pat = oracle_pattern(2000)
        assert len(pat) == 2000
        windows = [pat[i:i + 4] for i in range(len(pat) - 3)]
        assert len(windows) == len(set(windows)), "duplicate 4-byte window"
        record("PASS", name)
    except AssertionError as e:
        record("FAIL", name, str(e))


# ---------------------------------------------------------------------------
# tools/pattern.py
# ---------------------------------------------------------------------------

def test_pattern_create():
    name = "pattern.py create: output matches oracle + windows unique"
    if tool_path("pattern.py") is None:
        record("SKIP", name, "not implemented yet (tools/pattern.py missing)")
        return
    try:
        rc, out, err = run_tool("pattern.py", ["create", "2000"])
        got = out.rstrip("\n")
        assert rc == 0, "exit %d, stderr: %s" % (rc, err.strip())
        assert got == oracle_pattern(2000), "create 2000 output != oracle"
        windows = [got[i:i + 4] for i in range(len(got) - 3)]
        assert len(windows) == len(set(windows)), "duplicate 4-byte window"
        record("PASS", name)
    except (AssertionError, subprocess.TimeoutExpired) as e:
        record("FAIL", name, str(e))


def test_pattern_offset():
    name = "pattern.py offset: known answers incl. little-endian hex form"
    if tool_path("pattern.py") is None:
        record("SKIP", name, "not implemented yet (tools/pattern.py missing)")
        return
    try:
        # Fixed known answers from SPEC.md.
        for arg, want in [("Aa9A", "27"), ("0x61413161", "4"),
                          ("6Ai7", "260"), ("0x68423368", "1000")]:
            rc, out, err = run_tool("pattern.py", ["offset", arg])
            assert rc == 0 and out.strip() == want, \
                "offset %s -> rc=%d out=%r, want %s" % (arg, rc, out, want)
        # Runtime-chosen substring, raw and little-endian hex forms.
        full = oracle_pattern(ORACLE_MAX)
        chosen = 1234
        sub = full[chosen:chosen + 4]
        rc, out, _ = run_tool("pattern.py", ["offset", sub])
        assert rc == 0 and out.strip() == str(chosen), \
            "offset %s -> %r, want %d" % (sub, out, chosen)
        hexform = "0x%08x" % int.from_bytes(sub.encode("latin-1"), "little")
        rc, out, _ = run_tool("pattern.py", ["offset", hexform])
        assert rc == 0 and out.strip() == str(chosen), \
            "offset %s -> %r, want %d" % (hexform, out, chosen)
        # Unknown bytes must be reported as not found.
        rc, out, _ = run_tool("pattern.py", ["offset", "ZZZZ"])
        assert out.strip() == "not found", "ZZZZ -> %r" % out
        record("PASS", name)
    except (AssertionError, subprocess.TimeoutExpired) as e:
        record("FAIL", name, str(e))


# ---------------------------------------------------------------------------
# tools/badchars.py
# ---------------------------------------------------------------------------

def parse_escaped(text):
    return bytes(int(h, 16) for h in re.findall(r"\\x([0-9a-fA-F]{2})", text))


def test_badchars_generate():
    name = "badchars.py generate: full range and exclusions"
    if tool_path("badchars.py") is None:
        record("SKIP", name, "not implemented yet (tools/badchars.py missing)")
        return
    try:
        rc, out, err = run_tool("badchars.py", ["generate"])
        assert rc == 0, "exit %d, stderr: %s" % (rc, err.strip())
        assert parse_escaped(out) == bytes(range(1, 256)), "full range wrong"
        rc, out, err = run_tool("badchars.py",
                                ["generate", "--exclude", "00,0a,0d"])
        assert rc == 0, "exit %d, stderr: %s" % (rc, err.strip())
        want = bytes(b for b in range(1, 256) if b not in (0x0A, 0x0D))
        assert parse_escaped(out) == want, "excluded range wrong"
        record("PASS", name)
    except (AssertionError, subprocess.TimeoutExpired) as e:
        record("FAIL", name, str(e))


def test_badchars_compare():
    name = "badchars.py compare: mangled byte + 0x0a truncation detected"
    if tool_path("badchars.py") is None:
        record("SKIP", name, "not implemented yet (tools/badchars.py missing)")
        return
    try:
        sent = bytes(range(1, 256))
        # Craft a dump: bytes 0x01..0x09 arrived, 0x05 was mangled to 0xff,
        # and 0x0a terminated the copy (0x0a and everything after is absent).
        dump = bytearray(sent[:9])      # 0x01..0x09
        dump[4] = 0xFF                  # position of 0x05
        with tempfile.TemporaryDirectory() as td:
            sp, dp = os.path.join(td, "sent.bin"), os.path.join(td, "dump.bin")
            with open(sp, "wb") as f:
                f.write(sent)
            with open(dp, "wb") as f:
                f.write(bytes(dump))
            rc, out, err = run_tool("badchars.py", ["compare", sp, dp])
        low = out.lower()
        assert rc == 1, "expected exit 1 on differences, got %d" % rc
        assert "0x05" in low, "mangled 0x05 not reported: %r" % out
        assert "0xff" in low, "mangled value 0xff not reported: %r" % out
        assert "0x0a" in low, "terminator 0x0a not reported: %r" % out
        record("PASS", name)
    except (AssertionError, subprocess.TimeoutExpired) as e:
        record("FAIL", name, str(e))


# ---------------------------------------------------------------------------
# tools/fuzz.py against labs/vuln1
# ---------------------------------------------------------------------------

def test_fuzz_stdin_vuln1():
    name = "fuzz.py stdin: crashes labs/vuln1 and reports a size"
    if tool_path("fuzz.py") is None:
        record("SKIP", name, "not implemented yet (tools/fuzz.py missing)")
        return
    binary = os.path.join(LABS_DIR, "vuln1")
    if not os.path.isfile(binary):
        record("SKIP", name, "labs not built (run: make -C labs)")
        return
    try:
        rc, out, err = run_tool(
            "fuzz.py",
            ["stdin", "--target", binary,
             "--start", "100", "--step", "100", "--max", "3000"],
            timeout=300,
        )
        m = re.search(r"smallest crashing size:\s*(\d+)", out)
        assert rc == 0, "exit %d, out tail: %s" % (rc, out[-300:])
        assert m, "no 'smallest crashing size' line in output: %s" % out[-300:]
        size = int(m.group(1))
        assert 256 < size <= 3000, "implausible crash size %d" % size
        record("PASS", name, "reported smallest crashing size %d" % size)
    except (AssertionError, subprocess.TimeoutExpired) as e:
        record("FAIL", name, str(e))


# ---------------------------------------------------------------------------

def main():
    test_oracle_known_answers()
    test_oracle_uniqueness()
    test_pattern_create()
    test_pattern_offset()
    test_badchars_generate()
    test_badchars_compare()
    test_fuzz_stdin_vuln1()

    passed = RESULTS.count("PASS")
    failed = RESULTS.count("FAIL")
    skipped = RESULTS.count("SKIP")
    print("\nSummary: %d passed, %d failed, %d skipped (of %d)"
          % (passed, failed, skipped, len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
