# install retdec 
pushd $(pwd)
PREFIX=/opt/cg/retdec
mkdir -p $PREFIX
VER=$(cat /etc/issue|cut -d' ' -f2)

if [[ $VER < "22" ]]; then
    #ubuntu version < 22
    #BIN_URL=https://github.com/avast/retdec/releases/download/v4.0/retdec-v4.0-ubuntu-64b.tar.xz does not work
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential cmake git openssl libssl-dev python3 autoconf automake libtool pkg-config m4 zlib1g-dev upx doxygen graphviz
    mkdir -p /tmp/retdec
    cd /tmp/retdec
    git clone https://github.com/avast/retdec.git && \
	cd retdec && \
	git checkout 3435bc827d2c2c5da91dfb84509af0c034ee22b5 && \
	mkdir build && \
	cd build && \
	cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_LIBRARY_PATH=/usr/lib/gcc/x86_64-linux-gnu/7/ && \
	make -j 8 && \
	make install

    rm -rf /tmp/retdec

else
    BIN_URL=https://github.com/avast/retdec/releases/download/v5.0/RetDec-v5.0-Linux-Release.tar.xz
    wget $BIN_URL -O /tmp/retdec.tar.xz && \
    tar -xJf /tmp/retdec.tar.xz -C $PREFIX/ ;\
    rm /tmp/retdec.tar.xz
fi

# replace with our config
popd
cp decompiler-config.json $PREFIX'/share/retdec/decompiler-config.json'
echo "Retdec installed. Please do: export RETDEC_PATH=$PREFIX"
