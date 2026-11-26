#!/usr/bin/env python3
"""Snapshot VSH AV-settings objects (4.92) to a JSON file: avsnap.py <name>; avsnap.py diff a b"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import vshmem
OUT = '/home/kynrek/claude/ps3/snaps'; os.makedirs(OUT, exist_ok=True)
def snap(name):
    root = vshmem.u32(0x738b34); regions = {'root': (root, 0x84)}
    r = vshmem.read(root, 0x84)
    for off in range(0, 0x84, 4):
        p = int.from_bytes(r[off:off+4], 'big')
        if 0x20000000 <= p < 0x30000000: regions[f'root+{off:#x}'] = (p, 0x100)
    # second level: pointers inside the port objects (state objects etc.)
    for k, (a, n) in list(regions.items()):
        if k == 'root': continue
        d = vshmem.read(a, n); regions[k] = (a, n, d.hex())
        for off in range(0, n, 4):
            p = int.from_bytes(d[off:off+4], 'big')
            if 0x20000000 <= p < 0x30000000 and f'{k}>{off:#x}' not in regions and len(regions) < 120:
                try: regions[f'{k}>{off:#x}'] = (p, 0x80, vshmem.read(p, 0x80).hex())
                except Exception: pass
    regions['root'] = (root, 0x84, r.hex())
    json.dump(regions, open(f'{OUT}/{name}.json', 'w')); print('saved', len(regions), 'regions')
def diff(a, b):
    A = json.load(open(f'{OUT}/{a}.json')); B = json.load(open(f'{OUT}/{b}.json'))
    for k in A:
        if k not in B or A[k][0] != B[k][0]: continue
        x, y = bytes.fromhex(A[k][2]), bytes.fromhex(B[k][2])
        for off in range(0, min(len(x), len(y)), 4):
            if x[off:off+4] != y[off:off+4]:
                print(f'{k:28s} @{A[k][0]+off:#010x} (+{off:#x}): {x[off:off+4].hex()} -> {y[off:off+4].hex()}')
if __name__ == '__main__':
    if sys.argv[1] == 'diff': diff(sys.argv[2], sys.argv[3])
    else: snap(sys.argv[1])
