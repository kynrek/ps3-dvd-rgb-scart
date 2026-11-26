#!/usr/bin/env python3
"""Minimal PS3 firmware tools: unpack PUP, decrypt SCE update packages (dev_flash tars).
Formats follow RPCS3's Loader/PUP.cpp and Crypto/unself.cpp."""
import struct, sys, os, zlib, io, tarfile
from Crypto.Cipher import AES
from Crypto.Util import Counter

SCEPKG_ERK = bytes.fromhex(os.environ["PS3_SCEPKG_ERK"])  # not included: set from RPCS3 key_vault.cpp
SCEPKG_RIV = bytes.fromhex(os.environ["PS3_SCEPKG_RIV"])

def unpup(path, outdir):
    d = open(path, 'rb').read()
    magic, pkgv, imgv, cnt, hlen, dlen = struct.unpack('>8sQQQQQ', d[:0x30])
    assert magic == b'SCEUF\0\0\0'
    os.makedirs(outdir, exist_ok=True)
    for i in range(cnt):
        eid, off, ln = struct.unpack('>QQQ', d[0x30+i*0x20:0x30+i*0x20+0x18])
        open(os.path.join(outdir, f'{eid:#x}'), 'wb').write(d[off:off+ln])
        print(f'{eid:#06x} off={off:#x} len={ln:#x}')

def ctr(key, iv, data):
    return AES.new(key, AES.MODE_CTR, counter=Counter.new(128, initial_value=int.from_bytes(iv, 'big'))).decrypt(data)

def sce_sections(d, erk, riv):
    """Decrypt an SCE container; returns list of (section header dict, plaintext bytes) after decompression."""
    magic, hver, flags, typ, meta, hsize, esize = struct.unpack('>IIHHIQQ', d[:0x20])
    assert magic == 0x53434500, 'not SCE'
    mi_off = meta + 0x20
    mi = d[mi_off:mi_off+0x40]
    if not (flags & 0x8000):
        mi = AES.new(erk, AES.MODE_CBC, riv).decrypt(mi)
    key, kpad, iv, ivpad = mi[:16], mi[16:32], mi[32:48], mi[48:64]
    if kpad[0] or ivpad[0]:
        raise ValueError('metadata info decrypt failed (wrong key?)')
    mh = ctr(key, iv, d[mi_off+0x40:hsize])
    sig_len, u1, scount, kcount, opt, u2, u3 = struct.unpack('>QIIIIII', mh[:0x20])
    secs = []
    for i in range(scount):
        f = struct.unpack('>QQIIIIIIII', mh[0x20+i*0x30:0x50+i*0x30])
        secs.append(dict(zip(['off','size','type','prog_idx','hashed','sha1_idx','enc','key_idx','iv_idx','comp'], f)))
    keys_off = 0x20 + scount*0x30
    keys = [mh[keys_off+j*16:keys_off+j*16+16] for j in range(kcount)]
    out = []
    for s in secs:
        raw = d[s['off']:s['off']+s['size']]
        if s['enc'] == 3:
            raw = ctr(keys[s['key_idx']], keys[s['iv_idx']], raw)
        if s['comp'] == 2:
            raw = zlib.decompress(raw)
        out.append((s, raw))
    return dict(flags=flags, type=typ, hver=hver, meta=meta, hsize=hsize, esize=esize), out

