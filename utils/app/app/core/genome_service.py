import binascii
import datetime
import hashlib
import json
import logging
import os
import shutil
import sys
import threading
import time
import traceback
from textwrap import indent

import numpy as np
from sqlitedict import SqliteDict

import codegenome as cg
import codegenome._defaults as defaults

from ..defaults import *
from .schema import KGNodeID

CG_CACHE_DIR = defaults.CG_CACHE_DIR

if not os.path.exists(CG_CACHE_DIR):
    os.makedirs(CG_CACHE_DIR)

CG_GENE_DIR = os.path.expanduser(
    os.environ.get("CG_GENE_DIR", os.path.join(CG_CACHE_DIR, "local.kg"))
)
CG_DOCKER_IMAGE_NAME = os.environ.get("CG_DOCKER_IMAGE_NAME", "cg-worker")


DEFAULT_API_CACHE_TTL_SECS = -1  # negative value, never expire
# node age check logic for cache invalidation: always refresh cache for young nodes (default: 1hr old node).
DEFAULT_API_CACHE_NODE_AGE_THRESHOLD_SECS = 60 * 60
DEFAULT_RECORD_API_STATS = 1  # record api stats in cache db
DEFAULT_API_COMPUTE_TIMEOUT_SECS = 24 * 60 * 60  # 1 day
DEFAULT_KEEP_AUX_FILES = 0

API_STATE_SUCCESS = "Success"
API_STATE_RESULT_NOT_READY = "ResultNotReady"
API_STATE_EMPTY_RESULT = "ResultEmpty"
API_STATE_ERROR = "Error"


log = logging.getLogger("codegenome.rest.kg_service")


def crc32(obj):
    return str(
        binascii.crc32(json.dumps(obj, default=lambda x: str(x)).encode("utf-8"))
    )


def is_exec(obj):
    # TODO implement proper test
    return True


class JobDBDict(SqliteDict):
    def __init__(self, *args, **kwargs):
        self._lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        with self._lock:
            super().__setitem__(key, value)
            super().commit()

    def __delitem__(self, key):
        with self._lock:
            super().__delitem__(key)
            super().commit()


