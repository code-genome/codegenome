import logging
import traceback

from flask_restx import Resource, fields

from ..core.genome_service import (API_STATE_EMPTY_RESULT,
                                   API_STATE_RESULT_NOT_READY)
from ..defaults import *
from ..main import kgs
from .api import api, check_event_loop

logger = logging.getLogger("codegenome.rest")

ns = api.namespace("api/v1/compare", description="Compare binaries.")

compare_file_id_args = api.model(
    "compare_file_id_args",
    {
        "id1": fields.String(
            required=True, description="The file identifier (file sha256 hash)"
        ),
        "id2": fields.String(
            required=True, description="The file identifier (file sha256 hash)"
        ),
        "method": fields.String(
            required=False,
            default=DEFAULT_COMPARE_METHOD,
            description="Internal query method to be used. \
    Currently supported values: [`gene_v0`, `genes_v1_3_0`, `genes_v1_3_0.jaccard_distance`, `genes_v1_3_0.jaccard_distance_w`,\
         `genes_v1_3_0.composition_ratio`, `genes_v1_3_0.composition_ratio_w`,\
         `genes_v1_3_0.containment_ratio`]",
        ),
        "output_detail": fields.String(
            required=False,
            default=DEFAULT_OUTPUT_DETAIL,
            description="Output format. \
    Supported values: ['simple','complete']",
        ),
    },
)


@ns.route("/files/by_file_ids")
@ns.response(200, "Final result")
@ns.response(202, "Request received. Result not ready. Must retry.")
@ns.response(204, "Result empty")
@ns.response(404, "File id not found")
class KGCompareFileIDs(Resource):
    """Compare binaries using genes."""

    @ns.expect(compare_file_id_args)
    def post(self):
        """Compare binaries using genes."""
        args = api.payload
        check_event_loop()
        try:
            ret = kgs.api_files_compare_kg(
                file_id1=args["id1"],
                file_id2=args["id2"],
                method=args.get("method", DEFAULT_COMPARE_METHOD),
                output_detail=args.get("output_detail", DEFAULT_OUTPUT_DETAIL),
            )
            if ret.get("status") == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get("status") == API_STATE_EMPTY_RESULT:
                if ret.get("query") is None:  # root search node not found.
                    return ret, 404
                else:
                    return ret, 204

            return ret
        except Exception as e:
            api.abort(405, f"Exception: {e}")


# TODO
# @ns.route("/packages/by_package_ids")
# @ns.route("/genes/by_gene_ids")
