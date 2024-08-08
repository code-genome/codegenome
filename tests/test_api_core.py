import hashlib
import json
import logging
import os
import sys
import time
import unittest

import test_data as data

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils/app")
)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
from app.core.genome_service import *  # noqa

from codegenome._defaults import UNIVERSAL_FUNC_NAME  # noqa

TEST_D = "/tmp/cg_test_api"
GENE_D = os.path.join("/tmp/cg_test_api", "local.kg")
TEST_FN = "p/p.c"
FUNC = "f1"
FN = os.path.splitext(os.path.basename(TEST_FN))[0]
DEST_FN = os.path.join(TEST_D, FN)

LOG_FN = os.path.join(TEST_D, "cg-test-api-core.log")

bin_id = None

CG_CONFIG = {"cache_dir": TEST_D, "gene_dir": GENE_D, "keep_aux_files": True}


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


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare()

    @classmethod
    def tearDownClass(cls):
        clear()

    def setUp(self):
        pass

    def test_01_compile(self):
        global bin_id
        import shutil

        dest_s = os.path.join(TEST_D, os.path.basename(TEST_FN))
        shutil.copy(TEST_FN, dest_s)
        cmd = "clang -O0 -o %s %s" % (DEST_FN, dest_s)
        os.system(cmd)
        self.assertTrue(os.path.exists(DEST_FN))
        bin_id = hashlib.sha256(open(DEST_FN, "rb").read()).hexdigest()

    def test_02_genome_service(self):
        global bin_id
        gs = GenomeService(CG_CONFIG)
        self.assertTrue(os.path.exists(TEST_D))

        ret = gs.check_job("abcd")
        self.assertEqual(ret["status"], API_STATE_ERROR)

        ret = gs.api_add_file(DEST_FN)

        self.assertEqual(ret["status"], API_STATE_RESULT_NOT_READY)
        job_id = ret.get("job_id")
        # check immediately, should fail
        ret = gs.check_job(job_id)
        self.assertEqual(ret["status"], API_STATE_RESULT_NOT_READY)

        for _ in range(5):
            time.sleep(1)
            # print(_)
            ret = gs.check_job(job_id)
            if ret.get("status") == API_STATE_SUCCESS:
                break
        # print(ret)
        self.assertEqual(ret["status"], API_STATE_SUCCESS)
        self.assertEqual(ret["ret_status"], "new_file")

        # check job, should not exit (self clean after successful completion)
        ret = gs.check_job(job_id)
        # print(ret)
        # only enable in prod
        # self.assertEqual(ret['status'],  API_STATE_ERROR)

        # try on existing file
        ret = gs.api_add_file(DEST_FN)

        self.assertEqual(ret["status"], API_STATE_SUCCESS)
        self.assertEqual(ret["ret_status"], "existing_file")

        ret = gs.api_files_compare_kg(bin_id, bin_id)

        # print(ret)
        self.assertEqual(ret["status"], API_STATE_SUCCESS)
        self.assertTrue(ret.get("query") is not None)

        # get ll
        ret = gs.api_get_ir("main", bin_id)
        # print(ret)
        self.assertEqual(ret["status"], API_STATE_SUCCESS)
        ret = ret.get("data")
        self.assertTrue("llvm_ir" in ret)
        self.assertTrue("gene_id" in ret)
        ir = ret.get("llvm_ir")
        # print(ir)
        self.assertEqual(type(ir), str)
        self.assertTrue(UNIVERSAL_FUNC_NAME in ir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
