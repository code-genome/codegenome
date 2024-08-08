import logging
import os
import sys
import unittest

logging.basicConfig(
    filename="/tmp/cg_unit_tests.log",
    level=logging.DEBUG,
    format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)

from test_ir import *
from test_kg import *
from test_lifters import *
from test_sigmal import *

if __name__ == "__main__":
    unittest.main()
