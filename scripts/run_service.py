#!/usr/bin/env python3
import json
import logging
import os
import sys
import dotenv
dotenv.load_dotenv()

logfn = os.environ.get("GC_SERVICE_LOG_PATH", "/tmp/cg_dev_run.log")
if not os.path.exists(os.path.dirname(logfn)):
    os.makedirs(os.path.dirname(logfn))
    
logging.basicConfig(
    filename=logfn,
    format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils/app/")
)
from app.main import *  # noqa

sgkg_log = logging.getLogger("codegenome")
sgkg_log.setLevel(logging.DEBUG)

host = "127.0.0.1"
port = 5001

if len(sys.argv) > 1:
    host = sys.argv[1]
if len(sys.argv) > 2:
    port = int(sys.argv[2])
app.run(host=host, debug=True, port=port)