class GenomeService(object):
    def __init__(self, config={}):
        self.start_ts = time.time()
        self.config = config
        self.config.setdefault("cache_dir", CG_CACHE_DIR)
        self.config.setdefault("gene_dir", CG_GENE_DIR)

        self.config.setdefault(
            "keep_aux_files",
            int(os.environ.get("CG_KEEP_AUX_FILES", DEFAULT_KEEP_AUX_FILES)),
        )
        self._disable_index_cache = int(config.get("disable_index_cache", 0))
        self.api_cache_ttl = self.config.get(
            "api_cache_ttl_secs",
            int(os.environ.get("API_CACHE_TTL_SECS", DEFAULT_API_CACHE_TTL_SECS)),
        )
        self.record_stats = self.config.get(
            "api_record_stats",
            int(os.environ.get("RECORD_API_STATS", DEFAULT_RECORD_API_STATS)),
        )
        self.api_compute_timeout = self.config.get(
            "api_compute_timeout_secs",
            int(
                os.environ.get(
                    "API_COMPUTE_TIMEOUT_SECS", DEFAULT_API_COMPUTE_TIMEOUT_SECS
                )
            ),
        )
        self.api_cache_node_age_threshold = self.config.get(
            "api_cache_node_age_threshold",
            int(
                os.environ.get(
                    "API_CACHE_NODE_AGE_THRESHOLD_SECS",
                    DEFAULT_API_CACHE_NODE_AGE_THRESHOLD_SECS,
                )
            ),
        )

        self.kg = cg.GenomeKG(db_dir=config.get("gene_dir"))
        self._jobs = JobDBDict(
            os.path.join(self.config.get("cache_dir"), "jobs.sqlite")
        )
        self._threads = {}

        self._update_status()

    def _update_status(self):
        updates = {}
        for k, v in self._jobs.items():
            if (v.get("end_ts") is None) and (k not in self._threads):
                v["status"] = "error"
                updates[k] = v
        for k, v in updates.items():
            self._jobs[k] = v

    def status(self):
        incomplete = []
        for k, v in self._jobs.items():
            if "end_ts" not in v:
                incomplete.append(
                    {
                        "job_id": str(k),
                        "job": v,
                        "duration_secs": int(time.time() - v.get("start_ts")),
                    }
                )

        return {
            "start_time": str(datetime.datetime.fromtimestamp(int(self.start_ts))),
            "uptime_secs": int(time.time() - self.start_ts),
            "total_genes": len(self.kg.gene_ids),
            "total_binaries": len(self.kg.bins),
            "gene_version": self.kg.gene_version,
            "jobs": {"total": len(self._jobs), "incomplete": incomplete},
        }

    def make_fileid(self, data):
        h = hashlib.sha256()
        h.update(data)
        return h.digest().hex()

    def _add_file(self, file_id, file_path, cleanup=True):
        log.debug(f"add_file(file_path={file_path})")
        qkey = ["add_file", file_path, cleanup]
        try:
            fid = self.kg.add_file(
                file_path=file_path, keep_aux_files=self.config.get("keep_aux_files")
            )
            if fid is None:
                out = {
                    "status": API_STATE_ERROR,
                    "file_id": file_id,
                    "status_msg": "File processing failed.",
                }
            elif fid != file_id:
                out = {
                    "status": API_STATE_ERROR,
                    "file_id": file_id,
                    "status_msg": f"file id mismatch {fid} != {file_id}",
                }
            else:
                out = {
                    "status": API_STATE_SUCCESS,
                    "file_id": file_id,
                    "ret_status": "new_file",
                }
            self._api_thread_final(file_id, qkey, out)
            if cleanup:
                tdir = os.path.dirname(file_path)
                if tdir.startswith(TMP_DIR_PREFIX):
                    log.debug(f"removing directory {tdir}")
                    shutil.rmtree(tdir)

            return out
        except Exception as err:
            log.error(
                f"Exception at add_file({file_path}). {err}. {repr(traceback.format_exc())}."
            )
            out = {"status": API_STATE_ERROR, "status_msg": str(err)}
            self._api_thread_final(file_id, qkey, out)
            return out

    def api_add_file(self, file_path):
        log.debug(f"api_add_file({file_path})")

        with open(file_path, "rb") as f:
            file_id = self.make_fileid(f.read())

        n = self.kg.get_node(file_id)

        if n:
            return {
                "status": API_STATE_SUCCESS,
                "file_id": file_id,
                "ret_status": "existing_file",
            }

        qkey = ["add_file", file_path, True]

        ret = self._api_thread_enter(file_id, qkey, target=self._add_file)
        ret["file_id"] = file_id
        return ret

    def _update_output(
        self, fnode, results, fnode2=None, filename=True, filetypes=True
    ):
        # filename
        def _update_node_filename(n):
            if type(n) == dict:
                for k in ["name", "metadata.name"]:
                    fn = n.get(k)
                    if fn:
                        n[k] = os.path.basename(fn)

        # filetypes
        def _update_node_filetypes(n):
            if type(n) == dict:
                ftypes = []
                dels = []
                for k in n.keys():
                    if k.startswith("filetype."):
                        ftypes.append(k.split(".")[1])
                        dels.append(k)
                for k in dels:
                    n.pop(k)

                n["filetypes"] = ftypes

        if filename:
            _update_node_filename(fnode)
            _update_node_filename(fnode2)
        if filetypes:
            _update_node_filetypes(fnode)
            _update_node_filetypes(fnode2)

    def _prep_output(self, output, output_detail):
        if output_detail == "simple":
            for r in output.get("results", []):
                if type(r) == dict:
                    r.setdefault(
                        "sha256",
                        r.get("object", {}).get(
                            "sha256", r.get("id", "").split(":")[-1]
                        ),
                    )
                    if "object" in r:
                        r.pop("object")

        return output

    def _cleanup_jobs(self, job_id):
        # TODO implement
        pass

    def check_job(self, job_id):
        job = self._jobs.get(job_id)
        if job:
            ret = job.get("result")
            if ret:
                # Clean job
                # self._jobs.pop(job_id)
                return ret
            ret = {
                "status": API_STATE_RESULT_NOT_READY,
                "start_ts": job.get("start_ts"),
                "job_id": job_id,
            }
            file_id = job.get("file_id")
            if file_id:
                ret["file_id"] = file_id

            return ret

        return {"status": API_STATE_ERROR, "status_msg": f"Job {job_id} not found"}

    def del_job(self, job_id):
        if job_id in self._jobs:
            log.warning(f"Deleting job({job_id}).")
            self._jobs.pop(job_id)
            return {"status": API_STATE_SUCCESS}

        return {"status": API_STATE_ERROR, "status_msg": f"Job {job_id} not found"}

    def delete_file(self, file_id):
        log.warning(f"Deleting file({file_id}).")
        # try removing jobs
        dels = []
        for k, v in self._jobs.items():
            if file_id == v.get("result", {}).get("file_id"):
                dels.append(k)
        for k in dels:
            self._jobs.pop(k)

        ret = self.kg.delete_file(file_id=file_id)
        if ret:
            return {"status": API_STATE_SUCCESS}

        return {
            "status": API_STATE_ERROR,
            "status_msg": f"Error deleting file {file_id}.",
        }

    def _create_job_id(self, obj_id, qkey):
        if qkey[0] == "add_file":
            # file path will be random
            return crc32([obj_id])
        return crc32([obj_id, qkey])

    def _api_thread_enter(self, obj_id, qkey, target):
        if not callable(target):
            raise Exception(f"target [{target}] argument must be callable.")
        try:
            # check if running
            job_id = self._create_job_id(obj_id, qkey)
            job = self._jobs.get(job_id)
            prev_out = None
            if job:
                ret = job.get("result")
                if ret:
                    self._cleanup_jobs(job_id)
                    dt = time.time() - job["end_ts"]

                    cache_ok = False
                    if self.api_cache_ttl < 0:
                        # always use cache
                        cache_ok = True
                    elif dt < self.api_cache_ttl:
                        cache_ok = True
                    # always return last result if available, but trigger new update if needed
                    prev_out = ret
                    if type(prev_out) == dict and prev_out.get("status") in [
                        API_STATE_ERROR,
                        API_STATE_EMPTY_RESULT,
                    ]:
                        cache_ok = False

                    if cache_ok:
                        log.info(f"Returning cached result for {(obj_id,qkey)}")
                        return ret
                else:
                    dt = time.time() - job.get("start_ts")
                    # is thread live?
                    running = False
                    try:
                        if job_id in self._threads and self._threads[job_id].is_alive():
                            running = True
                    except:
                        pass
                    if running:
                        if dt < self.api_compute_timeout:
                            # still computing
                            return {
                                "status": API_STATE_RESULT_NOT_READY,
                                "start_ts": job["start_ts"],
                                "job_id": job_id,
                            }
                        else:
                            # you can not kill the thread
                            # signal to stop, thread function need to cooperate
                            job["stop"] = True
                            job["status"] = "stopping"
                            if job_id in self._threads:
                                self._threads.pop(job_id)
                    else:
                        # job crashed
                        job["status"] = "error"

            try:
                args = [obj_id] + qkey[1:]
                th = threading.Thread(target=target, args=args)
                th.start()
                sts = int(time.time())
                self._threads[job_id] = th
                self._jobs[job_id] = {"start_ts": sts, "status": "running"}
                if prev_out:
                    return prev_out
                else:
                    return {
                        "status": API_STATE_RESULT_NOT_READY,
                        "start_ts": sts,
                        "job_id": job_id,
                    }
            except Exception as err:
                log.error(
                    f"Exception creating job thread. {err} Using blocking call for {target.__name__}{(obj_id, qkey)})"
                )
                return target(*args)

        except Exception as err:
            log.error(
                f"Exception at _api_thread_enter({(obj_id, qkey, target.__name__)}). {err}. {repr(traceback.format_exc())}"
            )

    def _api_thread_final(self, obj_id, qkey, out):
        try:
            job_id = self._create_job_id(obj_id, qkey)
            job = self._jobs.get(job_id, {})
            job["result"] = out
            job["end_ts"] = time.time()
            job["status"] = "completed"
            self._jobs[job_id] = job
            if job_id in self._threads:
                self._threads.pop(job_id)
        except Exception as err:
            log.error(
                f"Exception at _api_thread_final({(obj_id,qkey)}). {err}. {repr(traceback.format_exc())}"
            )

    def api_files_compare_kg(
        self,
        file_id1,
        file_id2,
        method=DEFAULT_COMPARE_METHOD,
        output_detail=DEFAULT_OUTPUT_DETAIL,
    ):
        """
        Main api exposed to the external UI rest-api.
        """
        log.debug(
            f"api_files_compare_kg(file_id1={file_id1}, file_id2={file_id2}, method={method}, output_detail={output_detail}"
        )
        file_id1 = KGNodeID.file_id(file_hash=file_id1)
        file_id2 = KGNodeID.file_id(file_hash=file_id2)

        obj_id = file_id1
        qkey = ["files_compare_kg", file_id2, method, output_detail]

        # test direct
        return self._files_compare_kg(obj_id, file_id2, method, output_detail)

        return self._api_thread_enter(obj_id, qkey, target=self._files_compare_kg)

    def _files_compare_kg(
        self, file_id1, file_id2, method="gene_v0", output_detail=DEFAULT_OUTPUT_DETAIL
    ):
        log.debug(
            f"_files_compare_kg(file_id1={file_id1}, file_id2={file_id2}, method={method}, output_detail={output_detail}"
        )
        qkey = ["files_compare_kg", file_id2, method, output_detail]
        try:
            t1 = time.time()
            fnode1 = self.kg.get_node(file_id1)
            fnode2 = self.kg.get_node(file_id2)
            t2 = time.time()
            if fnode1 is None or fnode2 is None:
                msg = ""
                if fnode1 is None:
                    msg = f"file_id:{file_id1} could not be found."
                if fnode2 is None:
                    msg += f"file_id:{file_id2} could not be found."

                out = {
                    "status": API_STATE_EMPTY_RESULT,
                    "results": [],
                    "stats": {"init_prep_time": t2 - t1},
                    "status_msg": msg,
                }
                self._api_thread_final(file_id1, qkey, out)
                log.warn(f"_files_compare_kg returning: {out}")
                return out

            if (not is_exec(fnode1)) or (not is_exec(fnode2)):
                # not a executable file, reset version to gene_v0
                log.info("not a executable file, reset version to gene_v0")
                method = "gene_v0"

            flags = method.split(".")
            version = flags[0]
            if len(flags) > 1:
                method = flags[1]
            else:
                method = DEFAULT_CALCULATION_METHOD

            if version == "gene_v0":
                results, stats = self.file_compare_gene_v0(
                    fnode1, fnode2, output_detail=output_detail
                )
                self._update_output(fnode1, results, fnode2)
            elif version in ["genes_v1_3_0", "genes_v1_3_1"]:
                # TODO pass match/mimatch thrs
                results, stats = self.kg.bindiff(
                    fnode1, fnode2, method=method, output_detail=output_detail
                )
                self._update_output(fnode1, results, fnode2)
            else:
                log.error(
                    f"_files_compare_kg error for fileids: {file_id1, file_id2}, version: {version}, method: {method}"
                )
                results, stats = {
                    "error": f"version: {version}, method: {method} not supported."
                }, {}

            stats["init_prep_time"] = stats.get("init_prep_time", 0.0) + (t2 - t1)
            out = {
                "query": [fnode1, fnode2],
                "results": results,
                "stats": stats,
                "status": API_STATE_SUCCESS,
            }
            if "error" in results:
                out["status"] = API_STATE_ERROR
                out["status_msg"] = results["error"]
            elif len(results) == 0:
                out["status"] = API_STATE_EMPTY_RESULT
            out = self._prep_output(out, output_detail)
            self._api_thread_final(file_id1, qkey, out)
            return out
        except Exception as err:
            log.error(
                f"Exception at _files_compare_kg(). {err}. {repr(traceback.format_exc())}."
            )
            out = {"status": API_STATE_ERROR, "status_msg": str(err)}
            self._api_thread_final(file_id1, qkey, out)
            return out

    def api_get_gene_info(
        self,
        gene_id=None,
        file_id=None,
        function_name=None,
        include_llvm_ir=False,
        include_asm=False,
        include_gene_value=False,
        include_function_names=False,
    ):
        log.debug(
            f"api_get_gene_info({gene_id=}, {file_id=}, {function_name=}, {include_llvm_ir=}, {include_asm=}...)"
        )
        # not threaded
        try:
            out = {"status": API_STATE_ERROR, "status_msg": "Unknown error"}
            if gene_id:
                data = self.kg.get_gene_info(
                    gene_id,
                    function_name=function_name,
                    llvm_ir=include_llvm_ir,
                    include_asm=include_asm,
                    gene_value=include_gene_value,
                    func_names=include_function_names,
                )
                if data:
                    out = {"status": API_STATE_SUCCESS, "data": data}
                else:
                    out = {
                        "status": API_STATE_EMPTY_RESULT,
                        "status_msg": "Can not get gene info",
                    }
            elif (file_id != "") and (function_name != ""):
                gids = self.kg.get_gene_ids(function_name, file_id, include_bin_id=True)
                # in case a binary may have multiple functions with same name, take last
                if len(gids) > 0:
                    gene_id, file_id = gids[-1]
                    data = self.kg.get_gene_info(
                        gene_id,
                        bin_id=file_id,
                        function_name=function_name,
                        llvm_ir=include_llvm_ir,
                        include_asm=include_asm,
                        gene_value=include_gene_value,
                        func_names=include_function_names,
                    )
                    if data:
                        out = {"status": API_STATE_SUCCESS, "data": data}
                    else:
                        out = {
                            "status": API_STATE_EMPTY_RESULT,
                            "status_msg": "Can not get gene info",
                        }
                else:
                    out = {
                        "status": API_STATE_EMPTY_RESULT,
                        "status_msg": f"Function gene not found for {file_id} -> {function_name}.",
                    }
            else:
                out = {
                    "status": API_STATE_ERROR,
                    "status_msg": "Not enough arguments. gene_id or (file_id and function_name) must be passed.",
                }
            return out
        except Exception as err:
            log.error(
                f"Exception at api_get_ir(). {err}. {repr(traceback.format_exc())}."
            )
            out = {"status": API_STATE_ERROR, "status_msg": str(err)}
            return out

    def api_get_node_info(
        self,
        obj_id=None,
        include_genes=False,
        include_llvm_ir=False,
        include_asm=False,
        include_gene_value=False,
        include_function_names=False,
    ):
        # not threaded
        try:
            if obj_id in self.kg.bins:
                data = self.kg.get_node(obj_id)
                if data:
                    if include_genes:
                        data["genes"] = self.kg.bins.get(obj_id, {})
                    out = {"status": API_STATE_SUCCESS, "data": data}
                else:
                    out = {
                        "status": API_STATE_EMPTY_RESULT,
                        "status_msg": f"Object id {obj_id} not found",
                    }

            else:
                data = self.kg.get_gene_info(
                    obj_id,
                    llvm_ir=include_llvm_ir,
                    include_asm=include_asm,
                    gene_value=include_gene_value,
                    func_names=include_function_names,
                )
                if data:
                    out = {"status": API_STATE_SUCCESS, "data": data}
                else:
                    out = {
                        "status": API_STATE_EMPTY_RESULT,
                        "status_msg": f"Object id {obj_id} not found",
                    }
            return out

        except Exception as err:
            log.error(
                f"Exception at api_get_ir(). {err}. {repr(traceback.format_exc())}."
            )
            out = {"status": API_STATE_ERROR, "status_msg": str(err)}
            return out


def read_config():
    config = {
        "gene_dir": CG_GENE_DIR,
        "cache_dir": CG_CACHE_DIR,
        "keep_aux_files": True,
    }
    return config


def create_genome_service():
    config = read_config()
    log.debug(f"read_config(). {config}")
    kgs = GenomeService(config)
    log.debug("GenomeService object created.")
    # do it from api to reduce service startup
    log.debug("updating index.")
    t1 = time.time()
    kgs.kg.load()
    t2 = time.time()
    log.debug("updating index completed.")
    return kgs
