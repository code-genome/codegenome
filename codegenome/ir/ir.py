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

# Set environment variables SG_IR_OPTIMIZE_EXTERNAL and LLVM_OPT_PATH to run external IR optimizer.
# E.g. with:
# export SG_IR_OPTIMIZE_EXTERNAL=1
# export LLVM_OPT_PATH=/usr/bin/opt-8

import collections
import datetime
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import sys
import tempfile
import time

import llvmlite.binding as llvm

from .._defaults import UNIVERSAL_FUNC_NAME
from .._file_format import _CANON_FILE_VERSION_

logger = logging.getLogger("codegenome.ir")


class SigmalEx(object):
    def normalize_func(self, f):
        pass


# challenges
# - type names are immutable (should not be part of genome as type-name can be arbitrary. Hope retdec has some consistencies  )
# - recursive identifier dependencies
# - registers can not be renamed (?)


class Function(object):
    def __init__(self, obj, parent, dbg=False):
        """
        Object for referencing an LLVM IR function.
        """

        self._obj = obj
        self._parent = parent
        self.name = str(obj.name)

        # explicitly preserver order of the items
        self.args = collections.OrderedDict()
        self.blocks = collections.OrderedDict()
        self.insts = collections.OrderedDict()
        self.types = collections.OrderedDict()
        self.attrs = []

        st = time.time()

        self.opnames = set()
        self.gvars = set()
        self.dbg = dbg
        self.done_set = set()

        # recursive call!
        self.add_types(obj.type)

        self._init(obj, parent, dbg)

    def _init(self, obj, parent, dbg):
        """
        Populate all the components of the function.
        """
        st = time.time()
        for a in obj.attributes:
            self.attrs.append(a)

        for a in obj.arguments:
            self.args[a.name] = a
            self.add_types(a.type)

        idx = 0
        for b in obj.blocks:
            self.blocks[b.name] = b

            for i in b.instructions:
                if i.name != "":
                    self.insts[i.name] = i
                elif str(i.type) != "void":
                    # not a function call
                    i.name = "tv" + str(idx)
                    idx += 1
                    self.insts[i.name] = i

                self.add_types(i.type)

                # inspect instruction ops
                ops = [x for x in i.operands]
                for op in ops:
                    if op.name != "":
                        if not op.is_global:  # TODO does not always work
                            self.opnames.add(op.name)

                    self.add_with_global_deps(op)

        self.externs = self.opnames - set(
            list(self.args.keys())
            + list(self.blocks.keys())
            + list(self.insts.keys())
            + [self.name]
        )
        self.externs = self.externs.union(self.gvars) - set([self.name])
        if dbg:
            print(self.externs)

        st = time.time() - st
        self.stat = {"init": st}

    def __str__(self):
        raise Exception("str Function not supported.")

    @property
    def name(self):
        return self._obj.name

    @name.setter
    def name(self, x):
        self._obj.name = x

    def add_with_global_deps(self, obj, depth=0):
        """
        Recursively add referenced variables. Only adds global variables or types.
        """
        if obj not in self.done_set:
            self.done_set.add(obj)
        else:
            return
        if isinstance(obj, llvm.ValueRef):
            # value
            ids = self._parent.get_identifiers(obj)
            for x in ids:
                # only handle if it's a global variable or a type object

                xn = x[1:]
                if x[:1] == "@":
                    # global variable id
                    if xn not in self.gvars:
                        self.gvars.add(xn)

                        # try extracting additional references
                        gv = self._parent.get_gv_by_name(xn)
                        if gv is not None:
                            if gv != obj:
                                self.add_with_global_deps(gv, depth + 1)
                        else:
                            # function may not have been parsed yet! so pass
                            # print("Warning: undefined global var! %s, %s (%s)"%(gv, xn, str(x)))
                            pass

                else:
                    xnt = self._parent.get_gtype_by_name(xn)
                    if xnt is not None:
                        # add type
                        self.add_types(xnt)

    def add_types(self, tp):
        """
        Recursively add type definitions.
        """
        while tp.is_pointer:
            tp = tp.element_type

        ids = [x[1:] for x in self._parent.get_identifiers(tp)]
        for x in ids:
            if x not in self.types:
                if x in self._parent.gtypes:
                    _tp = self._parent.gtypes[x]
                    self.types[x] = _tp
                    if tp != _tp:
                        self.add_types(_tp)
                else:
                    raise Exception("undefined type! " + str(x))

    def get_ll(self):
        """
        Main method for generating the final text for ll file.
        """
        _name = self._obj.name
        self._obj.name = UNIVERSAL_FUNC_NAME
        i = 1
        for a in self.args.values():
            a.name = "a%d" % (i)
            i += 1
        i = 1
        for b in self.blocks.values():
            b.name = "b%d" % (i)
            i += 1

        i = 1
        for b in self.insts.values():
            b.name = "v%d" % (i)
            i += 1

        i = 1
        for b in self.types.values():
            b.name = "t%d" % (i)
            i += 1

        # --- rename externs

        externs = []
        # sort externs
        for ex in self.externs:
            obj = self._parent.get_gv_by_name(ex)
            if obj is not None:
                if isinstance(obj, Function):
                    ln = self._parent.str_external_funcs(obj._obj)
                else:
                    # global var
                    ln = self._parent.str_globals(obj)
                    ln = ln.split("=")
                    ln = "=".join(ln[1:]).strip()
                externs.append([ln, ex, obj])

        externs.sort()

        i = 1
        j = 1
        k = 1
        for _, ex, obj in externs:

            if obj is not None:
                if isinstance(obj, Function):
                    # TODO intelligent rename. e.g.; don't rename *printf*
                    # TODO rename function arg names as well
                    # print "processing "+ex+str(obj._obj)
                    # do not rename external
                    if not obj._obj.is_declaration:
                        obj.name = "gf%d" % i
                        i += 1
                    else:
                        pass
                        # obj.name = 'gef%d'%k
                        # k+=1
                else:
                    # global var
                    try:
                        obj.name = "gv%d" % j
                    except Exception as e:
                        print(_name, "Error ", e, obj)

                    j += 1
                # externs[ex] = obj

        #             if self.dbg:
        #                 print '-------', ex, ':', obj
        #                 print str(self._obj)
        #                 return

        # ------------------
        # types

        tps = "\n".join([str(x) for x in self.types.values()])

        # -----------------
        # globals

        # append externs (hack)
        gefs = gfs = gvs = ""

        for _, ex, obj in externs:
            if obj is not None:
                if isinstance(obj, Function):
                    ln = self._parent.str_external_funcs(obj._obj)
                    if not obj._obj.is_declaration:
                        gfs += "\n" + ln
                    else:
                        gefs += "\n" + ln
                else:
                    # global var
                    ln = self._parent.str_globals(obj)
                    gvs += "\n" + ln

        # combine
        gvs = "\n".join([gefs, gfs, gvs])

        # ------------------
        # generate main code

        body = str(self._obj)
        body = self._parent.str_rm_meta(body)
        # ------------------

        # reset externs
        for _, ex, obj in externs:
            if obj is not None:
                obj.name = ex

        for k, v in self.args.items():
            v.name = k
        for k, v in self.blocks.items():
            v.name = k
        for k, v in self.insts.items():
            v.name = k
        for k, v in self.types.items():
            v.name = k
        self._obj.name = _name

        return "\n".join([tps, gvs, body])

    def get_bc(self):
        m = llvm.parse_assembly(self.get_ll())
        return m.as_bitcode()


