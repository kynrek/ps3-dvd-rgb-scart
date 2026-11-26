# PS3 DVD playback over RGB SCART: green picture fix (VSH 4.92)

On a CFW PS3 using an **RGB SCART** cable, DVD playback comes out **green**. The disc player asks the AV
system for a YCbCr pipeline, and the AV MULTI encoder puts YCbCr on the RGB pins. The XMB setting
"BD/DVD Video Output Format (HDMI)" doesn't help, because it only covers HDMI.

This repo has a reverse-engineered **RAM-only** VSH patch for firmware **4.92 and 4.93 CEX (Evilnat Cobra 8.5)**
that rewrites the AV packets so the AV MULTI port stays RGB. It also includes an optional Macrovision-off patch.
It was tested on a real console: DVDs play in correct colour over RGB SCART.

- `ps3/autoexec.bat` + `ps3/ps3-dvd-rgb/fix-4.92.bat`, `fix-4.93.bat`: webMAN MOD startup scripts that apply the patches at every boot.
  - Copy `autoexec.bat` to `/dev_hdd0/` and the folder to `/dev_hdd0/ps3-dvd-rgb/`.
  - Each version script runs only on its own firmware, so one install covers both. Regenerate with `scripts/mkbat.py`.
  - Hold **L1** while the XMB appears to skip it for that boot. Delete the file to remove it.
  - Nothing in flash is modified.
- `scripts/ps3-dvd-rgb-apply.sh`: applies the same patches from a PC over webMAN's HTTP `setmem`.
- `scripts/mkcave_fix.py`: assembles the patch (keystone).
- Other scripts in `scripts/`:
  - firmware unpacking and SELF decryption (`ps3fw.py`; keys not included);
  - live memory reading;
  - AV packet logging and decoding.
- `logs/`: the captured AV packets (XMB vs DVD launch, before and after the fix).
- `WORKLOG.md`: the full investigation. `NOTES.md`: notes taken along the way.

**Addresses apply to 4.92 and 4.93 CEX VSH**, and the patch bytes are identical on both. Every patch site matches, and
the log buffer at `0x751600` is free on both. 4.92 was tested on a console. 4.93 was checked against Sony's official 4.93 and is now confirmed on a console too; it was checked against
Evilnat's 4.93 CEX vsh.self (Evilnat's changes don't touch the patched code or the free areas).
On any other firmware the scripts do nothing. No Sony firmware files, keys or console data are included.
