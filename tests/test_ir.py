import json
import logging
import os
import sys
import time
import unittest

import test_data as data

logging.basicConfig(
    filename="/tmp/cg-test-ir.log",
    level=logging.DEBUG,
    format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))


class TestIR(unittest.TestCase):
    def setUp(self):
        pass

    def test_global(self):
        from codegenome.ir import IRBinary

        irb = IRBinary(data.global_ir, ll=True)
        self.assertTrue(len(irb.fs), 2)
        f0_str = irb.fs["f0"].get_ll()
        self.assertTrue("@gv1" in f0_str)
        self.assertTrue("@gv2" in f0_str)

    def test_types(self):
        from codegenome.ir import IRBinary

        irb = IRBinary(data.type_ir, ll=True)
        self.assertTrue(len(irb.fs), 2)
        f0_str = irb.fs["f0"].get_ll()
        # print(f0_str)
        # import ipdb; ipdb.set_trace()
        self.assertTrue("%t1" in f0_str)
        self.assertTrue("%t2" in f0_str)
        self.assertFalse("type1" in f0_str)
        self.assertFalse("type2" in f0_str)

    def test_externs(self):
        from codegenome.ir import IRBinary

        irb = IRBinary(data.externs_ir, ll=True)
        self.assertTrue(len(irb.fs), 2)
        f0_str = irb.fs["f0"].get_ll()
        # print(f0_str)
        # import ipdb
        # ipdb.set_trace()
        self.assertTrue("@printf" in f0_str)
        self.assertTrue("@gf1" in f0_str)
        self.assertFalse("local_func" in f0_str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
