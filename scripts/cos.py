import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps3fw
d = open(sys.argv[1],'rb').read()
hdr, secs = ps3fw.sce_sections(d, ps3fw.SCEPKG_ERK, ps3fw.SCEPKG_RIV)
cos = secs[2][1]
os.makedirs(sys.argv[2], exist_ok=True)
# COS: u32 unk, u32 count, u64 total; entries 0x30: u64 off, u64 size, char name[0x20]
_, n, tot = struct.unpack('>IIQ', cos[:16])
for i in range(n):
    off, sz = struct.unpack('>QQ', cos[16+i*0x30:32+i*0x30])
    name = cos[32+i*0x30:64+i*0x30].split(b'\0')[0].decode()
    open(os.path.join(sys.argv[2], name),'wb').write(cos[off:off+sz]); print(name, hex(sz))
