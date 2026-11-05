# Tools: implementation map

The four tools are implemented by the learner against `../SPEC.md`, in the
build order below. Nothing here is implemented yet; the acceptance suite in
`../tests/run_tests.py` reports SKIP for each tool until its file exists
and behaves per spec.

| # | File to write | Spec | Subcommands | Status |
|---|---|---|---|---|
| 1 | `tools/pattern.py` | `SPEC.md` §1 | `create <length>`, `offset <value>` | not implemented yet (yours to write) |
| 2 | `tools/badchars.py` | `SPEC.md` §2 | `generate [--exclude LIST] [--out FILE]`, `compare <sent.bin> <dump.bin>` | not implemented yet (yours to write) |
| 3 | `tools/fuzz.py` | `SPEC.md` §3 | `stdin --target "CMD"`, `tcp --host H --port N [--prefix S] [--suffix S] [--restart "CMD"]` | not implemented yet (yours to write) |

Build order: pattern first, then offset (same file), then badchars, then
the fuzzer. Run `python3 tests/run_tests.py` after each one.
