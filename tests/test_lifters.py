import hashlib
import json
import logging
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
from codegenome.lifters.retdec import CGRetdec  # noqa

os.environ.setdefault("RETDEC_PATH", "/opt/cg/retdec/")

TEST_D = "/tmp/cg_lifter_test"
TEST_FN = "p/p.c"
FUNC = "f1"

LOG_FN = os.path.join(TEST_D, "cg-test.log")

GENE_PATH = os.path.join(TEST_D, "sigmal")
GKG_PATH = GENE_PATH + ".gkg"
bin_id = None  # populated by test_compile()

test_gene_id = None  # populated by test_bingene()

FN = os.path.splitext(os.path.basename(TEST_FN))[0]
DEST_FN = os.path.join(TEST_D, FN)


def prepare():
    os.system("rm -rf " + TEST_D)
    os.system("mkdir -p " + TEST_D)
    logging.basicConfig(
        filename=LOG_FN,
        level=logging.DEBUG,
        format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        force=True,
    )


def clear():
    print(f"clearing {TEST_D}")
    # os.system('rm -rf '+TEST_D)


class TestLifter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare()

    @classmethod
    def tearDownClass(cls):
        clear()

    # test order is sorted test function names!

    def test_01_to_bc(self):
        global bin_id
        cmd = "clang -O0 -o %s %s" % (DEST_FN, TEST_FN)
        os.system(cmd)
        self.assertTrue(os.path.exists(DEST_FN))
        with open(DEST_FN, "rb") as f:
            bin_id = hashlib.sha256(f.read()).hexdigest()

        retdec = CGRetdec()

        retdec.process_file(DEST_FN)

        out_fn = os.path.join(TEST_D, FN + ".bc")
        self.assertTrue(os.path.exists(out_fn))

        out_dir = os.path.join(TEST_D, "tmp")
        os.makedirs(out_dir)

        retdec.process_file(DEST_FN, output_dir=out_dir, output_fname=bin_id)

        out_fn = os.path.join(out_dir, bin_id + ".bc")
        self.assertTrue(os.path.exists(out_fn))


if __name__ == "__main__":
    unittest.main(verbosity=2)
