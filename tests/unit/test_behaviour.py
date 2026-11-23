import tempfile
import unittest
from pathlib import Path

from sentinel_x.behaviour.__main__ import run
from sentinel_x.behaviour.dataset import Trace, partition
from sentinel_x.behaviour.model import END, START, TraceModel


class TraceTests(unittest.TestCase):
    def test_no_cross_trace_edges(self):
        m = TraceModel().fit([(1,2), (2,3)])
        self.assertEqual(m.edges[2,2], 0)
        self.assertEqual(m.edges[START,2], 1)
        self.assertEqual(m.edges[2,END], 1)
        for source in (START,1,2,3,-3):
            self.assertAlmostEqual(sum(m.probability(source,j) for j in m.alphabet),1)

    def test_order_and_unknowns(self):
        m = TraceModel().fit([(1,2,3)] * 5)
        normal, reversed_ = m.score((1,2,3)), m.score((3,2,1))
        self.assertAlmostEqual(normal[0], reversed_[0])
        self.assertGreater(reversed_[1], normal[1])
        self.assertGreater(m.score((252,))[1], 0)
        with self.assertRaises(ValueError):
            m.score(())

    def test_group_exclusion(self):
        rows = [Trace("d","development","benign",(0,)), Trace("overlap","test","benign",(0,)),
                Trace("n","test","benign",(9,)), Trace("conflict","test","attack",(9,)),
                Trace("a","test","attack",(2,))]
        _, c, t, audit = partition(rows)
        self.assertEqual(len(c), 1)
        self.assertEqual([r.name for r in t],["a"])
        self.assertEqual(audit["heldout_conflicting_removed"],2)
        self.assertEqual(audit["heldout_overlap_removed"],1)

    def test_fixture_run_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "results"
            result = run(out,"fixture",None)
            self.assertEqual(run(out,"fixture",None),result)
            self.assertGreater(result["metrics"]["markov"]["average_precision"],0.9)
            (out / "scores.csv").write_text("edited")
            with self.assertRaises(ValueError):
                run(out,"fixture",None)
