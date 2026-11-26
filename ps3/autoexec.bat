# ================================================================================
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
