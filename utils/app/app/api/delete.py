import os
import json
from flask_restx import Resource, fields
from flask import request
from flask_restx import Resource
from werkzeug.datastructures import FileStorage
import copy
import traceback
import logging
import tempfile

from .api import api
from ..main import kgs
from ..core.genome_service import API_STATE_RESULT_NOT_READY, API_STATE_EMPTY_RESULT, API_STATE_ERROR
from ..defaults import *

logger = logging.getLogger('codegenome.rest')
ns = api.namespace("api/v1/delete", description="Delete from KG.")

upload_parser = api.parser()

file_args = api.model(
    "file_args",
    {"file_id": fields.String(
        required=True, default='',
        description="The identifier of the file")})


@ns.route("/file")
@ns.response(200, "Success")
@ns.response(404, "Object id not found")
class DeleteFile(Resource):
    """Delete by `file_id`."""

    @ns.expect(file_args)
    def post(self):
        """Delete by `file_id`."""
        try:
            args = dict(api.payload)
            ret = kgs.delete_file(args.get('file_id'))
            if ret.get('status') == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get('status') == API_STATE_EMPTY_RESULT:
                return ret, 404
            elif ret.get('status') == API_STATE_ERROR:
                return ret, 500
            return ret
        except Exception as e:
            api.abort(500, f"Exception: {e}")
