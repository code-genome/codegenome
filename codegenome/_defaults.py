"""
Global default values
"""
import os
import dotenv
import logging

#not configurable defaults
UNIVERSAL_FUNC_NAME = "_F" 
KNOWN_CALCULATION_METHODS = ["jaccard_distance", "jaccard_distance_w", "all"]
VALID_OUTPUT_DETAILS = ["simple", "complete"]

logger = logging.getLogger("cg.defaults")
dotenv.load_dotenv()

CG_DATA_ROOT_DIR = os.path.expanduser(os.environ.get('CG_DATA_ROOT_DIR',"~/.cg"))
CG_CACHE_DIR = os.path.expanduser(os.environ.get('CG_CACHE_DIR', os.path.join(CG_DATA_ROOT_DIR, 'cache')))

if not os.path.exists(CG_DATA_ROOT_DIR):
    os.makedirs(CG_DATA_ROOT_DIR)
    
if not os.path.exists(CG_CACHE_DIR):
    os.makedirs(CG_CACHE_DIR)

DEFAULT_GENE_VERSION = os.environ.get("DEFAULT_GENE_VERSION", "genes_v0_0_1")
DEFAULT_EXEC_GENE_VERSION = os.environ.get("DEFAULT_EXEC_GENE_VERSION", DEFAULT_GENE_VERSION)

DEFAULT_CALCULATION_METHOD = os.environ.get("DEFAULT_CALCULATION_METHOD", "jaccard_distance_w")
if DEFAULT_CALCULATION_METHOD not in KNOWN_CALCULATION_METHODS:
    logger.error(f"Invalid DEFAULT_CALCULATION_METHOD={DEFAULT_CALCULATION_METHOD}")
    DEFAULT_CALCULATION_METHOD = "jaccard_distance_w"
    
# function compare
# minimum canonicalized function size (canon_bc_size). Smaller than this size will be
# skipped during comparison.
# Ref: 928 is the bc size of the following code
# 'source_filename = "<string>"\n\ndeclare i64 @gf1() local_unnamed_addr\n\ndefine i64 @_F() local_unnamed_addr {\nb1:\n  %v1 = tail call i64 @gf1()\n  ret i64 %v1\n}\n'
#
MIN_GENE_SIZE_FILE_COMPARE = int(os.environ.get( "MIN_GENE_SIZE_FILE_COMPARE" ,1000))

# max genes allowed per file during comparison.
MAX_GENES_PER_FILE_COMPARE = int(os.environ.get( "MAX_GENES_PER_FILE_COMPARE" ,50000))

# during pairwise file compare greater than or equal to this threshold will be considered as a match `~`
FILE_COMPARE_FUNC_MATCH_SIM_THRESHOLD = float(os.environ.get( "FILE_COMPARE_FUNC_MATCH_SIM_THRESHOLD" ,0.99))

# for the same function names, greater than or equal to this threshold will be considered as a mismatch `!`,
# smaller wil be considered delete `-`
FILE_COMPARE_FUNC_MISMATCH_SIM_THRESHOLD = float(os.environ.get("FILE_COMPARE_FUNC_MISMATCH_SIM_THRESHOLD",0.80))
