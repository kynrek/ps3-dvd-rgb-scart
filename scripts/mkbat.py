# Generate the webMAN boot scripts for every supported VSH version into ps3files/.
import subprocess, sys, os
PY = sys.executable; HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'ps3files')
U = '/setmem.ps3mapi?proc=0x1000300&oper=0'
VERS = {'4.92': 0x751500, '4.93': 0x751600}
def cave(fw):
    out = subprocess.run([PY, '-I', os.path.join(HERE, 'mkcave_fix.py'), f'--fw={fw}'], capture_output=True, text=True, check=True).stdout
    return next(l for l in out.split() if len(l) > 40)
os.makedirs(os.path.join(OUT, 'ps3-dvd-rgb'), exist_ok=True)
# NOTE for comment text: webMAN's parser treats the words "else" and "end if" (and "=/" or ".ps3")
# specially even inside # comments, so the comments below avoid them.
with open(os.path.join(OUT, 'autoexec.bat'), 'w') as f:
    f.write("""# ================================================================================
#  PS3 DVD fixes for RGB SCART  -  webMAN MOD startup script
#  https://github.com/kynrek/ps3-dvd-rgb-scart
# ================================================================================
#  webMAN runs this file every time the PS3 boots. It applies two fixes:
#    1. FORCE RGB OVER SCART: stops DVD playback turning green on an RGB SCART cable
#    2. MACROVISION OFF: the DVD player never switches analog copy protection on
#  Both are changes to the XMB program (VSH) in RAM only. Nothing is written to
#  flash, and a reboot without this file undoes everything.
#
#  The patch commands are in /dev_hdd0/ps3-dvd-rgb/ (one file per firmware).
#  Each file only runs on its own firmware and does nothing on any other.
#
#  Skip once : hold L1 while the XMB appears.
#  Remove    : delete this file (and /dev_hdd0/ps3-dvd-rgb), then reboot.
# ================================================================================

# Wait until the XMB has finished loading, so VSH is in memory.
wait xmb

# Safety switch: if L1 is held right now, stop here and patch nothing.
abort if L1

# Run the patch file for the installed firmware (the other one stops itself).
call /dev_hdd0/ps3-dvd-rgb/fix-4.92.bat
call /dev_hdd0/ps3-dvd-rgb/fix-4.93.bat
""")
for fw, log in VERS.items():
    h = cave(fw)
    with open(os.path.join(OUT, 'ps3-dvd-rgb', f'fix-{fw}.bat'), 'w') as f:
        f.write(f"""# ================================================================================
#  DVD fixes for PS3 firmware {fw} CEX  (called by /dev_hdd0/autoexec.bat)
# ================================================================================
#  Every command line below is a webMAN memory write:
#    setmem  proc=0x1000300 (VSH, the XMB)  addr=<address>  val=<new bytes>
#  To turn one fix off, put a # at the start of its command line(s), then reboot.
# ================================================================================

# This file only works on firmware {fw}: on any other firmware, stop now.
abort if not Firmware {fw}

# --------------------------------------------------------------------------------
#  FIX 1: MACROVISION OFF                                        (one command)
# --------------------------------------------------------------------------------
#  Address 0x473A48 is in the function the DVD/BD player calls to switch analog
#  Macrovision copy protection on or off. The original instruction passes the
#  player's request along (mr r31,r4 = 7C9F2378). The new one always passes 0
#  (li r31,0 = 3BE00000), so the request is always "Macrovision off".
#  Original bytes, to undo it live: 7C9F2378.
{U}&addr=473A48&val=3BE00000

# --------------------------------------------------------------------------------
#  FIX 2: FORCE RGB OVER SCART                         (four commands, in order)
# --------------------------------------------------------------------------------
#  Why the picture goes green: when DVD playback starts, VSH tells the AV chip to
#  run the AV MULTI (SCART) port in YCbCr colour. The analog encoder then puts
#  YCbCr onto the R/G/B pins, so the TV shows green.
#  The fix: a small routine that checks every command VSH sends to the AV chip.
#  In setups for the AV MULTI port it sets the colour fields back to RGB first:
#    - video mode "output format" 9 (YCbCr) changed to 0 (RGB)
#    - AV MULTI colour space out/in YCbCr changed to RGB/RGB
#  It also keeps a copy of each command in a log buffer (for debugging).

#  2a. Write the routine into free space at the end of VSH's code
#      (0x6BBEB0-0x6BBFFF, 336 bytes, in two chunks of 256 and 80 bytes).
{U}&addr=6BBEB0&val={h[:512]}
{U}&addr=6BBFB0&val={h[512:]}

#  2b. Empty the routine's log buffer (free memory at 0x{log:X}).
{U}&addr={log:X}&val=00000000

#  2c. Switch it on: redirect VSH's "send to AV chip" function (0x5DED64) to the
#      routine (branch to 0x6BBEB0). This must be the last command, so the routine
#      is fully written before anything uses it.
#      Original bytes, to undo it live: 38A00002.
{U}&addr=5DED64&val=480DD14C
""")
    print('wrote fix-%s.bat' % fw)
