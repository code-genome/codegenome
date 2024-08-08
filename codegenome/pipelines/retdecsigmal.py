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

import hashlib
import logging
import os
import pickle
import tempfile
import time
import traceback

from .._file_format import *
from ..genes.sigmal import GENE_TYPE_CONFIG, SigmalGene, prep_data_sigmal2
from ..ir import IRBinary
from ..ir.canon import IRCanonPassBinary
from ..lifters.retdec import CGRetdec
from .base import CGPipeline

DB_GENE_DIR = "genes"
DB_AUX_DIR = ".auxs"
DB_LOG_DIR = ".logs"
DB_INDEX_NAME = "index.gkg"
DEFAULT_GENE_TYPE = "sigmal2"

_logger = logging.getLogger("codegenome.pipelines.RetdecSigmal")


def _retdec_bin_to_ir(
    file_path,
    output_dir=None,
    output_fname=None,
    keep_aux_files=False,
    overwrite=True,
    logger=None,
):
    retdec = CGRetdec(logger=logger)
    bc_path = retdec.process_file(
        file_path,
        output_dir=output_dir,
        output_fname=output_fname,
        keep_aux_files=keep_aux_files,
        overwrite=overwrite,
    )
    with open(bc_path, "rb") as f:
        out = f.read()
    if not keep_aux_files:
        os.remove(bc_path)
    return out


def _ir_to_canon(
    ir_data, output_path=None, opt_level=None, bin_id=None, metadata=None, logger=None
):
    logger = _logger if logger is None else logger
    logger.debug(f"Creating IRBinary")
    irb = IRBinary(ir_data, opt_level=opt_level, bin_id=bin_id)
    canon = prep_canon_file(irb, metadata)

    if output_path:
        with open(output_path, "wb") as cf:
            pickle.dump(canon, cf, protocol=pickle.HIGHEST_PROTOCOL)

    return canon


def _ir_to_canon_using_pass(
    ir_data, output_path=None, bin_id=None, metadata=None, logger=None
):
    logger = _logger if logger is None else logger
    if output_path:
        jsonl_output = os.path.splitext(output_path)[0] + ".canon.jsonl"
    else:
        fd, jsonl_output = tempfile.mkstemp()
        os.close(fd)

    logger.debug(f"Creating IRCanonPassBinary")
    irb = IRCanonPassBinary(ir_data, output=jsonl_output, bin_id=bin_id)
    canon = prep_canon_file(irb, metadata)

    if output_path:
        with open(output_path, "wb") as cf:
            pickle.dump(canon, cf, protocol=pickle.HIGHEST_PROTOCOL)
    return canon


def _canon_to_sigmal_gene(
    canon, output_path=None, gene_type=DEFAULT_GENE_TYPE, logger=None
):
    logger = _logger if logger is None else logger
    logger.debug(f"Creating Sigmal gene")
    t = time.time()
    sg = SigmalGene()
    sg_genes = []
    # find unique genes
    gid_funcs = {}
    for gid, func, bc, meta in canon["funcs"]:
        if gid not in gid_funcs:
            gid_funcs[gid] = [func]
        else:
            gid_funcs[gid].append(func)

    done = set()

    for gid, func, bc, meta in canon["funcs"]:
        if gid not in done:
            raw_gene = sg.from_bitcode(bc, gene_type)
            # format
            gene_data = (gid, gid_funcs[gid], raw_gene, meta)
            sg_genes.append(gene_data)
            done.add(gid)
    t = time.time() - t
    out = prep_gene_file(sg_genes, canon["binid"], canon["file_meta"])
    logger.info("process_canon_to_gene time: %f" % (t))

    if output_path:
        with open(output_path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


class RetdecSigmal(CGPipeline):
    def __init__(self):
        self.logger = logging.getLogger("codegenome.pipelines.RetdecSigmal")

    def process_file(
        self,
        file_path,
        sigmal_gene_type=DEFAULT_GENE_TYPE,
        output_dir=None,
        output_fname=None,
        keep_aux_files=True,
        overwrite=True,
        bin_id=None,
        logger=None,
        return_genes=False,
        keep_gene_file=True,
    ):
        metadata = get_file_meta(file_path)
        if bin_id is None:
            with open(file_path, "rb") as f:
                bin_id = hashlib.sha256(f.read()).hexdigest()
        output_dir = os.path.dirname(file_path) if output_dir is None else output_dir
        output_fname = (
            os.path.basename(file_path) if output_fname is None else output_fname
        )

        logger = self.logger if logger is None else logger

        logger.debug("Lifting to IR.")
        try:
            ir_path = (
                None
                if keep_aux_files is False
                else os.path.join(output_dir, output_fname + ".bc")
            )
            ir_data = _retdec_bin_to_ir(
                file_path,
                output_dir=output_dir,
                output_fname=output_fname,
                keep_aux_files=keep_aux_files,
                overwrite=overwrite,
                logger=logger,
            )
            if not ir_data:
                logger.error("_retdec_bin_to_ir failed.")
                return False
        except Exception as ex:
            logger.error(f"Exception: {ex}. {repr(traceback.format_exc())}")
            return False

        logger.debug("IR to canonical IR")

        try:
            canon_path = (
                None
                if keep_aux_files is False
                else os.path.join(output_dir, output_fname + ".canon")
            )
            canon = _ir_to_canon_using_pass(
                ir_data,
                output_path=canon_path,
                bin_id=bin_id,
                metadata=metadata,
                logger=None,
            )
            if canon is None:
                logger.error("_ir_to_canon failed.")
                return False
        except Exception as ex:
            logger.error(f"Exception: {ex}. {repr(traceback.format_exc())}")
            return False

        logger.debug("Canonical IR to Sigmal gene")

        try:
            gene_path = os.path.join(output_dir, output_fname + ".gene")
            if (keep_aux_files == False) and (keep_gene_file == False):
                gene_path = None

            genes = _canon_to_sigmal_gene(
                canon, output_path=gene_path, gene_type=sigmal_gene_type, logger=logger
            )
            if canon is None:
                logger.error("_ir_to_canon failed.")
                return False
        except Exception as ex:
            logger.error(f"Exception: {ex}. {repr(traceback.format_exc())}")
            return False
        if return_genes:
            return genes
        return True


class RetdecSigmalV1(RetdecSigmal):
    def __init__(self):
        super().__init__()
        self.gene_version = "genes_v0_0_1"

    def process_file(
        self,
        file_path,
        sigmal_gene_type=DEFAULT_GENE_TYPE,
        output_dir=None,
        output_fname=None,
        keep_aux_files=True,
        overwrite=True,
        bin_id=None,
        logger=None,
        return_genes=False,
        keep_gene_file=True,
    ):

        return super().process_file(
            file_path,
            "sigmal2",
            output_dir=output_dir,
            output_fname=output_fname,
            keep_aux_files=keep_aux_files,
            overwrite=overwrite,
            bin_id=bin_id,
            logger=logger,
            return_genes=return_genes,
            keep_gene_file=keep_gene_file,
        )
