#!/bin/bash
# Check whether the DVD-Video region check in bdp_disccheck_plugin.sprx is patched (read-only).
# The plugin is only loaded while a disc is in the drive, so insert a DVD first.
# Usage: ps3-dvd-region-check.sh [ip]   (exit 0 = patched, 1 = PS3 offline, 2 = not patched, 3 = plugin not loaded)
IP=${1:-${PS3_IP:-192.168.1.239}}
ORIG=808100744BFFFE3539200067      # lwz r4,0x74(r1); bl 0x1360 (region test); li r9,0x67
PATCHED=808100743860000139200067   # lwz r4,0x74(r1); li r3,1;                    li r9,0x67
curl -s -m 8 -o /dev/null "http://$IP/cpursx.ps3" || { echo "PS3 at $IP is offline"; exit 1; }
find() {  # find <hexpattern> -> prints address or nothing; scans VSH 0x10000..0x40000000 in 16 MB steps
  local s=$((0x10000)) e out a
  while [ $s -lt $((0x40000000)) ]; do
    e=$((s + 0x1000000))
    out=$(curl -s -m 120 "http://$IP/getmem.ps3mapi?proc=0x1000300&addr=$(printf %X $s)&len=16&find=0x$1&stop=$(printf %X $e)" | sed 's/<[^>]*>/ /g')
    a=$(echo "$out" | grep -o "LV1 Dump 0x[0-9a-f]*" | head -1 | awk '{print $3}')
    [ -n "$a" ] && [ $((a)) -ne $s ] && { printf '%X\n' $((a)); return; }
    s=$e
  done
}
a=$(find $PATCHED); [ -n "$a" ] && { echo "region check PATCHED at 0x$a (li r3,1)"; exit 0; }
a=$(find $ORIG);    [ -n "$a" ] && { echo "region check NOT patched at 0x$a (bl 0x1360)"; exit 2; }
echo "bdp_disccheck_plugin not loaded: insert a DVD and run again"; exit 3
