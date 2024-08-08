import logging
import traceback

from flask_restx import Resource, fields

from ..core.genome_service import (API_STATE_EMPTY_RESULT, API_STATE_ERROR,
                                   API_STATE_RESULT_NOT_READY)
from ..defaults import *
from ..main import kgs
from .api import api, check_event_loop

logger = logging.getLogger("codegenome.rest")

ns = api.namespace("api/v1/search", description="Search for info")

gene_info_args = api.model(
    "gene_info_args",
    {
        "gene_id": fields.String(
            required=False,
            default="",
            description="The gene identifier (sha256 hash). If this is not passed, `file_id` and `function_name` must be passed ",
        ),
        "file_id": fields.String(
            required=False,
            default="",
            description="The file identifier if known (file sha256 hash)",
        ),
        "function_name": fields.String(
            required=False,
            default="",
            description="For searching by function name if known.",
        ),
        "include_llvm_ir": fields.Boolean(
            required=False, default=False, description="Include LLVM IR in output."
        ),
        "include_asm": fields.Boolean(
            required=False, default=False, description="Include disassembly output."
        ),
        "include_gene_value": fields.Boolean(
            required=False,
            default=False,
            description="Include raw gene value in output.",
        ),
        "include_function_names": fields.Boolean(
            required=False,
            default=False,
            description="Include all function names in output.",
        ),
    },
)

obj_info_args = api.model(
    "obj_info_args",
    {
        "obj_id": fields.String(
            required=False, default="", description="The identifier of gene or file"
        ),
        "output_detail": fields.String(
            required=False,
            default=DEFAULT_OUTPUT_DETAIL,
            description="Output format. \
    Supported values: ['simple','complete']",
        ),
    },
)


@ns.route("/gene")
@ns.response(200, "Final result")
@ns.response(202, "Request received. Result not ready. Must retry.")
@ns.response(404, "Object id not found")
class SearchGene(Resource):
    """Search by id"""

    @ns.expect(gene_info_args)
    def post(self):
        """Search either by `gene_id` or (`file_id` and `function_name`) combination."""
        try:
            args = api.payload
            ret = kgs.api_get_gene_info(**args)
            if ret.get("status") == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get("status") == API_STATE_EMPTY_RESULT:
                return ret, 404
            elif ret.get("status") == API_STATE_ERROR:
                return ret, 500

            return ret
        except Exception as e:
            api.abort(500, f"Exception: {e}")


@ns.route("/by_id")
@ns.response(200, "Final result")
@ns.response(202, "Request received. Result not ready. Must retry.")
@ns.response(404, "Object id not found")
class SearchID(Resource):
    """Search by id"""

    @ns.expect(obj_info_args)
    def post(self):
        """Search either by `gene_id` or (`file_id` and `function_name`) combination."""
        try:
            args = dict(api.payload)
            output = args.pop("output_detail")
            flag = False
            if output == "complete":
                flag = True

            args.update(
                {
                    "include_genes": flag,
                    "include_llvm_ir": flag,
                    "include_asm": flag,
                    "include_gene_value": flag,
                    "include_function_names": flag,
                }
            )
            ret = kgs.api_get_node_info(**args)
            if ret.get("status") == API_STATE_RESULT_NOT_READY:
                return ret, 202
            elif ret.get("status") == API_STATE_EMPTY_RESULT:
                return ret, 404
            elif ret.get("status") == API_STATE_ERROR:
                return ret, 500

            return ret
        except Exception as e:
            api.abort(500, f"Exception: {e}")
