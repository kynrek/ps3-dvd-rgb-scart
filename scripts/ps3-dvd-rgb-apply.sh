#!/bin/bash
# Re-apply the PS3 DVD-over-RGB-SCART fix (RAM only) via webMAN, for VSH 4.92 or 4.93 CEX. Checks bytes first.
# Usage: ps3-dvd-rgb-apply.sh [ip]   (exit 0 = applied/already applied, 1 = PS3 offline, 2 = unsupported/unexpected)
IP=${1:-192.168.1.239}; DIR=$(dirname "$(readlink -f "$0")"); PY=${PYTHON:-python3}
S="http://$IP/setmem.ps3mapi?proc=0x1000300&oper=0"
rd() { python3 -I "$DIR/vshmem.py" "$1" 4 2>/dev/null | awk '{print $2}'; }
page=$(curl -s -m 8 "http://$IP/cpursx.ps3") || exit 1
FW=$(echo "$page" | sed 's/<[^>]*>/ /g' | grep -oE "Firmware ?: ?4\.9[0-9]" | grep -oE "4\.9[0-9]" | head -1)
case "$FW" in 4.92) LOG=751500;; 4.93) LOG=751600;; *) echo "unsupported firmware '$FW'"; exit 2;; esac
hook=$(rd 5ded64); mv=$(rd 473a48); pre=$(rd 5ded60)
[ "$hook" = 480dd14c ] && [ "$mv" = 3be00000 ] && { echo "already applied ($FW)"; exit 0; }
[ "$pre" = f8010010 ] || { echo "unexpected bytes at 0x5ded60: $pre"; exit 2; }
[ "$hook" = 38a00002 ] || [ "$hook" = 480dd14c ] || { echo "unexpected bytes at 0x5ded64: $hook"; exit 2; }
[ "$mv" = 7c9f2378 ] || [ "$mv" = 3be00000 ] || { echo "unexpected bytes at 0x473a48: $mv"; exit 2; }
HEX=$($PY -I "$DIR/mkcave_fix.py" --fw=$FW | sed -n '/^[0-9A-F]\{40,\}$/p')
curl -s -m 15 "$S&addr=5DED64&val=38A00002" >/dev/null
curl -s -m 15 "$S&addr=6BBEB0&val=${HEX:0:512}" >/dev/null
curl -s -m 15 "$S&addr=6BBFB0&val=${HEX:512}" >/dev/null
live=$($PY -I -c "import sys; sys.path.insert(0,'$DIR'); import vshmem; print(vshmem.read(0x6bbeb0,0x150).hex().upper())")
[ "$live" = "$HEX" ] || { echo "cave verify failed"; exit 2; }
curl -s -m 15 "$S&addr=$LOG&val=00000000" >/dev/null
curl -s -m 15 "$S&addr=473A48&val=3BE00000" >/dev/null
curl -s -m 15 "$S&addr=5DED64&val=480DD14C" >/dev/null
echo "applied ($FW): hook=$(rd 5ded64) mv=$(rd 473a48)"
