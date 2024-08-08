import logging
import logging.config
import os

from flask import Flask
from flask_restx import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix
import dotenv
dotenv.load_dotenv()

# logging.config.fileConfig('logging.conf')
logging.basicConfig(filename= os.environ.get("GC_SERVICE_LOG_PATH", "/tmp/cg.rest.log"))
log = logging.getLogger("codegenome.rest")
log.setLevel(int(os.environ.get("CG_DEBUG", logging.ERROR)))
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s, %(name)s, %(levelname)s, %(message)s"))
log.addHandler(ch)


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

from .core.genome_service import create_genome_service  # noqa

kgs = create_genome_service()
from .api import api  # noqa

if __name__ == "__main__":
    # Only for debugging while developing
    # app.run(host="127.0.0.1", debug=True, port=5000)
    app.run(host="0.0.0.0", debug=True)
