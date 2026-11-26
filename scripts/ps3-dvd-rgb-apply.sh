#!/bin/bash
# Re-apply the PS3 DVD-over-RGB-SCART fix (RAM only) via webMAN. VSH 4.92 only: checks bytes first.
# Usage: ps3-dvd-rgb-apply.sh [ip]    (exit 0 = applied/already applied, 1 = PS3 offline, 2 = unexpected bytes)
IP=${1:-192.168.1.239}; DIR=$(dirname "$(readlink -f "$0")"); PY=${PYTHON:-python3}
S="http://$IP/setmem.ps3mapi?proc=0x1000300&oper=0"
rd() { python3 -I "$DIR/vshmem.py" "$1" 4 2>/dev/null | awk '{print $2}'; }
curl -s -m 5 -o /dev/null "http://$IP/" || exit 1
hook=$(rd 5ded64); mv=$(rd 473a48)
[ "$hook" = 480dd14c ] && [ "$mv" = 3be00000 ] && { echo "already applied"; exit 0; }
[ "$hook" = 38a00002 ] || [ "$hook" = 480dd14c ] || { echo "unexpected bytes at 0x5ded64: $hook"; exit 2; }
[ "$mv" = 7c9f2378 ] || [ "$mv" = 3be00000 ] || { echo "unexpected bytes at 0x473a48: $mv"; exit 2; }
HEX=$($PY -I "$DIR/mkcave_fix.py" | sed -n '/^[0-9A-F]\{40,\}$/p')
curl -s -m 15 "$S&addr=5DED64&val=38A00002" >/dev/null
curl -s -m 15 "$S&addr=6BBEB0&val=${HEX:0:512}" >/dev/null
curl -s -m 15 "$S&addr=6BBFB0&val=${HEX:512}" >/dev/null
live=$($PY -I -c "import sys; sys.path.insert(0,'$DIR'); import vshmem; print(vshmem.read(0x6bbeb0,0x150).hex().upper())")
[ "$live" = "$HEX" ] || { echo "cave verify failed"; exit 2; }
curl -s -m 15 "$S&addr=751500&val=00000000" >/dev/null
curl -s -m 15 "$S&addr=473A48&val=3BE00000" >/dev/null
curl -s -m 15 "$S&addr=5DED64&val=480DD14C" >/dev/null
echo "applied: hook=$(rd 5ded64) mv=$(rd 473a48)"
