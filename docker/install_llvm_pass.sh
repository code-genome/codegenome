TMP=/tmp/llvm_pass
[ ! -e "$TMP" ] && cp -r ../deps/canon_pass "$TMP"/llvm_pass

cd "$TMP" && \
  PATH=/opt/llvm/bin/:$PATH make &&\
  cp build/libcanonicalization-pass.so /opt/llvm/lib/libcanonicalization-pass.so && \
  cd /tmp && \
  rm -rf "$TMP"
