#/bin/bash

P=$1
A='unknown'
if [ "$(uname)" == "Linux" ];then
    A='elf'
    llvm_dis=$(which llvm-dis)
    if [ "$llvm_dis" == "" ];then
        llvm_dis='/opt/llvm/bin/llvm-dis'
    fi
fi

if [ "$(uname)" == "Darwin" ];then
    A='mac'
    llvm_dis='/usr/local/Cellar/llvm/9.0.0/bin/llvm-dis'
fi

#echo gcc -O0 -o $P'.gcc.0.'$A $P'.c'
#echo gcc -O3 -o $P'.gcc.3.'$A $P'.c'
echo clang -O0 -o $P'.clang.0.'$A $P'.c'
echo clang -O3 -o $P'.clang.3.'$A $P'.c'
echo clang -O0 -emit-llvm -o $P'.clang.0.bc' -c $P'.c'
echo $llvm_dis $P'.clang.0.bc'
echo clang -O3 -emit-llvm -o $P'.clang.3.bc' -c $P'.c'
echo $llvm_dis $P'.clang.3.bc'


