#!/usr/bin/env bash
# bnty_0715 verification — runs on any clean machine, stdlib Python only, no API keys.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi
[ -n "$PY" ] || { echo "no working python found" >&2; exit 1; }

echo "== unit tests =="
"$PY" -m unittest discover -s tests

echo "== known totals: Orbit 138,054 (Kaggle ref 58570422) =="
"$PY" santa_attrib.py data/orbit_santa2026_138054.csv --expect-total 138054 \
    --engine orbit_portfolio_138054=data/orbit_santa2026_138054.csv \
    --out-prefix report/orbit_138054

echo "== known totals: Orbit 137,932 (Kaggle ref 58577052) =="
"$PY" santa_attrib.py data/orbit_santa2026_137932.csv --expect-total 137932 \
    --engine orbit_portfolio_138054=data/orbit_santa2026_138054.csv \
    --engine orbit_rewritten_137932=data/orbit_santa2026_137932.csv \
    --out-prefix report/orbit_137932_vs_portfolio

echo "== first5 = 950 (bnty_0713 bar) =="
"$PY" - <<'PY'
import json
for f in ("report/orbit_138054.json", "report/orbit_137932_vs_portfolio.json"):
    t = json.load(open(f))["totals"]
    assert t["first5_instructions"] == 950, (f, t["first5_instructions"])
print("first5 950 OK in both reports")
PY

echo "== committed reports are byte-reproducible =="
"$PY" - <<'PY'
import json, subprocess, sys, filecmp, tempfile, os
# regenerate into a temp dir and byte-compare against committed report/
for cmd_prefix, args in (
    ("report/orbit_138054", ["data/orbit_santa2026_138054.csv", "--engine",
        "orbit_portfolio_138054=data/orbit_santa2026_138054.csv"]),
    ("report/orbit_137932_vs_portfolio", ["data/orbit_santa2026_137932.csv", "--engine",
        "orbit_portfolio_138054=data/orbit_santa2026_138054.csv", "--engine",
        "orbit_rewritten_137932=data/orbit_santa2026_137932.csv"]),
):
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "r")
    subprocess.run([sys.executable, "santa_attrib.py"] + args + ["--out-prefix", out],
                   check=True, capture_output=True)
    for ext in (".json", ".md"):
        assert filecmp.cmp(out + ext, cmd_prefix + ext, shallow=False), cmd_prefix + ext
print("reports byte-identical after regeneration")
PY

echo "== ALL CHECKS PASSED =="
