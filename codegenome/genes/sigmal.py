##
## This code is part of the Code Genome Framework.
##
## (C) Copyright IBM 2023.
##
## This code is licensed under the Apache License, Version 2.0. You may
## obtain a copy of this license in the LICENSE.txt file in the root directory
## of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
##
## Any modifications or derivative works of this code must retain this
## copyright notice, and modified files need to carry a notice indicating
## that they have been altered from the originals.
##

import array
import hashlib
import logging
import os
import sys
from collections import deque
from datetime import datetime
from threading import Lock, Thread

import numpy as np
# import matplotlib.pylab as plt
import scipy
from PIL import Image
from sklearn.neighbors import BallTree

from .base import CGGeneBase

logger = logging.getLogger("codegenome.gene.sigmal")

MAX_SIZE_KB = 10000
FEATURE_UNIT = 128
FEATURE_SHAPE = (FEATURE_UNIT, FEATURE_UNIT)
FEATURE_SIZE = 320
COL_SIZE = 256
SIZE_MAP = [
    (10, 32),
    (30, 64),
    (60, 128),
    (100, 256),
    (500, 512),
    (1000, 768),
    (MAX_SIZE_KB, 1024),
]

GENE_TYPE_CONFIG = {
    "sigmal2": {"resample": Image.Resampling.NEAREST, "weights": [0.8, 0.2]},
    "sigmal2b": {"resample": Image.Resampling.BICUBIC, "weights": [0.8, 0.2]},
}


def prep_data_sigmal2(bc):
    """
    Split IR to function and auxiliary data
    """
    import llvmlite.binding as llvm

    from codegenome._defaults import UNIVERSAL_FUNC_NAME

    obj = llvm.parse_bitcode(bc)
    fns = {f.name: f for f in obj.functions}
    func_str = str(fns[UNIVERSAL_FUNC_NAME])

    struc_str = [str(x) for x in obj.struct_types]
    gvs_str = [str(x) for x in obj.global_variables]
    other_funcdef_str = [str(v) for k, v in fns.items() if k != UNIVERSAL_FUNC_NAME]

    aux_str = "\n".join(struc_str + gvs_str + other_funcdef_str)
    if aux_str == "":
        aux_str = " "

    return func_str, aux_str


