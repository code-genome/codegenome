import logging

from flask_restx import Resource, fields

from ..core.genome_service import (API_STATE_EMPTY_RESULT,
                                   API_STATE_RESULT_NOT_READY)
from ..main import kgs
from .api import api

ns = api.namespace("api/v1/status", description="Service status")

logger = logging.getLogger("codegenome.rest")


@ns.route("/")
class ConfigStatus(Resource):
    """Service status."""

    def get(self):
        """Service status"""
        try:
            return kgs.status()
        except KeyError as e:
            api.abort(404, f"Failed to retrieve service status.")


@ns.route("/job/<job_id>")
@ns.response(200, "Final result")
@ns.response(202, "Request received. Result not ready. Must retry.")
@ns.response(204, "Result empty")
@ns.response(404, "Job id not found")
class Job(Resource):
    """Job status"""

    def get(self, job_id):
        """Get Job status."""

        try:
            ret = kgs.check_job(job_id)
            if ret.get("status") == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get("status") == API_STATE_EMPTY_RESULT:
                if ret.get("query") is None:  # root search node not found.
                    return ret, 404

            return ret
        except Exception as e:
            api.abort(500, f"Exception: {e}")
