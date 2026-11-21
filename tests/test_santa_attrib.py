"""Unit tests for santa_attrib — hand-checked fixture values plus regression on the
real published Orbit files shipped in data/ (totals reproduce Kaggle publicScores)."""

import io
import json
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import santa_attrib as sa

DATA = Path(__file__).resolve().parent.parent / "data"


class TestAnalyzeProgram(unittest.TestCase):
    def test_handchecked_chain(self):
        # [*,3,3,4], [*,4,4,5], [-,5,4,6]: squares of 3 and 4 feeding a subtraction.
        n, depth, tech = sa.analyze_program(
            [("*", 3, 3, 4), ("*", 4, 4, 5), ("-", 5, 4, 6)])
        self.assertEqual(n, 3)
        self.assertEqual(depth, 3)  # 1 -> 2 -> 3 dependency chain
        self.assertEqual(tech, Counter({"*": 2, "-": 1, "square": 2, "diff_squares": 1}))

    def test_slot_reuse_chains_on_live_value(self):
        # dst slot reuse: [*,7,10,10] chains on the value live in slot 10 at read time.
        # depths: r10=1, r11=1, r12=2, then r10=1+max(r7=0, old r10=1)=2 -> max 2.
        n, depth, tech = sa.analyze_program(
            [("-", 9, 4, 10), ("+", 4, 2, 11), ("*", 10, 11, 12), ("*", 7, 10, 10)])
        self.assertEqual(n, 4)
        self.assertEqual(depth, 2)

    def test_depth_starts_at_zero_for_fresh_slots(self):
        n, depth, tech = sa.analyze_program([("+", 0, 1, 2)])
        self.assertEqual((n, depth), (1, 1))
        self.assertEqual(tech, Counter({"+": 1}))


class TestFixtureEndToEnd(unittest.TestCase):
    def run_cli(self, extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = sa.main(extra)
        return rc, json.loads(out.getvalue())

    def test_fixture_totals_and_attribution(self):
        rep = sa.build_report(
            DATA / "fixture_submission.csv",
            {"engineA": DATA / "fixture_engineA.csv",
             "engineB": DATA / "fixture_engineB.csv"})
        self.assertEqual(rep["totals"]["instructions"], 6)
        self.assertEqual(rep["totals"]["first5_instructions"], 0)
        self.assertEqual(rep["totals"]["techniques"],
                         {"+": 2, "-": 1, "*": 2, "/": 1,
                          "diff_squares": 1, "double": 1, "square": 2})
        self.assertEqual(rep["totals"]["helper_chain_depth"],
                         {"histogram": {"1": 1, "2": 1, "3": 1}, "max": 3, "mean": 2.0})
        self.assertEqual(rep["puzzles"]["toy_0001"]["provenance"], ["engineA", "engineB"])
        self.assertEqual(rep["puzzles"]["toy_0002"]["provenance"], ["engineA"])
        self.assertEqual(rep["puzzles"]["toy_0003"]["provenance"], ["unattributed"])
        self.assertEqual(rep["totals"]["unattributed_puzzles"], 1)
        self.assertEqual({k: (v["puzzles"], v["instructions"])
                          for k, v in rep["reference_engines"].items()},
                         {"engineA": (2, 4), "engineB": (1, 1)})

    def test_expect_total_exit_codes(self):
        base = [str(DATA / "fixture_submission.csv")]
        rc, summary = self.run_cli(base + ["--expect-total", "6"])
        self.assertEqual((rc, summary["total_instructions"]), (0, 6))
        rc, _ = self.run_cli(base + ["--expect-total", "7"])
        self.assertEqual(rc, 1)

    def test_bad_header_rejected(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as tf:
            tf.write("a,b\n1,2\n")
            path = Path(tf.name)
        with self.assertRaises(ValueError):
            sa.load_submission(path)


class TestPublishedOrbitFiles(unittest.TestCase):
    """Regression on the real public data: these totals are Kaggle publicScores, verified
    against Orbit's bounty entries on DAiL (bnty_0689 ref 58570422 = 138054; bnty_0696
    ref 58577052 = 137932; bnty_0713 bar text: Orbit scores 950 on puzzles 1-5)."""

    F138 = DATA / "orbit_santa2026_138054.csv"
    F137 = DATA / "orbit_santa2026_137932.csv"

    def test_138054_reproduces_known_totals(self):
        rep = sa.build_report(self.F138, {})
        self.assertEqual(rep["submission"]["sha256"],
                         "fea37476d6c71050ffb72148ab1798f242ffe45c8267ed39e7416a7b8235ddc3")
        self.assertEqual(rep["submission"]["puzzles"], 1000)
        self.assertEqual(rep["totals"]["instructions"], 138054)
        self.assertEqual(rep["totals"]["first5_instructions"], 950)

    def test_137932_reproduces_known_totals(self):
        rep = sa.build_report(self.F137, {})
        self.assertEqual(rep["submission"]["sha256"],
                         "659f2bd95d7944adebc1e98e57961be4b282a7e71097b36fb601eef4537ba6e6")
        self.assertEqual(rep["totals"]["instructions"], 137932)
        self.assertEqual(rep["totals"]["first5_instructions"], 950)

    def test_cross_attribution_partition(self):
        rep = sa.build_report(self.F137, {"orbit_portfolio_138054": self.F138})
        n_attr = sum(e["puzzles"] for e in rep["reference_engines"].values())
        n_unattr = rep["totals"]["unattributed_puzzles"]
        self.assertEqual(n_attr + n_unattr, 1000)
        self.assertGreater(n_unattr, 0)  # the rewriter pass really changed programs
        attr_inst = sum(e["instructions"] for e in rep["reference_engines"].values())
        unattr_inst = sum(p["instructions"] for p in rep["puzzles"].values()
                          if p["provenance"] == ["unattributed"])
        self.assertEqual(attr_inst + unattr_inst, 137932)


if __name__ == "__main__":
    unittest.main()