class SigmalGene(CGGeneBase):
    def from_data(self, data):
        return self.feats_from_binary(data)

    def from_bitcode(self, data, gene_type="sigmal"):
        """
        gene_type can be sigmal|sigmal2|sigmal2b|func_only

        """
        if gene_type == "sigmal":
            raw_gene = self.feats_from_binary(data)
        else:
            if gene_type in GENE_TYPE_CONFIG:
                func, aux = prep_data_sigmal2(data)
                raw_gene = self.feats_from_binary_list(
                    [func, aux],
                    weights=GENE_TYPE_CONFIG[gene_type]["weights"],
                    resample=GENE_TYPE_CONFIG[gene_type]["resample"],
                )
            elif gene_type == "func_only":
                func, aux = prep_data_sigmal2(data)
                raw_gene = self.feats_from_binary_list([func], weights=[1.0])
        return raw_gene

    def feats_from_file(self, fn, only_desc=False):
        with open(fn, "rb") as f:
            fdata = f.read()
            md5 = hashlib.md5(fdata).hexdigest()
            dsize = os.path.getsize(fn)
            if only_desc:
                return md5, dsize, None
            else:
                return md5, dsize, self.feats_from_binary(fdata)
        return None

    def feats_from_buff(self, data, only_desc=False):
        md5 = hashlib.md5(data).hexdigest()
        dsize = len(data)
        if only_desc:
            return md5, dsize, None
        else:
            return md5, dsize, self.feats_from_binary(data)

    def binary_to_img_old(self, data):
        dsize = len(data)
        dsize_kb = dsize / 1024
        col_size = 32
        for fs, sz in SIZE_MAP:
            if dsize_kb < fs:
                col_size = sz

        return self.array_to_img(np.frombuffer(data, dtype="B"), col_size)

    def array_to_img(
        self, data, col_size=COL_SIZE, return_array=False, auto_resize_col_size=True
    ):
        dsize = len(data)
        if auto_resize_col_size:
            if dsize < (col_size * col_size):
                # resize col_size to form a square image
                col_size = int(np.sqrt(dsize))

        rows = int(dsize / col_size)
        rem = dsize % col_size
        # print((dsize, col_size, rem))
        if rem != 0:
            a = np.append(data, np.zeros(col_size - rem, dtype="B")).reshape(
                (rows + 1, col_size)
            )
        else:
            a = data.reshape((rows, col_size))

        if return_array:
            return a

        im = Image.fromarray(a)
        return im

    def binary_to_img(
        self, data, col_size=COL_SIZE, return_array=False, auto_resize_col_size=True
    ):
        return self.array_to_img(
            np.frombuffer(data, dtype="B"), col_size, return_array, auto_resize_col_size
        )

    def feats_from_binary(self, data):
        import leargist  # lazy loading

        im = self.binary_to_img(data)
        im = im.resize(FEATURE_SHAPE, resample=Image.BICUBIC)
        des = leargist.color_gist(im)
        des = des[0:FEATURE_SIZE]
        return des

    def feats_from_binary_list(self, data_list, weights, resample=Image.NEAREST):
        import leargist  # lazy loading

        N = len(data_list)
        assert N == len(weights)
        assert sum(weights) == 1.0
        w, h = FEATURE_SHAPE
        shapes = [(w, int(float(x) * h)) for x in weights]
        # print(shapes)

        ims = []
        for i, data in enumerate(data_list):
            if type(data) == str:
                data = bytes(data, "utf8")
            w, h = shapes[i]
            # single pixel hight img
            im = Image.frombytes("L", (len(data), 1), data)
            im = im.resize((w * h, 1), resample=resample)
            im = np.asarray(im).reshape((h, w))
            ims.append(im)

            # plt.imshow(im,cmap='gray',vmin=0,vmax=255)
            # plt.show()

        im = np.vstack(ims)

        # plt.imshow(im,cmap='gray',vmin=0,vmax=255)
        # plt.show()

        des = leargist.bw_gist(im)
        des = des[0:FEATURE_SIZE]
        return des

    def show(self, img, dpi=72):
        if type(img) == np.ndarray:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, c = img.shape
        else:
            h, w = img.size

        fh = h / dpi
        fw = w / dpi

        if fh <= 0:
            fh = 1
        if fw <= 0:
            fw = 1

        # plt.figure(figsize=(fh, fw))
        # plt.imshow(img, 'viridis')

    def dist(self, fn1, fn2):
        h1, l1, f1 = self.feats_from_file(fn1)
        h2, l2, f2 = self.feats_from_file(fn2)
        return np.linalg.norm(f1 - f2)

    def dist_buff(self, d1, d2):
        h1, l1, f1 = self.feats_from_buff(d1)
        h2, l2, f2 = self.feats_from_buff(d2)
        return np.linalg.norm(f1 - f2)

    def _debug_feats_from_file(self, fn):
        with open(fn, "rb") as f:
            data = f.read()
            self._debug_feats_from_buff(data, fn)

    def _debug_feats_from_buff(self, data, fn="<buffer>"):
        import leargist  # lazy loading

        im = self.binary_to_img(data)
        dpi = 30

        self.show(im, dpi)
        # plt.title("binary data (%d bytes)\n%s"%(len(data),os.path.basename(fn)))

        im = im.resize(FEATURE_SHAPE)

        self.show(im, dpi)
        # plt.title("resize (shape:%s)"%(str(FEATURE_SHAPE)))

        des = leargist.color_gist(im)[0:FEATURE_SIZE]
        im = self.array_to_img(des, 32)

        self.show(im, 5)
        # plt.title("features (len:%d)"%(FEATURE_SIZE))
        # plt.imshow(im)
