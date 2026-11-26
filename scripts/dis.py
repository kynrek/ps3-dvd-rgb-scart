import struct,sys
from capstone import *
d=open(sys.argv[1],'rb').read()
TOC=int(sys.argv[2],16)
_phoff,=struct.unpack('>Q',d[0x20:0x28]); _n,=struct.unpack('>H',d[0x38:0x3a])
SEGS=[]
for _i in range(_n):
    _t,_fl,_off,_va,_pa,_fs,_ms,_al=struct.unpack('>IIQQQQQQ',d[_phoff+_i*56:_phoff+_i*56+56])
    if _t==1 and _fs: SEGS.append((_va,_fs,_off))
def fo(va):
    for v,fs,off in SEGS:
        if v<=va<v+fs: return off+va-v
    return -1
def cstr(va):
    o=fo(va); e=d.find(b'\0',o); return d[o:e].decode(errors='replace') if 0<=o<len(d) and e-o<80 else None
def toc(off):
    v,=struct.unpack('>I',d[fo(TOC+off):fo(TOC+off)+4]); return v
md=Cs(CS_ARCH_PPC, CS_MODE_64|CS_MODE_BIG_ENDIAN)
def dis(start,end):
    out=[]
    def gen():
        a=start
        while a<end:
            got=False
            for i in md.disasm(d[fo(a):fo(end)], a):
                got=True; yield i; a=i.address+4
            if a<end and (not got or True):
                w=d[fo(a):fo(a)+4]
                class X: pass
                x=X(); x.address=a; x.mnemonic='.long'; x.op_str=w.hex(); yield x; a+=4
    for i in gen():
        c=''
        if 'r2)' in i.op_str and i.mnemonic in ('lwz','ld','addi'):
            try:
                off=int(i.op_str.split(',')[1].strip().split('(')[0],0)
                if i.mnemonic=='addi':
                    off=int(i.op_str.split(',')[2],0)
                v=toc(off); s=cstr(v); c=f'  ; toc[{off:#x}]={v:#x} {s!r}' if s else f'  ; toc[{off:#x}]={v:#x}'
            except Exception as e: pass
        out.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}{c}')
    return out
if __name__=='__main__':
    for l in dis(int(sys.argv[3],16),int(sys.argv[4],16)): print(l)
