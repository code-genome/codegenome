#!/bin/bash
P=p
A='elf'
gcc -O0 -o $P'.gcc.0.'$A $P'.c'
gcc -O3 -o $P'.gcc.3.'$A $P'.c'
clang -O0 -o $P'.clang.0.'$A $P'.c'
clang -O3 -o $P'.clang.3.'$A $P'.c'
clang -Oz -o $P'.clang.z.'$A $P'.c'

