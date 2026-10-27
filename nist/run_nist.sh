#!/bin/bash
# NIST STS 2.1.2 (unmodified) on a 29929-bit ASCII file. usage: run_nist.sh /abs/path/input.txt
# run inside a copy of sts-2.1.2-src
mkdir -p obj && make >/dev/null
mkdir -p experiments/AlgorithmTesting && for t in Frequency BlockFrequency Runs LongestRun Rank FFT NonOverlappingTemplate OverlappingTemplate Universal LinearComplexity Serial ApproximateEntropy CumulativeSums RandomExcursions RandomExcursionsVariant; do mkdir -p experiments/AlgorithmTesting/$t; done
# menu: 0=input file, file, 0=choose tests, mask (Freq,BlockFreq,CuSum,Runs,LongestRun,DFT), 0=default params, 1 stream, 0=ASCII
printf '0\n%s\n0\n111110100000000\n0\n1\n0\n' "$1" | ./assess 29929
