# PS3 DVD playback over RGB SCART: green picture fix (VSH 4.92)

On a CFW PS3 using an **RGB SCART** cable, DVD playback comes out **green**. The disc player asks the AV
system for a YCbCr pipeline, and the AV MULTI encoder puts YCbCr on the RGB pins. The XMB setting
"BD/DVD Video Output Format (HDMI)" doesn't help, because it only covers HDMI.

This repo has a reverse-engineered **RAM-only** VSH patch for firmware **4.92 CEX (Evilnat Cobra 8.5)**
that rewrites the AV packets so the AV MULTI port stays RGB. It also includes an optional Macrovision-off patch.
It was tested on a real console: DVDs play in correct colour over RGB SCART.

- `ps3/autoexec.bat`: webMAN MOD startup script that applies the patches at every boot.
  - Copy it to `/dev_hdd0/autoexec.bat`.
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

**Addresses apply only to 4.92 CEX VSH** (vsh.self sha1 74deff6b9068985d948f1583cdb7482be9a3dbe8).
On any other firmware, check them again first. The startup script aborts on any firmware other than 4.92.
No Sony firmware files, keys or console data are included.
