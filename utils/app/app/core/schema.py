import hashlib
import uuid

import numpy as np

DEFAULT_ID_DELIMITER = ":"  # TODO move to a separate common module


def get_type_from_id(id_):
    if type(id_) == str:
        id_comp = id_.split(DEFAULT_ID_DELIMITER)
        if len(id_comp) > 1:
            return id_comp[0]
    return None


class KGNodeTypes:
    file = "file"
    gene = "gene"
    cache = "cache"
    stat = "stat"


class KGNodeID:
    @staticmethod
    def _mk_id(_type, _hash):
        # return f"{_type}:{_hash}"
        return _hash

    @staticmethod
    def split(_id):
        return str(_id).split(":")

    @staticmethod
    def id(_type, data=None, hash=None, file_path=None, return_hash=False):
        if hash is None:
            if data is not None:
                if type(data) != bytes:
                    # forced conversion!
                    data = str(data).strip().lower().encode("utf-8")
                hash = hashlib.sha256(data).hexdigest()

            elif file_path is not None:
                with open(file_path, "rb") as f:
                    hash = hashlib.sha256(f.read()).hexdigest()
            else:
                raise Exception("parameter missing")

        if return_hash:
            return KGNodeID._mk_id(_type, hash), hash
        return KGNodeID._mk_id(_type, hash)

    @staticmethod
    def file_id(file_data=None, file_hash=None, file_path=None, return_hash=False):
        return KGNodeID.id(
            KGNodeTypes.file, file_data, file_hash, file_path, return_hash
        )
