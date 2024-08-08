from flask_restx import Api

from ..main import app


def check_event_loop():
    pass


api = Api(
    app,
    version="0.0.1",
    title="Code Genome",
    description="Code Genome APIs",
)

from . import add  # noqa
from . import compare  # noqa
from . import delete  # noqa
from . import search  # noqa
from . import status  # noqa

# import config
