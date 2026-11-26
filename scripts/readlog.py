import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import vshmem
B = 0x751500
end = vshmem.u32(B); d = vshmem.read(B, min(end + 8, 0x9f8))
off = 0; i = 0
while off < end:
    size = int.from_bytes(d[off+4:off+8], 'big'); n = min(size, 0x200)
    pkt = d[off+8:off+8+n]
    print(f'#{i} len={size:#x} ' + ' '.join(pkt[j:j+4].hex() for j in range(0, len(pkt), 4)))
    off += (n + 7) & ~3; i += 1
