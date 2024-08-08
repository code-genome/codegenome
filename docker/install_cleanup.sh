#cleanup
rm -f /tmp/llvmlite-settypename.patch
rm -rf /tmp/llvm_pass
rm -rf /tmp/tmp_src
rm -rf /tmp/*
apt-get remove -y \
    git g++ make cmake libcurl4-openssl-dev\
    python3-dev
