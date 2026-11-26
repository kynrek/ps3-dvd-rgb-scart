#!/bin/bash
# Headless Ghidra decompile of the functions containing the given addresses.
# usage: GHIDRA=<ghidra dir> PROJ=<project dir> decomp.sh <project name> <outfile> <hex addrs...>
P=$1; O=$2; shift 2; D=$(dirname "$(readlink -f "$0")")
"$GHIDRA/support/analyzeHeadless" "$PROJ" "$P" -process -noanalysis -readOnly -scriptPath "$D" \
  -postScript Decomp.java "$(readlink -f "$O")" "$@" > "$O.log" 2>&1
tail -1 "$O.log"
