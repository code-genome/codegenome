import os

import joblib

_GKG_FILE_VERSION = "0.3"
_CANON_FILE_VERSION_ = "0.3"
_GENE_FILE_VERSION_ = "0.3"


def get_file_meta(file_path, file_size=None):
    if file_size is None:
        file_size = os.path.getsize(file_path)

    return {"file_path": file_path, "file_size": file_size}


def prep_gkg_file(gkg):
    file_content = {
        "type": "gkg",
        "version": _GKG_FILE_VERSION,
        "data": gkg.serialize(),
    }
    return file_content


def read_gkg_file(path):
    data = joblib.load(path)
    assert data["type"] == "gkg"
    assert data["version"] == _GKG_FILE_VERSION
    return data


def prep_gene_file(genes, binid, file_meta):
    file_content = {
        "type": "gene",
        "version": _GENE_FILE_VERSION_,
        "binid": binid,
        "genes": genes,
        "file_meta": file_meta,
    }
    return file_content


def read_gene_file(path):
    data = joblib.load(path)
    assert data["type"] == "gene"
    assert data["version"] == _GENE_FILE_VERSION_
    return data


def prep_canon_file(ir_bin, file_meta):
    file_content = {
        "type": "canon",
        "version": _CANON_FILE_VERSION_,
        "binid": ir_bin._bin_id,
        "funcs": ir_bin.serialize(),
        "file_meta": file_meta,
    }
    return file_content


def read_canon_file(path):
    data = joblib.load(path)
    assert data["type"] == "canon"
    assert data["version"] == _CANON_FILE_VERSION_
    return data
