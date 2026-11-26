#!/usr/bin/env python3
"""Read VSH memory on the PS3 through webMAN's getmem.ps3mapi page. vshmem.py <hexaddr> <len>"""
import sys, re, urllib.request
IP = '192.168.1.239'; PID = '0x1000300'
def read(addr, n):
    out = b''
    while n > 0:
        k = min(n, 256)
        html = urllib.request.urlopen(f'http://{IP}/getmem.ps3mapi?proc={PID}&addr={addr:X}&len={k}', timeout=15).read().decode(errors='replace')
        m = re.search(r'([0-9A-F]{%d})\s*Dump:' % (2*k), re.sub(r'<[^>]*>', ' ', html))
        if not m: raise IOError('parse failed at %x' % addr)
        out += bytes.fromhex(m[1]); addr += k; n -= k
    return out
def u32(a): return int.from_bytes(read(a, 4), 'big')
if __name__ == '__main__':
    a, n = int(sys.argv[1], 16), int(sys.argv[2], 0)
    d = read(a, n)
    for i in range(0, len(d), 16):
        print(f'{a+i:08x}  ' + ' '.join(d[i+j:i+j+4].hex() for j in range(0, 16, 4)))
