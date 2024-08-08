#!/bin/bash
# install modified llvmlite
# Tested on Ubuntu 22.04

cp llvmlite-settypename.patch llvm-gcc-fix.patch /tmp/

apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip python-is-python3 \
    git g++ make cmake vim unzip libcurl4-openssl-dev wget  ;\

TMP=/tmp/tmp_src
mkdir -p $TMP
wget -O $TMP/llvm.tar.gz https://github.com/llvm/llvm-project/archive/llvmorg-8.0.1.tar.gz ;\
cd $TMP && tar xf $TMP/llvm.tar.gz; \
cd $TMP && git clone https://github.com/numba/llvmlite.git && \
cd llvmlite && \
git checkout aa11b129c0b55973067422397821ae6d44fa5e70 && \
git apply --whitespace=nowarn /tmp/llvmlite-settypename.patch && \
mv $TMP/llvmlite/conda-recipes/twine_cfg_undefined_behavior.patch $TMP/llvmlite/conda-recipes/twine_cfg_undefined_behavior.patch.bak;\
cd $TMP/llvm-project-llvmorg-8.0.1/llvm && \
for f in $TMP/llvmlite/conda-recipes/*.patch; do  patch -fN -p1 -i $f; done ;\
cd $TMP/llvm-project-llvmorg-8.0.1/ && \
patch -fN -p1 -i /tmp/llvm-gcc-fix.patch ;\

# fix recipes --------
LLVMLITESRC=$TMP/llvmlite

BUILD=$LLVMLITESRC/conda-recipes/llvmdev/build.sh

if grep -q '^RECIPE_DIR' $BUILD; then
   true;
else
ex $BUILD <<EX1
/^# SVML tests on x86_64/
a
RECIPE_DIR=$LLVMLITESRC/conda-recipes/llvmdev
.
wq!
EX1
fi
# fix --------

cd $TMP/llvm-project-llvmorg-8.0.1/llvm && \
chmod +x $TMP/llvmlite/conda-recipes/llvmdev/build.sh && \
PREFIX=/opt/llvm CPU_COUNT=12 CMAKE_BUILD_PARALLEL_LEVEL=2 $TMP/llvmlite/conda-recipes/llvmdev/build.sh ;\
cd $TMP/llvmlite && LLVM_CONFIG=/opt/llvm/bin/llvm-config python3 setup.py install

