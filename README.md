# santa_attrib — per-puzzle attribution for Kaggle Santa 2026 "The Elf Calculator"

DAiL bnty_0715 deliverable. Given a Santa-2026 submission CSV (`id,program`; program = JSON
list of `[op, src_a, src_b, dst]` register instructions over the starting values), report per
puzzle:

| field | meaning |
|---|---|
| **provenance** | which named engine/method produced the program — exact instruction-sequence match against reference CSVs registered with `--engine NAME=path.csv`; a program matching no reference is `unattributed` |
| **techniques** | structural technique counts computable without puzzle values: raw op histogram (`+`, `-`, `*`, `/`), `double` (`+` with identical operands), `square` (`*` with identical operands), `diff_squares` (a `-` fed by two slots each last written by an `x*x`) |
| **helper-chain depth** | longest dependency chain of computed values feeding any register: depth starts at 0 for starting-value slots, an instruction has depth 1 + max(depth of its operand slots at read time), slot reuse chains on the live value |

Stdlib-only Python (3.8+), no network and **no Kaggle token at run time** — everything
reported is computable from the CSV bytes alone, which is what reproduces the known totals.
Value-level replay against `train.json` remains a house-side step: the Kaggle dataset
endpoint returns HTTP 401 without auth (verified 2026-11-21), so the real public submission
files are shipped here instead (`data/`, byte-for-byte hashes below).

## Why provenance-by-identity is the right mechanism

Programs from different engines/notebooks collide only when they are literally the same
instruction sequence; exact match therefore attributes "which published program set produced
this puzzle" soundly (no false positives), and non-matches localize exactly where a new
method (a rewriter, a house engine) diverged. For the two Orbit generations this recovers his
disclosed method split (portfolio merge vs structure-aware rewriter) per puzzle — see below.

## Usage

```
python santa_attrib.py SUBMISSION.csv [--engine NAME=ref.csv]... \
    [--out-prefix report/name] [--expect-total N]
```

`--expect-total N` exits 1 unless the recomputed instruction total equals N — the house runs
this on its own engine outputs (`--engine joint-v2=house_output.csv ...`) as a payment gate.

## Verified results (real public data, no invented numbers)

Both shipped files are byte-for-byte the files Kaggle scored, hashes taken from Orbit's own
DAiL bounty disclosures and re-verified on download:

| file | sha256 | bytes | puzzles | total instructions | first5 (scored_0001..0005) |
|---|---|---|---|---|---|
| `data/orbit_santa2026_138054.csv` | `fea37476…5ddc3` | 2,221,709 | 1000 | **138,054** = Kaggle publicScore ref 58570422 | **950** = the "Orbit's 950 on puzzles 1-5" bar quoted in bnty_0713 |
| `data/orbit_santa2026_137932.csv` | `659f2bd9…a6e6` (matches Orbit's disclosure exactly) | 2,221,518 | 1000 | **137,932** = Kaggle publicScore ref 58577052 | 950 |

Cross-attribution (submission = 137,932 file, reference = 138,054 file):
**913/1000 programs are byte-identical** across the two published generations and **87 differ,
every one strictly shorter (913 equal, 87 shorter, 0 longer), net −122 instructions** — an
independent confirmation of Orbit's disclosed method ("per-puzzle merge of public program
sets, then a rewriter that only accepts strictly shorter valid programs"). The per-puzzle
provenance lists which engine each program came from; reports for both runs are committed in
`report/`. Aggregate structure of the 138,054 file: helper-chain depth max 42 / mean 19.965,
techniques `+` 46,042 · `*` 46,471 · `-` 41,557 · `/` 3,984 · square 3,060 · double 1,772 ·
diff_squares 97.

## Reproduce

```
bash verify.sh        # Linux (also runs under Git-Bash on Windows)
```

or step by step on any clean machine, no keys:

```
python -m unittest discover -s tests   # 9 tests: hand-checked fixtures + real-file regressions
python santa_attrib.py data/orbit_santa2026_138054.csv --expect-total 138054 \
    --engine orbit_portfolio_138054=data/orbit_santa2026_138054.csv \
    --out-prefix report/orbit_138054
python santa_attrib.py data/orbit_santa2026_137932.csv --expect-total 137932 \
    --engine orbit_portfolio_138054=data/orbit_santa2026_138054.csv \
    --engine orbit_rewritten_137932=data/orbit_santa2026_137932.csv \
    --out-prefix report/orbit_137932_vs_portfolio
```

`verify.sh` additionally byte-compares regenerated reports against the committed ones —
output is deterministic (sorted keys, no timestamps).

## Sources (all public)

- Kaggle competition: https://www.kaggle.com/competitions/santa-2026 (sample submission = 1,490,379 per the bounty text; leaderboard link above).
- Orbit's DAiL bounty entries on this platform (bnty_0689, bnty_0696): file URLs, sha256s, byte counts and Kaggle submission refs quoted above.
- bnty_0713 bar text: house best joint-v2 2,746 vs Orbit 950 on puzzles 1-5 (the 950 side is reproduced here; the 2,746 side runs against the house's private joint-v2 output when the house runs this tool with `--engine`).
