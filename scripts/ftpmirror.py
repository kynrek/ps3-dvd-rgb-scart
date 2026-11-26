import ftplib, os, sys, time
IP = sys.argv[1]
class C:
    ftp = None
def conn():
    if C.ftp:
        try: C.ftp.close()
        except Exception: pass
    C.ftp = ftplib.FTP(encoding='latin-1', timeout=60); C.ftp.connect(IP); C.ftp.login()
def retry(fn):
    for i in range(12):
        try: return fn()
        except (ftplib.error_temp, OSError, EOFError) as e:
            time.sleep(2 + i); conn()
    raise IOError('gave up')
def mirror(remote, local, st):
    os.makedirs(local, exist_ok=True)
    ents = []
    retry(lambda: (ents.clear(), C.ftp.retrlines(f'LIST {remote}', ents.append)))
    for line in ents:
        p = line.split(None, 8)
        if len(p) < 9 or p[8] in ('.', '..'): continue
        rp, lp = f'{remote}/{p[8]}', os.path.join(local, p[8])
        if line.startswith('d'): mirror(rp, lp, st); continue
        size = int(p[4])
        if os.path.exists(lp) and os.path.getsize(lp) == size: st[0] += 1; st[1] += size; continue
        def get():
            with open(lp, 'wb') as f: C.ftp.retrbinary(f'RETR {rp}', f.write)
        retry(get); time.sleep(0.05)
        if os.path.getsize(lp) != size: print('SIZE MISMATCH', rp, size, os.path.getsize(lp))
        st[0] += 1; st[1] += size
conn()
for root in sys.argv[3:]:
    st = [0, 0]; mirror(root, os.path.join(sys.argv[2], root.strip('/')), st)
    print(f'{root}: {st[0]} files, {st[1]/1e6:.1f} MB')
