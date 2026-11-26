# PS3 DVD playback over RGB SCART: green picture fix (4.92 / 4.93 CEX)

On a CFW PS3 using an **RGB SCART** cable, DVD playback comes out **green**. The DVD player asks the AV system for a
YCbCr pipeline, and the AV MULTI encoder puts YCbCr on the RGB pins. The XMB setting "BD/DVD Video Output Format (HDMI)"
doesn't help, because it only covers HDMI.

This repo has a reverse-engineered, **RAM-only** VSH patch for firmware **4.92 and 4.93 CEX (Evilnat Cobra 8.5)** that
rewrites the AV packets so the AV MULTI port stays RGB, plus an optional Macrovision-off patch. Tested on a real console
on both firmware versions: DVDs play in correct colour over RGB SCART. Nothing in flash is modified; a reboot without the
boot script undoes it.

It also documents the **DVD region lock** ([REGION.md](REGION.md)): where the check is, and that Cobra 8.x already
patches it out, with a script to confirm that on a live console.

## Requirements
- CFW 4.92 or 4.93 CEX with Cobra (tested: Evilnat Cobra 8.5) and **webMAN MOD** (its web server applies the patches).
- On any other firmware the scripts change nothing.

## Install (boot script, applied at every boot)
1. Copy `ps3/autoexec.bat` to `/dev_hdd0/autoexec.bat` and the folder `ps3/ps3-dvd-rgb/` to `/dev_hdd0/ps3-dvd-rgb/`
   (webMAN FTP works).
2. Reboot. webMAN runs `autoexec.bat` once the XMB is up. It calls `fix-4.92.bat` and `fix-4.93.bat`; each one aborts
   unless the console runs that firmware.
- Hold **L1** while the XMB appears to skip it for that boot. Delete `autoexec.bat` to remove it.
- Regenerate the scripts with `scripts/mkbat.py` (the patch bytes come from `scripts/mkcave_fix.py`).

Or apply once from a PC: `scripts/ps3-dvd-rgb-apply.sh <ps3-ip>` (idempotent; checks the original bytes first).

## What the patches do
| Patch | Address (VSH) | Change |
|---|---|---|
| `nomv` (Macrovision off) | 0x473a48 | `mr r31,r4` → `li r31,0`: every setmv request becomes "off" |
| `avfix` (force RGB) | hook 0x5ded64 in libavset's `sys_uart_send` wrapper → cave 0x6bbeb0 | in AVB_PARAM packets for the AV MULTI port (0x10/0x11): AV_VIDEO_CS cs_out/cs_in = 0 (RGB) and VIDEO_MODE word 6 = 0 (RGB bus); packets are logged at 0x751600 |

The addresses and patch bytes are identical on 4.92 and 4.93 CEX. Details, packet captures and the dead ends are in the docs.

## Documentation
- [WORKLOG.md](WORKLOG.md): the full investigation, in order (firmware unpacking, Ghidra analysis, AV object
  snapshots, packet logging, the failed patches, 4.93 port and upgrade).
- [NOTES.md](NOTES.md): the working notes and findings about VSH's `libavset`.
- [REGION.md](REGION.md): the DVD region check in `bdp_disccheck_plugin.sprx` and how Cobra disables it.
- `logs/`: captured AV packets (XMB vs DVD launch, before and after the fix, 4.93), decoded by `scripts/readlog.py`.

## Scripts
| Script | Purpose |
|---|---|
| `ps3-dvd-rgb-apply.sh` | apply the RGB / Macrovision patches over webMAN HTTP |
| `ps3-dvd-region-check.sh` | read-only check that the DVD region check is patched (insert a DVD first) |
| `mkcave_fix.py`, `mkcave_log.py`, `mkbat.py` | assemble the patch cave (keystone) and generate the boot scripts |
| `vshmem.py`, `avsnap.py`, `readlog.py` | read VSH memory, snapshot AV objects, decode the packet log (`PS3_IP` env var) |
| `ps3fw.py`, `cos.py` | PUP unpack, SCE package and SELF decrypt, CORE_OS unpack (**keys not included**; SELF keys are read from an RPCS3 source checkout) |
| `dis.py`, `prx.py` | capstone PPC64 disassembler with TOC string annotations; PRX import/export scanner |
| `ps3mapi_patch.py` | the same patch over the PS3MAPI TCP port (untested) |
| `ghidra/` | headless Ghidra decompile helper scripts |

## Notes
- No Sony firmware files, keys, decompiled Sony code or console data are included.
- Use at your own risk. The patches only touch RAM, but they modify a running system process.
- Developed with Claude Code (Anthropic).