def unpkg(path, outdir):
    d = open(path, 'rb').read()
    hdr, secs = sce_sections(d, SCEPKG_ERK, SCEPKG_RIV)
    tar = secs[2][1]
    os.makedirs(outdir, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(outdir, filter='fully_trusted')
    return len(tar)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'unpup': unpup(sys.argv[2], sys.argv[3])
    elif cmd == 'unpkg': print(unpkg(sys.argv[2], sys.argv[3]))

# ---- SELF decryption ----
import re
def load_keys(kv_cpp):
    src = open(kv_cpp).read()
    keys = []
    for m in re.finditer(r'emplace_back\(\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),\s*(KEY_\w+),\s*"([0-9A-F]{64})",\s*"([0-9A-F]{32})"', src):
        keys.append(dict(vs=int(m[1],16), ve=int(m[2],16), rev=int(m[3],16), type=m[4], erk=bytes.fromhex(m[5]), riv=bytes.fromhex(m[6])))
    return keys

KEYS = None
def unself(path, out, kv_cpp):
    global KEYS
    if KEYS is None: KEYS = load_keys(kv_cpp)
    d = open(path, 'rb').read()
    magic, hver, flags, typ, meta, hsize, esize = struct.unpack('>IIHHIQQ', d[:0x20])
    assert magic == 0x53434500
    ext = struct.unpack('>9Q', d[0x20:0x68])
    _, pid_off, ehdr_off, phdr_off, shdr_off, seg_off, ver_off, sup_off, sup_sz = ext
    auth, vendor, ptype, sver = struct.unpack('>QIIQ', d[pid_off:pid_off+0x18])
    mi_off = meta + 0x20
    enc_mi = d[mi_off:mi_off+0x40]
    tname = {1:'KEY_LV0',2:'KEY_LV1',3:'KEY_LV2',4:'KEY_APP',5:'KEY_ISO',6:'KEY_LDR',7:'KEY_UNK7',8:'KEY_NPDRM'}.get(ptype)
    cands = sorted(KEYS, key=lambda k: (k['type']!=tname, k['rev']!=flags))
    for k in cands:
        mi = AES.new(k['erk'], AES.MODE_CBC, k['riv']).decrypt(enc_mi)
        if mi[16:32] == bytes(16) and mi[48:64] == bytes(16): break
    else:
        raise ValueError(f'no key found (type {ptype} rev {flags:#x})')
    key, iv = mi[:16], mi[32:48]
    mh = ctr(key, iv, d[mi_off+0x40:hsize])
    sig_len, u1, scount, kcount, opt, u2, u3 = struct.unpack('>QIIIIII', mh[:0x20])
    keys = [mh[0x20+scount*0x30+j*16:0x20+scount*0x30+j*16+16] for j in range(kcount)]
    # ELF header
    eh = d[ehdr_off:ehdr_off+0x40]
    e_phoff, e_shoff = struct.unpack('>QQ', eh[0x20:0x30])
    e_phentsize, e_phnum, e_shentsize, e_shnum = struct.unpack('>HHHH', eh[0x36:0x3e])
    ph = d[phdr_off:phdr_off+e_phentsize*e_phnum]
    phdrs = [struct.unpack('>IIQQQQQQ', ph[i*0x38:(i+1)*0x38]) for i in range(e_phnum)]
    size = max([p[2]+p[5] for p in phdrs] + [e_phoff+len(ph), 0x40])
    shdr = b''
    if shdr_off and e_shnum:
        shdr = d[shdr_off:shdr_off+e_shentsize*e_shnum]
        size = max(size, e_shoff+len(shdr))
    elf = bytearray(size)
    elf[0:0x40] = eh; elf[e_phoff:e_phoff+len(ph)] = ph
    if shdr: elf[e_shoff:e_shoff+len(shdr)] = shdr
    for i in range(scount):
        off, sz, styp, pidx, hashed, sha1, enc, kidx, ividx, comp = struct.unpack('>QQIIIIIIII', mh[0x20+i*0x30:0x50+i*0x30])
        if styp != 2: continue
        raw = d[off:off+sz]
        if enc == 3: raw = ctr(keys[kidx], keys[ividx], raw)
        if comp == 2: raw = zlib.decompress(raw)
        po = phdrs[pidx][2]
        elf[po:po+len(raw)] = raw
    open(out, 'wb').write(elf)
    return ptype, flags, sver

if __name__ == '__main__' and sys.argv[1] == 'unself':
    kv = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools/rpcs3-src/rpcs3/Crypto/key_vault.cpp')
    for p in sys.argv[2:]:
        try: print(p, unself(p, p + '.elf', kv))
        except Exception as e: print(p, 'ERR', e)
