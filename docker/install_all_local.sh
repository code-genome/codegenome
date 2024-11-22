# local install
apt-get update && \
  apt-get install -y \
  python3 \
  python3-pip \
  python-is-python3 \
  wget

cp -f decompiler-config.json /tmp/
cp -f install_retdec.sh /tmp/
cp -f install_pyleargist.sh /tmp/

cp -f llvmlite-settypename.patch /tmp/
cp -f llvm-gcc-fix.patch /tmp/
cp -f install_llvmlite.sh /tmp/

cp -rf ../llvm_pass /tmp/llvm_pass
cp -f install_llvm_pass.sh /tmp/

export PATH="/opt/cg/retdec/bin:$PATH"
export RETDEC_PATH="/opt/cg/retdec"

cleanup() {
    cd /tmp
    rm -f /tmp/llvmlite-settypename.patch
    rm -f /tmp/llvm-gcc-fix.patch
    rm -rf /tmp/llvm_pass
    rm -rf /tmp/tmp_src
    rm -f /tmp/decompiler-config.json
    rm -f /tmp/install_retdec.sh
    rm -f /tmp/install_pyleargist.sh
    rm -f /tmp/install_llvmlite.sh
    rm -f /tmp/install_llvm_pass.sh
}

cd /tmp && bash install_retdec.sh && \
cd /tmp && bash install_pyleargist.sh && \
cd /tmp && bash install_llvmlite.sh && \
cd /tmp && bash install_llvm_pass.sh

# Check the exit status of the last command
if [ $? -ne 0 ]; then
    echo "Installation failed. Do you want to cleanup files from /tmp? (y/n)"
    read answer

    case ${answer:0:1} in
        y|Y )
            echo "Cleaning up.."
            cleanup
            ;;
        * )
            echo "Exiting..."
            exit 1
            ;;
    esac
else
    cleanup
fi

