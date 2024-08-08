import os
import time
import json
import jsonlines
import logging
import datetime
import subprocess
import hashlib

DEFAULT_LLVM_PATH = '/opt/llvm'
logger = logging.getLogger('codegenome.canon')

class IRCanonPassBinary(object):
    def __init__(self, input_data, output='canon.jsonl', bin_id='', pass_file='libcanonicalization-pass.so', llvm_path=None):
        self.input_data = input_data
        self._bin_id = bin_id
        self.llvm_path = os.environ.get(
            'LLVM_PATH', DEFAULT_LLVM_PATH) if llvm_path is None else llvm_path
        self.pass_file = os.path.join(self.llvm_path, 'lib',pass_file )
        self.opt_bin = os.path.join(self.llvm_path, 'bin', 'opt')
        self.output = output
        self.stat = {}
        
    def canon_pass(self):
        args = [self.opt_bin, '--load', self.pass_file,'--canonicalization', '--canon-out',
                 self.output]
        #print(' '.join(args))
        logger.info(f'running {args}')
        try:
            t = time.time()
            ret = subprocess.run(args, input=self.input_data, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
            if ret.returncode == 0:
                    logger.debug(
                        f"CANON_PASS_OK. Time: {time.time()-t} secs. {['->', self.output]}")
                    return self.output

            else:
                logger.debug(
                    f"CANON_PASS_ERROR. Time: {time.time()-t} secs. {['->', self.output]}")
                # move
        except Exception as ex:
            logger.error(f"Exception: {ex}")

        return None
    
    def serialize(self, statf=None):
        import llvmlite.binding as llvm #lazy loading
        fns = []
        i = 0
        tot = 0
        err = 0
        st = time.time()
        
        jsonl = self.canon_pass()
        if jsonl is None:
            return None
        t1 = time.time()
        
        with jsonlines.open(jsonl) as reader:
            for func in reader:
                #code, data, extern, name
                try:
                    if func['extern']:
                        continue
                    s = time.time()
                    #sort data
                    data = func['data'].split('\n')
                    data.sort()
                    data = '\n'.join([x for x in data if x!=''])
                    
                    m = llvm.parse_assembly( data + '\n' + func['code'] )
                    bc =  m.as_bitcode()
                    s = time.time() - s
                    tot += 1

                    gid = hashlib.sha256(bc).hexdigest()
                    # TODO get file_offset
                    bc_size = len(bc)
                    file_offset = 0
                    meta = (bc_size, file_offset)

                    # format (gene_id, func_name, bitcode, meta)
                    func_name = func['name']
                    fns.append((gid, func_name, bc, meta))
                    
                    if statf:
                        txt = '{"type": "OK", "i": %d, "ts": "%s", "func": "%s", "time": %f, "size": %d}' % (
                            i, str(datetime.datetime.now()), func_name, s, len(bc))
                        statf.write(txt + '\n')
                except Exception as e:
                    err += 1
                    txt = '{"type": "ERR", "i": %d, "ts": "%s", "func": "%s", "e": "%s", "bin_id": "%s"}' % (
                        i, str(datetime.datetime.now()), func_name, str(e), self._bin_id)
                    logger.warning(txt)
                    if statf:
                        statf.write(txt + '\n')
                    else:
                        pass
        t2 = time.time()
        if statf:
            stat = {"type": "stat", "bin_id": self._bin_id, "total": tot,
                    "errors": err, "func_count": len(self.fs), 'pass_time': t1-st, 'time': t2-t1}
            for k, v in self.stat.items():
                stat[k] = v
            statf.write(json.dumps(stat) + '\n')
        
        return fns
