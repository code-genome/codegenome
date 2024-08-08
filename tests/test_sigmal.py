import logging
import os
import sys
import unittest

import numpy as np

logging.basicConfig(
    filename="/tmp/cg-test-sigmal.log",
    level=logging.DEBUG,
    format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

import test_data as data


class TestSigmal(unittest.TestCase):
    def setUp(self):
        from codegenome.genes import SigmalGene
        from codegenome.ir import IRBinary

        self.irb = IRBinary(data.global_ir, ll=True)
        self.sm = SigmalGene()
        pass

    def test_gene(self):
        bc = self.irb.fs["f0"].get_bc()
        g1 = self.sm.from_bitcode(bc)
        g2 = self.sm.from_bitcode(bc, gene_type="sigmal")
        g3 = self.sm.from_bitcode(bc, gene_type="sigmal2")
        g4 = self.sm.from_bitcode(bc, gene_type="sigmal2b")
        g5 = self.sm.from_bitcode(bc, gene_type="func_only")
        g6 = self.sm.from_data(bc)

        self.assertTrue(np.array_equal(g1, g2))
        self.assertTrue(np.array_equal(g1, g6))
        self.assertFalse(np.array_equal(g1, g3))
        self.assertFalse(np.array_equal(g3, g4))
        self.assertFalse(np.array_equal(g4, g5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
