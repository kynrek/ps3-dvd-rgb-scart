# ================================================================================
#  DVD fixes for PS3 firmware 4.93 CEX  (called by /dev_hdd0/autoexec.bat)
# ================================================================================
#  Every command line below is a webMAN memory write:
#    setmem  proc=0x1000300 (VSH, the XMB)  addr=<address>  val=<new bytes>
#  To turn one fix off, put a # at the start of its command line(s), then reboot.
# ================================================================================

# This file only works on firmware 4.93: on any other firmware, stop now.
abort if not Firmware 4.93

# --------------------------------------------------------------------------------
#  FIX 1: MACROVISION OFF                                        (one command)
# --------------------------------------------------------------------------------
#  Address 0x473A48 is in the function the DVD/BD player calls to switch analog
#  Macrovision copy protection on or off. The original instruction passes the
#  player's request along (mr r31,r4 = 7C9F2378). The new one always passes 0
#  (li r31,0 = 3BE00000), so the request is always "Macrovision off".
#  Original bytes, to undo it live: 7C9F2378.
/setmem.ps3mapi?proc=0x1000300&oper=0&addr=473A48&val=3BE00000

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
/setmem.ps3mapi?proc=0x1000300&oper=0&addr=6BBEB0&val=78650020800500043CE0040060E700017F803800409E00C0A1050002390800047D0542143920000038C50010380600087F804040419D004CA1460002394A00042B8A0008419C003C800600043CE0000160E700017F803800409E0020A00600085400043C2F800010409E0010380000009006000C392000017CC652144BFFFFB02F890000419E005038C50010380600087F804040419D0040A1460002394A00042B8A0008419C0030800600043CE0010060E700027F803800409E00142B8A0030419C000C38000000900600207CC652144BFFFFBC3D2000756129160081490000800500045400003C3CE0000360E700047F803800419E00542F840000419E004C
/setmem.ps3mapi?proc=0x1000300&oper=0&addr=6BBFB0&val=7CEA221438E700042B8709F0419D003C7CC952149086000438C600087CA72B787C8903A6880700009806000038E7000138C600014200FFF07D4A2214394A0007554A003A9149000038A000024BF22D6C

#  2b. Empty the routine's log buffer (free memory at 0x751600).
/setmem.ps3mapi?proc=0x1000300&oper=0&addr=751600&val=00000000

#  2c. Switch it on: redirect VSH's "send to AV chip" function (0x5DED64) to the
#      routine (branch to 0x6BBEB0). This must be the last command, so the routine
#      is fully written before anything uses it.
#      Original bytes, to undo it live: 38A00002.
/setmem.ps3mapi?proc=0x1000300&oper=0&addr=5DED64&val=480DD14C
