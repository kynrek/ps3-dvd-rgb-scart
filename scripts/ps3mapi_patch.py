#!/usr/bin/env python3
"""Runtime (RAM-only) VSH patch for PS3 4.93 over PS3MAPI (webMAN-MOD / Cobra, TCP 7887).
Nothing is written to flash; a reboot undoes it.

  ps3mapi_patch.py <ps3-ip> status          # show firmware, VSH pid, current bytes
  ps3mapi_patch.py <ps3-ip> apply  <patch>  # write patch (verifies original bytes first)
  ps3mapi_patch.py <ps3-ip> revert <patch>

UNTESTED against a real console yet: the PS3MAPI command names follow the ps3mapi server
source (PS3 GETFWVERSION, PROCESS GETALLPID/GETNAME, MEMORY GET/SET over a PASV data link).
"""
import socket, sys, re

# patch name -> list of (vsh address, original bytes, new bytes, note)
PATCHES = {
    # VSH 4.93 FUN_00473a28 = the only path that calls avset_setmv (Macrovision on/off for the
    # analog AV MULTI port). 'mr r31,r4' -> 'li r31,0' makes every request "MV off".
    'nomv': [(0x473a48, '7c9f2378', '3be00000', 'FUN_00473a28: mode := 0 (Macrovision off)')],
}

class Mapi:
    def __init__(s, ip):
        s.ip = ip; s.c = socket.create_connection((ip, 7887), timeout=10); s.f = s.c.makefile('rb')
        s.read()                       # banner
    def read(s):
        l = s.f.readline().decode(errors='replace').strip()
        if not l: raise IOError('connection closed')
        while re.match(r'^\d{3}-', l): l = s.f.readline().decode(errors='replace').strip()
        return l
    def cmd(s, c):
        s.c.sendall((c + '\r\n').encode()); r = s.read()
        if r[:1] not in '12': raise IOError(f'{c!r} -> {r}')
        return r
    def pasv(s):
        r = s.cmd('PASV'); n = list(map(int, re.search(r'\((.*)\)', r)[1].split(',')))
        return socket.create_connection((s.ip, n[4]*256 + n[5]), timeout=10)
    def mget(s, pid, addr, size):
        dc = s.pasv(); s.cmd(f'MEMORY GET {pid} {addr:X} {size}'); data = b''
        while len(data) < size:
            b = dc.recv(size - len(data))
            if not b: break
            data += b
        dc.close(); s.read(); return data
    def mset(s, pid, addr, data):
        dc = s.pasv(); s.cmd(f'MEMORY SET {pid} {addr:X}'); dc.sendall(data); dc.close(); s.read()
    def vsh_pid(s):
        pids = s.cmd('PROCESS GETALLPID').split(' ', 1)[1].split('|')
        for p in pids:
            if p and int(p) != 0:
                name = s.cmd(f'PROCESS GETNAME {p}').split(' ', 1)[1]
                if 'vsh' in name.lower(): return int(p), name
        raise IOError('VSH process not found')

def main():
    ip, op = sys.argv[1], sys.argv[2]
    m = Mapi(ip)
    print('firmware:', m.cmd('PS3 GETFWVERSION'), '| type:', m.cmd('PS3 GETFWTYPE'))
    pid, name = m.vsh_pid(); print(f'VSH pid {pid} ({name})')
    names = [sys.argv[3]] if len(sys.argv) > 3 else list(PATCHES)
    for n in names:
        for addr, orig, new, note in PATCHES[n]:
            cur = m.mget(pid, addr, 4).hex()
            print(f'{n} {addr:#x} now={cur} orig={orig} patched={new}  {note}')
            if op == 'apply':
                if cur == new: print('  already applied'); continue
                if cur != orig: sys.exit('  bytes differ from 4.93 VSH: NOT patching')
                m.mset(pid, addr, bytes.fromhex(new)); print('  applied ->', m.mget(pid, addr, 4).hex())
            elif op == 'revert':
                if cur == new: m.mset(pid, addr, bytes.fromhex(orig)); print('  reverted ->', m.mget(pid, addr, 4).hex())

if __name__ == '__main__': main()
