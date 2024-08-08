import base64
import pickle
import zlib

import numpy as np

from .._defaults import *


def encode_gene(gene_data):
    if type(gene_data) == list:
        gene_data = np.array(gene_data).astype("float32").tobytes()
    if type(gene_data) == np.ndarray:
        gene_data = gene_data.astype("float32").tobytes()
    if type(gene_data) != bytes:
        raise Exception("gene data can not be converted to bytes.")
    return base64.b64encode(zlib.compress(gene_data)).decode("ascii")


def decode_gene(data_str):
    return np.frombuffer(zlib.decompress(base64.b64decode(data_str)), dtype="float32")


def decode_gene_by_ver(gene):
    # Implement version specific decoding if needed
    # gene.get('version')

    raw_gene = gene["value"]
    if type(raw_gene) == str:
        raw_gene = decode_gene(gene["value"])
    return raw_gene


def gene_distance(raw_gene1, raw_gene2, normalized=True):
    x = np.linalg.norm(raw_gene1 - raw_gene2)
    if normalized:
        x /= np.sqrt(len(raw_gene1))
    return x


def gene_similarity_score_adjusted(sim):
    return np.power(float(sim), 2)  # tone down similarity score


def gene_similarity(raw_gene1, raw_gene2, adjusted=False, normalized=True):
    sim = 1.0 - gene_distance(raw_gene1, raw_gene2, normalized)
    if adjusted:
        sim = gene_similarity_score_adjusted(sim)
    return sim


def gene_distance_by_ver(gene1, gene2, normalized=True):
    raw_gene1, raw_gene2 = decode_gene_by_ver(gene1), decode_gene_by_ver(gene2)
    x = np.linalg.norm(raw_gene1 - raw_gene2)
    if normalized:
        x /= np.sqrt(len(raw_gene1))
    return x


def gene_similarity_by_ver(gene1, gene2, adjusted=False, normalized=True):
    sim = 1.0 - gene_distance_by_ver(gene1, gene2, normalized)
    if adjusted:
        sim = gene_similarity_score_adjusted(sim)
    return sim


class GeneIterator(object):
    def __init__(self, data):
        self.idx = 0
        self.data = data

    def __iter__(self):
        return self

    def __next__(self):
        self.idx += 1
        try:
            return self.__getitem__(self.idx - 1)
        except IndexError:
            self.idx = 0
            raise StopIteration

    def __getitem__(self, ii):
        # override according to file version
        return self.data[ii]


class GeneFile(object):
    def __init__(self, data=None, file_path=None):
        if data is not None:
            self.data = pickle.loads(data)
        elif file_path is not None:
            self.data = pickle.load(open(file_path, "rb"))
        else:
            raise Exception("invalid argument.")

        if self.data["type"] != "gene":
            raise Exception(f"invalid file type {self.data['type']}")

        self.version = self.data["version"]

        if self.version == "0.3":
            self.init_v0_3()
        else:
            raise Exception("Unknown file version.")

    def init_v0_3(self):
        self.binid = self.data["binid"]
        self._genes = self.data["genes"]
        self._meta = self.data["file_meta"]

        class GeneIteratorEx(GeneIterator):
            def __getitem__(self, ii):
                cid, funcs, gene, gene_meta = self.data[ii]
                bc_size, file_offset = gene_meta
                return {
                    "canon_bc_id": cid,
                    "func_names": funcs,
                    "gene": gene,
                    "canon_bc_size": bc_size,
                    "file_offset": file_offset,
                }

        self.genes = GeneIteratorEx(self._genes)

    @classmethod
    def load(cls, file_path):
        return cls(file_path=file_path)

    @classmethod
    def loads(cls, data):
        return cls(data=data)
