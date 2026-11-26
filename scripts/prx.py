import struct,sys
def load(p):
    d=open(p,'rb').read()
    phoff,=struct.unpack('>Q',d[0x20:0x28]); n,=struct.unpack('>H',d[0x38:0x3a]); typ,=struct.unpack('>H',d[0x10:0x12])
    segs=[]
    for i in range(n):
        t,fl,off,va,pa,fs,ms,al=struct.unpack('>IIQQQQQQ',d[phoff+i*56:phoff+i*56+56]); segs.append((t,off,va,pa,fs))
    return d,segs,typ
def mk(d,segs,typ):
    loads=[s for s in segs if s[0]==1 and s[4]]
    def fo(v):
        for t,off,va,pa,fs in loads:
            if va<=v<va+fs: return off+v-va
        return None
    return fo
def cstr(d,o): return d[o:d.find(b'\0',o)].decode(errors='replace')
def scan(p):
    d,segs,typ=load(p); fo=mk(d,segs,typ)
    exps=[];imps=[]
    # brute-force scan for import (0x2c) and export (0x1c) entries
    for o in range(0,len(d)-0x2c,4):
        sz=d[o]
        if sz==0x2c and d[o+1]==0:
            nf,nv=struct.unpack('>HH',d[o+6:o+10]); name,fnid,fstub=struct.unpack('>III',d[o+0x10:o+0x1c])
            if 0<nf<1000 and fo(name) and fo(fnid) and fo(fstub):
                ln=cstr(d,fo(name))
                if ln.isprintable() and 2<len(ln)<40:
                    nids=[struct.unpack('>I',d[fo(fnid)+4*i:fo(fnid)+4*i+4])[0] for i in range(nf)]
                    imps.append((ln,nids))
        if sz==0x1c and d[o+1]==0:
            nf,nv=struct.unpack('>HH',d[o+6:o+10]); name,nids,stubs=struct.unpack('>III',d[o+0x10:o+0x1c])
            if 0<nf<2000 and nv<500 and fo(nids) and fo(stubs):
                ln=cstr(d,fo(name)) if name and fo(name) else ''
                if name==0 or (ln.isprintable() and len(ln)<40):
                    ents=[]
                    for i in range(nf):
                        nid,=struct.unpack('>I',d[fo(nids)+4*i:fo(nids)+4*i+4]); opd,=struct.unpack('>I',d[fo(stubs)+4*i:fo(stubs)+4*i+4])
                        f=struct.unpack('>I',d[fo(opd):fo(opd)+4])[0] if fo(opd) else None
                        ents.append((nid,opd,f))
                    exps.append((ln,ents))
    return imps,exps
if __name__=='__main__':
    imps,exps=scan(sys.argv[1])
    for l,n in imps: print('IMP',l,len(n))
    for l,e in exps: print('EXP',l,len(e))
