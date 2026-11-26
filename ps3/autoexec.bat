# PS3 DVD over RGB SCART fix + Macrovision off (RAM-only VSH patches), 4.92 and 4.93 CEX.
# https://github.com/kynrek/ps3-dvd-rgb-scart  -  disable: delete /dev_hdd0/autoexec.bat and reboot.
wait xmb
# Hold L1 while the XMB appears to skip the patches this boot
abort if L1
call /dev_hdd0/ps3-dvd-rgb/fix-4.92.bat
call /dev_hdd0/ps3-dvd-rgb/fix-4.93.bat