class IRBinary(object):
    def __init__(self, data, ll=False, opt_level=3, bin_id=""):
        global logger
        self.logger = logger
        self._re_p = re.compile(r"[%@]\"?[-a-zA-Z$._0-9][-a-zA-Z$._0-9@]*\"?")
        self._re_gv = re.compile(r"^[%@]\"?[-a-zA-Z$._0-9][-a-zA-Z$._0-9@]*\"?")
        self._re_meta = re.compile(", *!.+\n")
        self._bin_id = bin_id
        self._opt_level = opt_level

        st = time.time()
        if ll:
            self._m = llvm.parse_assembly(data)
        else:
            self._m = llvm.parse_bitcode(data)
        st = time.time() - st
        self.stat = {"parse": st}
        self.logger.info("stat:" + json.dumps(self.stat))

        self.fs = collections.OrderedDict()
        self.fs_objs = {}
        self.gv = {}
        self.gtypes = {}
        self._ids = {}

        self._init()

    def _init(self):
        st = time.time()
        if self._opt_level > 0:
            if os.environ.get("SG_IR_OPTIMIZE_EXTERNAL") is not None:
                self._optimize_external(self._opt_level)
            else:
                self._optimize(self._opt_level)
        st = time.time() - st
        self.stat["optimize"] = st
        self.logger.info("stat:" + json.dumps(self.stat))

        st = time.time()

        for g in self._m.global_variables:
            if g.name == "":
                gid = self.get_gv_identifier(g)
                for gn in gid:
                    self.gv[gn[1:]] = g
            else:
                self.gv[g.name] = g

        i = 0
        for tp in self._m.struct_types:
            if tp.name != "":
                self.gtypes[tp.name] = tp
            else:
                tp.name = "_ANON_TYPE_%d" % (i)
                i += 1
                self.gtypes[tp.name] = tp

        self.stat["globals_init"] = time.time() - st
        st = time.time()

        # function llvmobj_dict
        for f in self._m.functions:
            self.fs_objs[f.name] = f

        self.logger.info("Creating function objects.")
        for f in self._m.functions:
            t1 = time.time()
            self.fs[f.name] = Function(f, self)
            self.logger.info(f"{f.name} took {time.time()-t1}secs.")
        st = time.time() - st
        self.stat["func_init"] = st

        st = time.time()
        self._collision_correction(self.fs)
        self._collision_correction(self.gv)
        st = time.time() - st
        self.stat["collision_correction"] = st

        self.logger.info("stat:" + json.dumps(self.stat))

    def _optimize_external(self, opt_level):
        opt_path = os.environ.get("LLVM_OPT_PATH", "opt-8")

        tmp = tempfile.NamedTemporaryFile("w+b", delete=True)
        output_filename = tmp.name + ".bc.tmp"

        try:
            tmp.write(self._m.as_bitcode())
            tmp.flush()
            self.logger.debug(f"created a tmp bc file{tmp.name}")
            args = [opt_path, f"--O{opt_level}", "-o", output_filename, tmp.name]
            self.logger.debug(f"Running {' '.join(args)}")
            ret = subprocess.run(args)
            if ret.returncode != 0:
                err = (
                    f"optimization step failed while running command: {' '.join(args)} "
                )
                raise Exception(err)

            self._m = llvm.parse_bitcode(open(output_filename, "rb").read())
            os.remove(output_filename)
            self.logger.debug("optimization completed.")
        except Exception as err:
            self.logger.error(err)
        finally:
            tmp.close()
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            if os.path.exists(output_filename):
                os.remove(output_filename)
        return self._m

    def _optimize(self, opt_level):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        self._m.verify()

        with llvm.create_module_pass_manager() as pm:
            with llvm.create_pass_manager_builder() as pmb:
                pmb.opt_level = opt_level
                pmb.populate(pm)
            pm.run(self._m)

    def _collision_correction(self, d):
        if UNIVERSAL_FUNC_NAME in d:
            rname = "_x_"
            while rname in d:
                rname = "".join(random.sample(string.letters, 8))
            tfs = d.pop(UNIVERSAL_FUNC_NAME)
            tfs.name = rname
            d[rname] = tfs

    def get_identifiers(self, obj):
        """
        Returns a list of all object identifies (function names,
        variable names, type names etc.) referenced by obj.
        Builds self._ids{} map on demand to avoid redundant processing.
        """
        out = self._ids.get(obj)
        if out is None:
            s, obj_str = self.str_external_funcs(obj, return_obj_str=True)
            if s == "":
                # not a function
                s = obj_str
            out = [x.replace('"', "") for x in self._re_p.findall(s)]
            self._ids[obj] = out
        return out

    def get_gv_identifier(self, obj):
        return [x.replace('"', "") for x in self._re_gv.findall(str(obj))]

    def str_globals(self, g):
        return str(g)

    def str_external_funcs(self, obj, return_obj_str=False):
        """
        Returns function declaration line if the obj is a function
        otherwise an empty string.
        """
        obj_str = str(obj)  # str(obj) is an expensive call!
        out_ln = ""
        for ln in obj_str.split("\n"):
            if ln.startswith("declare"):
                out_ln = ln
                break
            elif ln.startswith("define"):
                ln = ln.strip()
                ln = "declare" + ln[6:-1]
                out_ln = ln
                break
        # ln = self.str_globals(ln)
        if return_obj_str:
            return out_ln, obj_str
        return out_ln

    def str_rm_meta(self, s):
        return self._re_meta.sub("\n", s)

    def get_gtype_by_name(self, name):
        if name in self.gtypes:
            return self.gtypes[name]
        return None

    def get_gv_by_name(self, name):
        out = self.gv.get(name)
        if out is None:
            out = self.fs.get(name)
        return out

    def p_inst(self, x):
        print(str(x).strip())
        print("opcode:" + x.opcode)
        print("operands:")
        for op in x.operands:
            print("type:%s, name:%s, value:%s" % (op.type, op.name, str(op)))

    def serialize(self, statf=None):
        fns = []
        i = 0
        tot = 0
        err = 0
        st = time.time()

        for k, v in self.fs.items():
            # skip declare
            if v._obj.is_declaration:
                continue
            i += 1
            try:
                s = time.time()
                bc = v.get_bc()
                s = time.time() - s
                tot += 1

                gid = hashlib.sha256(bc).hexdigest()
                # TODO get file_offset
                bc_size = len(bc)
                file_offset = 0
                meta = (bc_size, file_offset)

                # format (gene_id, func_name, bitcode, meta)
                fns.append((gid, k, bc, meta))

                if statf:
                    txt = (
                        '{"type": "OK", "i": %d, "ts": "%s", "func": "%s", "time": %f, "size": %d}'
                        % (i, str(datetime.datetime.now()), k, s, len(bc))
                    )
                    statf.write(txt + "\n")
            except Exception as e:
                err += 1
                txt = (
                    '{"type": "ERR", "i": %d, "ts": "%s", "func": "%s", "e": "%s", "bin_id": "%s"}'
                    % (i, str(datetime.datetime.now()), k, str(e), self._bin_id)
                )
                self.logger.error(txt)
                if statf:
                    statf.write(txt + "\n")
                else:
                    pass
        st = time.time() - st
        if statf:
            stat = {
                "type": "stat",
                "bin_id": self._bin_id,
                "total": tot,
                "errors": err,
                "func_count": len(self.fs),
                "time": st,
            }
            for k, v in self.stat.items():
                stat[k] = v
            statf.write(json.dumps(stat) + "\n")

        return fns
