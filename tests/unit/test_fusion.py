import unittest
from sentinel_x.behaviour.dataset import Trace
from sentinel_x.fusion.__main__ import groupsplit, supervised_parts


class FusionTests(unittest.TestCase):
    def test_scenario_groups_are_atomic_and_disjoint_from_density(self):
        rows = [Trace("t","development","benign",(77,)),
                Trace("n","test","benign",(77,))]
        for i in range(10):
            for j in range(3):
                rows.append(Trace(f"A/F_{i}/a{j}","test","F",(i,j,10)))
            rows.append(Trace(f"n/{i}","test","benign",(i,46)))
        rows.extend([Trace("A/F_1/c","test","F",(88,)),
                     Trace("A/F_2/c","test","F",(88,))])
        density,parts,audit=supervised_parts(rows)
        groups = [{g for _,r,g in batch if r.label} for batch in parts.values()]
        self.assertEqual(len(groups),3)
        self.assertEqual(len(set.union(*groups)),sum(map(len,groups)))
        self.assertTrue(all(not(set(density) & {k for k,_,_ in b}) for b in parts.values()))
        self.assertEqual(audit["ambiguous_scenario_rows_removed"],2)
        self.assertEqual(audit["overlapping_rows_removed"],1)

    def test_group_split_input_order_invariance(self):
        keys = list(map(str,range(11)))
        self.assertEqual(groupsplit(keys),groupsplit(reversed(keys)))
