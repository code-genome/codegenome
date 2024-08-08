import copy
import json
import logging
import os
import tempfile
import traceback

from flask import request
from flask_restx import Resource, fields
from werkzeug.datastructures import FileStorage

from ..core.genome_service import (API_STATE_EMPTY_RESULT, API_STATE_ERROR,
                                   API_STATE_RESULT_NOT_READY)
from ..defaults import *
from ..main import kgs
from .api import api

logger = logging.getLogger("codegenome.rest")
ns = api.namespace("api/v1/add", description="Add to KG.")

upload_parser = api.parser()
upload_parser.add_argument("file", location="files", type=FileStorage, required=True)


@ns.route("/file")
@ns.response(200, "Final result")
@ns.response(
    202, "Request received. Result not ready. Must check using `status/job/<job_id>`."
)
@ns.response(204, "Result empty")
@ns.response(404, "Submissions id not found")
@ns.expect(upload_parser)
class Add(Resource):
    def post(self):
        args = upload_parser.parse_args(request)
        uploaded_file = args["file"]  # This is FileStorage instance
        # We can get the filename, stream, mimetype, etc. from it
        logger.info("Received a file %s" % uploaded_file)
        try:
            if not os.path.exists(TMP_UPLOAD_DIR):
                os.makedirs(TMP_UPLOAD_DIR)

            tmpdir = tempfile.mkdtemp(prefix=TMP_DIR_PREFIX, dir=TMP_UPLOAD_DIR)
            tmpfn = os.path.join(tmpdir, os.path.basename(uploaded_file.filename))
            uploaded_file.save(tmpfn)

            ret = kgs.api_add_file(tmpfn)
            if ret.get("status") == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get("status") == API_STATE_EMPTY_RESULT:
                if ret.get("query") is None:  # root search node not found.
                    return ret, 206
            elif ret.get("status") == API_STATE_ERROR:
                return ret, 404
            return ret
        except Exception as e:
            api.abort(404, f"Exception: {e}")
