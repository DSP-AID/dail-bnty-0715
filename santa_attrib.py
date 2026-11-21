#!/usr/bin/env python3
"""santa_attrib.py — per-puzzle attribution tool for Kaggle Santa 2026 "The Elf Calculator" submissions.

Given a submission CSV (header `id,program`; program = JSON list of [op, src_a, src_b, dst]
register instructions), report per puzzle:

* provenance   — which named engine/method produced the program, by exact instruction-sequence
                 match against reference CSVs registered with --engine NAME=path.csv;
* technique    — counts of structural techniques (add/sub/mul/div/double/square/diff_squares);
* helper-chain depth — longest dependency chain of computed values feeding any register.

Stdlib only. No Kaggle account, no network at run time: everything reported is computable
from the CSV itself (instruction totals, depth and structure), which is what reproduces the
known public totals. Value-level replay against train.json stays a house-side step (dataset
is Kaggle-auth gated; verified 2026-11-21: download endpoint returns HTTP 401 without token).

Usage:
  python santa_attrib.py SUBMISSION.csv [--engine NAME=ref.csv]... \
      [--out-prefix report/attribution_report] [--expect-total N]
Exit code 1 on --expect-total mismatch or any parse/validity failure.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

OPS = ("+", "-", "*", "/")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_submission(path):
    """Parse a Santa-2026 style submission CSV -> {puzzle_id: [instructions]}.

    Each instruction is [op, src_a, src_b, dst]; ops must be one of + - * / and operands
    are integer register slots.
    """
    rows = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or [c.strip().lower() for c in header[:2]] != ["id", "program"]:
            raise ValueError(f"{path}: expected header 'id,program', got {header!r}")
        for lineno, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                continue
            pid = row[0].strip()
            try:
                insts = json.loads(row[1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: bad program JSON: {exc}") from exc
            if not isinstance(insts, list) or any(
                not (isinstance(i, list) and len(i) == 4 and i[0] in OPS
                     and all(isinstance(x, int) for x in i[1:]))
                for i in insts
            ):
                raise ValueError(f"{path}:{lineno}: malformed instruction list")
            if pid in rows:
                raise ValueError(f"{path}:{lineno}: duplicate puzzle id {pid}")
            rows[pid] = [tuple(i) for i in insts]
    return rows


def canonical(prog):
    """Hashable canonical form of a program, for exact-match attribution."""
    return tuple(tuple(i) for i in prog)


def analyze_program(insts):
    """Return (instruction_count, helper_chain_depth, technique Counter) for one program.

    Helper-chain depth: register depths start at 0 (starting values); an instruction
    writing dst has depth 1 + max(depth[src_a], depth[src_b]) and becomes that slot's new
    depth (slot reuse chains on the value live at read time). Program depth = max over all
    instructions. Techniques are structural signatures computable without puzzle values:
    op counts (+, -, *, /); double ('+' with identical operands); square ('*' with
    identical operands); diff_squares (a '-' whose two operand slots were each last
    written by a '*' with identical operands — x*x and y*y feeding a subtraction).
    """
    cur_depth = {}          # register slot -> depth of value currently in it
    producer = {}           # register slot -> instruction that last wrote it
    tech = Counter()
    max_depth = 0
    for op, a, b, d in insts:
        tech[op] += 1
        dep = 1 + max(cur_depth.get(a, 0), cur_depth.get(b, 0))
        cur_depth[d] = dep
        max_depth = max(max_depth, dep)
        if a == b:
            if op == "+":
                tech["double"] += 1
            elif op == "*":
                tech["square"] += 1
        if op == "-":
            ia, ib = producer.get(a), producer.get(b)
            if (ia is not None and ib is not None
                    and ia[0] == "*" and ia[1] == ia[2]
                    and ib[0] == "*" and ib[1] == ib[2]):
                tech["diff_squares"] += 1
        producer[d] = (op, a, b, d)
    return len(insts), max_depth, tech


def attribute(sub_rows, engines):
    """Per-puzzle provenance by exact program match against each engine's reference rows.

    engines: {name: {puzzle_id: program}}. Returns {puzzle_id: [engine names matched]};
    an empty list means unattributed (matches no registered engine).
    """
    index = {name: {pid: canonical(prog) for pid, prog in rows.items()}
             for name, rows in engines.items()}
    out = {}
    for pid, prog in sub_rows.items():
        c = canonical(prog)
        out[pid] = sorted(name for name, ref in index.items() if ref.get(pid) == c)
    return out


def build_report(sub_path, engine_paths):
    """Full report dict. engine_paths: ordered {name: reference CSV path}."""
    sub_rows = load_submission(sub_path)
    engines = {name: load_submission(p) for name, p in engine_paths.items()}
    prov = attribute(sub_rows, engines)
    puzzles = {}
    tech_totals = Counter()
    depth_hist = Counter()
    engine_stats = {name: {"puzzles": 0, "instructions": 0} for name in engine_paths}
    total = 0
    for pid in sorted(sub_rows):
        n, dep, tech = analyze_program(sub_rows[pid])
        total += n
        tech_totals.update(tech)
        depth_hist[dep] += 1
        hits = prov[pid]
        for name in hits:
            engine_stats[name]["puzzles"] += 1
            engine_stats[name]["instructions"] += n
        puzzles[pid] = {
            "instructions": n,
            "helper_chain_depth": dep,
            "techniques": {k: tech[k] for k in sorted(tech)},
            "provenance": hits or ["unattributed"],
        }
    depths = [p["helper_chain_depth"] for p in puzzles.values()]
    unattr = [p for p in puzzles.values() if p["provenance"] == ["unattributed"]]
    return {
        "tool": "santa_attrib v1",
        "submission": {"path": str(sub_path).replace("\\", "/"),
                       "sha256": sha256_file(sub_path),
                       "puzzles": len(sub_rows)},
        "reference_engines": {name: {"path": str(p).replace("\\", "/"),
                                     "sha256": sha256_file(p),
                                     **engine_stats[name]}
                              for name, p in engine_paths.items()},
        "totals": {
            "instructions": total,
            "first5_instructions": sum(
                puzzles[f"scored_{i:04d}"]["instructions"]
                for i in range(1, 6) if f"scored_{i:04d}" in puzzles),
            "techniques": {k: tech_totals[k] for k in sorted(tech_totals)},
            "helper_chain_depth": {
                "max": max(depths) if depths else 0,
                "mean": round(sum(depths) / len(depths), 3) if depths else 0,
                "histogram": {str(k): depth_hist[k] for k in sorted(depth_hist)},
            },
            "unattributed_puzzles": len(unattr),
        },
        "puzzles": puzzles,
    }


def render_markdown(rep):
    t = rep["totals"]
    lines = [
        "# Santa 2026 attribution report — %s" % rep["submission"]["path"],
        "",
        "- tool: `%s` (deterministic; no network, stdlib only)" % rep["tool"],
        "- submission sha256: `%s` (%d puzzles)" % (rep["submission"]["sha256"], rep["submission"]["puzzles"]),
        "- **total instructions: %s** | first5 (scored_0001..0005): %s" % (t["instructions"], t["first5_instructions"]),
        "- helper-chain depth: max %s, mean %s, unattributed %s" % (
            t["helper_chain_depth"]["max"], t["helper_chain_depth"]["mean"], t["unattributed_puzzles"]),
        "- techniques: " + ", ".join("%s=%d" % kv for kv in t["techniques"].items()),
        "",
        "| engine | puzzles attributed | instructions attributed |",
        "|---|---|---|",
    ]
    for name, e in rep["reference_engines"].items():
        lines.append("| %s | %d | %d |" % (name, e["puzzles"], e["instructions"]))
    unattr_inst = sum(p["instructions"] for p in rep["puzzles"].values()
                      if p["provenance"] == ["unattributed"])
    lines.append("| unattributed | %d | %d |" % (t["unattributed_puzzles"], unattr_inst))
    lines += ["", "Depth histogram (depth: puzzles):", "",
              " ".join("%s:%d" % kv for kv in t["helper_chain_depth"]["histogram"].items()),
              "", "Per-puzzle detail lives in the JSON report of the same run. First 10 puzzles:",
              "", "| id | instructions | depth | provenance | techniques |", "|---|---|---|---|---|"]
    for pid in list(rep["puzzles"])[:10]:
        p = rep["puzzles"][pid]
        lines.append("| %s | %d | %d | %s | %s |" % (
            pid, p["instructions"], p["helper_chain_depth"],
            ",".join(p["provenance"]),
            ", ".join("%s:%d" % kv for kv in p["techniques"].items())))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("submission", help="submission CSV (id,program)")
    ap.add_argument("--engine", action="append", default=[], metavar="NAME=PATH.csv",
                    help="reference engine CSV for exact-match provenance (repeatable)")
    ap.add_argument("--out-prefix", help="write PREFIX.json and PREFIX.md")
    ap.add_argument("--expect-total", type=int, help="fail unless total instructions == N")
    args = ap.parse_args(argv)

    engine_paths = {}
    for spec in args.engine:
        name, _, path = spec.partition("=")
        if not name or not path:
            ap.error(f"--engine needs NAME=path.csv, got {spec!r}")
        engine_paths[name] = path

    rep = build_report(args.submission, engine_paths)

    if args.out_prefix:
        pre = Path(args.out_prefix)
        pre.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n": reports must be byte-identical on every platform (verify.sh byte-compares)
        with open(pre.with_suffix(".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(rep, f, indent=1, sort_keys=True)
        with open(pre.with_suffix(".md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(render_markdown(rep))

    print(json.dumps({"path": rep["submission"]["path"], "sha256": rep["submission"]["sha256"],
                      "puzzles": rep["submission"]["puzzles"],
                      "total_instructions": rep["totals"]["instructions"],
                      "first5_instructions": rep["totals"]["first5_instructions"]}, indent=1))

    if args.expect_total is not None and rep["totals"]["instructions"] != args.expect_total:
        print(f"EXPECTED TOTAL {args.expect_total} — MISMATCH", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
