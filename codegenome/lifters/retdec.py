import logging
import os
import shutil
import subprocess
import tempfile
import time

from .base import CGLifterBase

logger = logging.getLogger("codegenome.lifter.retdec")

DEFAULT_RETDEC_PATH = "/opt/retdec"


class CGRetdec(CGLifterBase):
    def __init__(self, retdec_path=None, logger=logger):
        self.retdec_path = (
            os.environ.get("RETDEC_PATH", DEFAULT_RETDEC_PATH)
            if retdec_path is None
            else retdec_path
        )
        self.logger = logger

    def process_file(
        self,
        file_path,
        output_dir=None,
        output_fname=None,
        retdec_logfile_path=None,
        retdec_path=None,
        keep_aux_files=False,
        overwrite=True,
    ):
        self.logger.debug(
            f"process_file. {file_path, output_dir, retdec_logfile_path, retdec_path}"
        )
        final_output_path = None
        fn = os.path.basename(file_path)

        if output_dir is None:
            output_dir = os.path.dirname(file_path)
        if output_dir == "":
            output_dir = "./"

        final_output_dir = output_dir
        output_dir = tempfile.mkdtemp(prefix="cgtmp__", dir="/tmp/")

        try:

            if output_fname is None:
                output_fname = os.path.basename(file_path)
            else:
                output_fname = os.path.basename(output_fname)

            if retdec_path is None:
                retdec_path = self.retdec_path

            if retdec_logfile_path is None:
                retdec_logfile_path = os.path.join(
                    output_dir, output_fname + ".retdec.log"
                )

            args = [
                os.path.join(retdec_path, "bin/retdec-decompiler"),
                "-o",
                os.path.join(output_dir, output_fname),
                file_path,
            ]

            self.logger.info(f"running {args}")

            t = time.time()
            with open(retdec_logfile_path, "w") as fout:
                ret = subprocess.call(args, stdout=fout, stderr=fout)

            if not keep_aux_files:
                # output debug logs
                with open(retdec_logfile_path, "r") as f:
                    logger.debug(f"RETDEC_LOG:\n{f.read()}\n")

            if ret == 0:
                logger.debug(
                    f"RETDEC_OK. Time: {time.time()-t} secs. {[file_path, '->', output_dir]}"
                )

            else:
                logger.debug(
                    f"RETDEC_ERROR. Time: {time.time()-t} secs. {[file_path, '->', output_dir]}"
                )
            # move

            for fn in os.listdir(output_dir):
                ext = os.path.splitext(fn)[-1].lower()

                if not keep_aux_files:
                    if ext != ".bc":
                        continue
                if ext in [".bc", ".dsm", ".ll", ".log"]:
                    src = os.path.join(output_dir, fn)

                    if os.path.isfile(src):
                        dst = os.path.join(final_output_dir, fn)
                        if fn.endswith(".bc"):
                            final_output_path = dst
                        if os.path.exists(dst) and (not overwrite):
                            continue
                        # copy
                        shutil.copy2(src, dst)
                        os.remove(src)

        finally:
            shutil.rmtree(output_dir)
        return final_output_path
