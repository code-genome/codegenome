import hashlib
import json
import logging
import os
import shutil
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

os.environ.setdefault("RETDEC_PATH", "/opt/cg/retdec/")

from codegenome._defaults import (DEFAULT_GENE_VERSION,  # noqa
                                  UNIVERSAL_FUNC_NAME)
from codegenome.kg import GenomeKG  # noqa

TEST_D = "/tmp/cg_kg_test"
TEST_FN = "p/p.c"
FUNC = "f1"
KG_REPO = os.path.join(TEST_D, "testkg.gkg")
LOG_FN = os.path.join(TEST_D, "cg-test.log")


FN = os.path.splitext(os.path.basename(TEST_FN))[0]
DEST_FN = os.path.join(TEST_D, FN)
DEST_FN2 = DEST_FN + "_2"


def prepare():
    if os.path.exists(TEST_D):
        shutil.rmtree(TEST_D)
    os.makedirs(TEST_D)
    logging.basicConfig(
        filename=LOG_FN,
        level=logging.DEBUG,
        format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        force=True,
    )


def clear():
    print(f"clearing {TEST_D}")
    # shutil.rmtree(TEST_D)


class TestKG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare()

    @classmethod
    def tearDownClass(cls):
        clear()

    # test order is sorted test function names!

    def test_01_add_file(self):
        global bin_id, bin_id2
        cmd = "clang -O0 -o %s %s" % (DEST_FN, TEST_FN)
        os.system(cmd)
        cmd = "clang -O1 -o %s %s" % (DEST_FN2, TEST_FN)
        os.system(cmd)
        self.assertTrue(os.path.exists(DEST_FN))
        self.assertTrue(os.path.exists(DEST_FN2))
        with open(DEST_FN, "rb") as f:
            bin_id = hashlib.sha256(f.read()).hexdigest()

        with open(DEST_FN2, "rb") as f:
            bin_id2 = hashlib.sha256(f.read()).hexdigest()

        kg = GenomeKG(KG_REPO)
        kg.add_file(DEST_FN, keep_aux_files=False)
        self.assertTrue(os.path.exists(KG_REPO))
        self.assertFalse(os.path.exists(os.path.join(KG_REPO, ".auxs", bin_id + ".bc")))
        self.assertFalse(
            os.path.exists(os.path.join(KG_REPO, ".auxs", bin_id + ".canon"))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(KG_REPO, "genes", DEFAULT_GENE_VERSION, bin_id + ".gene")
            )
        )

        shutil.rmtree(KG_REPO)
        kg = GenomeKG(KG_REPO)
        kg.add_file(DEST_FN)
        self.assertTrue(os.path.exists(KG_REPO))
        self.assertTrue(os.path.exists(os.path.join(KG_REPO, ".auxs", bin_id + ".bc")))
        self.assertTrue(
            os.path.exists(os.path.join(KG_REPO, ".auxs", bin_id + ".canon"))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(KG_REPO, "genes", DEFAULT_GENE_VERSION, bin_id + ".gene")
            )
        )

        self.assertEqual(len(kg.bins), 1)
        self.assertTrue(len(kg.gene_ids) >= 14)
        ll = kg.get_ll(kg.gene_ids[0])
        # print(ll)
        self.assertTrue(ll is not None)

        bg = kg.get_bin(bin_id)
        self.assertTrue(bg is not None)
        self.assertTrue(len(bg.gene_ids) >= 14)

        ll = bg.get_ll(bg.gene_ids[0])
        # print(ll)
        self.assertTrue(ll is not None)

        # re add
        t1 = time.time()
        kg.add_file(DEST_FN)
        t2 = time.time()
        self.assertTrue(t2 - t1 < 0.1)  # should be fast with no reprocessing

        kg.add_file(DEST_FN2)

        self.assertEqual(len(kg.bins), 2)
        self.assertTrue(len(kg.gene_ids) >= 20)

    def test_02_load(self):
        kg = GenomeKG(KG_REPO)
        self.assertEqual(len(kg.bins), 0)

        kg.load()
        self.assertEqual(len(kg.bins), 2)
        self.assertTrue(len(kg.gene_ids) >= 20)
        ll = kg.get_ll(kg.gene_ids[0])
        # print(ll)
        self.assertTrue(ll is not None)

        # import ipdb; ipdb.set_trace()

    def test_03_bindiff_old(self):
        kg = GenomeKG(KG_REPO)
        kg.load()
        a, b = list(kg.bins.keys())[:2]
        diff = kg.bindiff_old(a, b)
        self.assertTrue(diff < 0.4)

    def test_04_bindiff(self):
        kg = GenomeKG(KG_REPO)
        kg.load()
        a, b = list(kg.bins.keys())[:2]
        ret, stat = kg.bindiff(a, b)
        self.assertEqual(ret.get("similarity"), 100)
        self.assertEqual(len(ret.get("diff_details")), 21)

    def test_05_bc(self):
        kg = GenomeKG(KG_REPO)
        kg.load()
        gids = kg.get_gene_ids("main")
        ll = kg.get_ll(gids[0])
        self.assertTrue("@gv1" in ll)
        self.assertTrue("main" not in ll)

    def test_05_local_apis(self):
        kg = GenomeKG(KG_REPO)
        kg.load()
        bin = kg.get_bin(bin_id)
        gid = bin.get_gene_id("main")
        gid2 = kg.get_gene_ids("main", bin_id)
        gid3 = kg.get_gene_ids("main", bin_id2)

        self.assertEqual(len(gid2), 1)
        self.assertEqual(len(gid3), 1)
        self.assertEqual(gid, gid2[0])
        self.assertNotEqual(gid, gid3[0])

        gids = kg.get_gene_ids("main")
        self.assertEqual(len(gids), 2)

        ir = kg.get_ll(gid)
        # print(ir)
        self.assertTrue(type(ir), str)
        self.assertTrue(UNIVERSAL_FUNC_NAME in ir)

        ginfo = kg.get_gene_info(gid)
        print(ginfo)
        self.assertEqual("gene", ginfo.get("type"))
        self.assertTrue("llvm_ir" in ginfo)
        self.assertEqual(["main"], list(ginfo.get("function_names", {}).values())[0])
        import ipdb

        ipdb.set_trace()  # noqa


if __name__ == "__main__":
    unittest.main(verbosity=2)
