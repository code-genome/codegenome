import hashlib
import os
import pickle
import re
import shutil
import subprocess
import sys

"""
Build sha256 hashmap

usage:
python build_hash_map.py src_path output_path
"""

PAT_EXECS = "ELF|PE32|DLL"


def hashmap(srcd, output=None):
    hmap = {}
    flist = subprocess.check_output(["find", srcd]).split("\n")
    for fn in flist:
        ft = subprocess.check_output(["file", "-b", fn]).strip()
        m = re.findall(PAT_EXECS, ft, re.IGNORECASE)
        if len(m) > 0:
            bin_id = hashlib.sha256(open(fn, "rb").read()).hexdigest()
            if bin_id in hmap:
                hmap[bin_id].append(fn)
            else:
                hmap[bin_id] = [fn]
    if output:
        with open(output, "w") as f:
            pickle.dump(hmap, f)
    return hmap


hashmap(sys.argv[1], sys.argv[2])
