import os

#override for REST service
DEFAULT_CALCULATION_METHOD = "jaccard_distance"
DEFAULT_COMPARE_METHOD = "genes_v1_3_1.jaccard_distance_w"
DEFAULT_OUTPUT_DETAIL = "simple"
TMP_DIR_PREFIX = "cg_temp_upload_"
TMP_UPLOAD_DIR = os.environ.get("TMP_UPLOAD_DIR", "/tmp/")
