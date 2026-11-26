# Generate the webMAN boot scripts for every supported VSH version into ps3files/.
import subprocess, sys, os
PY = sys.executable; HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'ps3files')
U = '/setmem.ps3mapi?proc=0x1000300&oper=0'
VERS = {'4.92': 0x751500, '4.93': 0x751600}
def cave(fw):
    out = subprocess.run([PY, '-I', os.path.join(HERE, 'mkcave_fix.py'), f'--fw={fw}'], capture_output=True, text=True, check=True).stdout
    return next(l for l in out.split() if len(l) > 40)
os.makedirs(os.path.join(OUT, 'ps3-dvd-rgb'), exist_ok=True)
with open(os.path.join(OUT, 'autoexec.bat'), 'w') as f:
    f.write("""# PS3 DVD over RGB SCART fix + Macrovision off (RAM-only VSH patches), 4.92 and 4.93 CEX.
# https://github.com/kynrek/ps3-dvd-rgb-scart  -  disable: delete /dev_hdd0/autoexec.bat and reboot.
wait xmb
# Hold L1 while the XMB appears to skip the patches this boot
abort if L1
call /dev_hdd0/ps3-dvd-rgb/fix-4.92.bat
call /dev_hdd0/ps3-dvd-rgb/fix-4.93.bat
""")
for fw, log in VERS.items():
    h = cave(fw)
    with open(os.path.join(OUT, 'ps3-dvd-rgb', f'fix-{fw}.bat'), 'w') as f:
        f.write(f"""# DVD RGB SCART fix for VSH {fw} CEX. Runs only on firmware {fw}.
abort if not Firmware {fw}
# 1) code cave (avfix) at 0x6BBEB0-0x6BBFFF
{U}&addr=6BBEB0&val={h[:512]}
{U}&addr=6BBFB0&val={h[512:]}
# 2) reset packet-log write offset (log at {log:#X})
{U}&addr={log:X}&val=00000000
# 3) nomv: Macrovision always off
{U}&addr=473A48&val=3BE00000
# 4) hook the sys_uart_send wrapper into the cave (must be last)
{U}&addr=5DED64&val=480DD14C
""")
    print('wrote fix-%s.bat' % fw)
