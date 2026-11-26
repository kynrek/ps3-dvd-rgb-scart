# PS3 DVD over RGB SCART turns green: reverse-engineering notes

> Full chronological work log: [WORKLOG.md](WORKLOG.md). Flash backup: `backup/`.

**Problem.** A CFW PS3 on RGB SCART at 480i looks fine. DVD playback is green: the AV MULTI port
switches to Y Pb Pr. Setting "BD/DVD Video Output Format (HDMI)" to RGB doesn't help, because that
setting only covers HDMI.

## What's here
- `fw/PS3UPDAT-4.93.PUP`: official 4.93 firmware (US). `fw/flash/` is the decrypted dev_flash
  (`*.elf` = decrypted SELF/SPRX). `fw/coreos/` holds lv1 and lv2.
- `scripts/ps3fw.py`: PUP unpack, SCE package decrypt, and SELF decrypt (keys read from RPCS3's
  `tools/rpcs3-src/rpcs3/Crypto/key_vault.cpp`). `scripts/cos.py` unpacks CORE_OS.
- `scripts/dis.py`: capstone PPC64 disassembler with TOC string annotation. `scripts/prx.py`:
  import/export table scanner.
- `ghidra/`: Ghidra 12.2 project `vsh` (analysed vsh.self), `decomp.sh <proj> <out> <hexaddr…>`,
  plus the decompile outputs `d*.txt`.
- `scripts/ps3mapi_patch.py`: RAM-only VSH patcher over PS3MAPI (TCP 7887). Untested.

## Findings (VSH 4.93)
- The DVD player `dev_flash/bdplayer/bdp_BDVD.self` never touches the AV hardware itself: it
  makes no AV-UART syscalls and doesn't import cellVideoOut.
- VSH has a built-in `libavset` (0x5da000–0x5e0000). It sends ps3av-style packets to the lv1 AV
  manager over `sys_uart` (syscalls 367–369). Port codes: 0/1 = HDMI, 0x10/0x11 = AV MULTI,
  0x20/0x21 = SPDIF (`FUN_004712f4`).
- `bdp_plugin.sprx` gets the AV-settings interface from xsetting NID 0x4712f276 (table at 0x6fdcf4).
  - Slot 0x50 → `0x453c00` → `0x44dc98` → `FUN_00473a28` → `avset_setmv` thunk `0x5d8b8c`.
    This is the only caller of setmv: analog Macrovision on/off, and it only acts for analog
    port states 4/5.
  - Slot 0x110 → `0x456ab0` → `0x44d6d0` → `FUN_00472670` → `avset_cs_direct`. This is the
    RGB / YCbCr colour selection (cs values 1 = RGB, 2/4/8 = YCbCr variants).
- `FUN_00473ba4` sets CGMS/WSS (`avset_setcgmswss`) and `avset_addsigctrl`.

## Hypothesis and patch 1 (`nomv`)
Sony's players switch analog RGB to component when Macrovision is required. The PS2 manual
documents this, and RGB can't carry Macrovision. My guess is that VSH or the lv1 AV manager makes
this switch when setmv turns MV on.

**Patch 1 (`nomv`):** at `0x473a48`, replace `mr r31,r4` (`7c9f2378`) with `li r31,0`
(`3be00000`). Every setmv request then becomes "off". It's applied in VSH RAM only, so a reboot
reverts it.

**Test:** play a pressed (Macrovision) DVD, and ideally also a home-burned DVD-Video.
- If the burned disc is already fine and the pressed one is green, Macrovision is the trigger.
- If both are green, the trigger is the colour path (slot 0x110), not setmv, and patch 2 would
  go there.

## Status
Waiting on the console: it wasn't found on the LAN (no FTP on :21, no Sony MAC address) on
2026-11-25.

## 2026-11-25: applied on the console
- PS3: 192.168.1.239 (Ethernet, MAC <console MAC>). Firmware 4.92 CEX, Cobra 8.5, webMAN MOD 1.47.48.
  The PS3MAPI TCP port 7887 is off, so the patch goes through webMAN's HTTP memory pages.
- The 4.92 vsh.self (pulled from the console into `fw492/`) has an identical libavset, and
  FUN_00473a28 is at the same address. The patch site 0x473a48 = 7c9f2378 there too.
- Apply (RAM only, lost on reboot):
  `curl "http://192.168.1.239/setmem.ps3mapi?proc=0x1000300&addr=473A48&oper=0&val=3BE00000"`
- Undo: the same command with `val=7C9F2378`.
- Check: `curl -s "http://192.168.1.239/getmem.ps3mapi?proc=0x1000300&addr=473A48&len=4" | grep -o "00473A48.*"`

## 2026-11-25: green found; patch 2 (`avrgb`)
- Not fixed by `nomv` alone. Snapshots of the VSH AV objects (`scripts/avsnap.py`, saved in `snaps/`)
  show that on DVD start the AV MULTI port object (vtable 0x6ca268, +0x40 = 2 → port 0x10) has its
  state (+0x64 → +0x8) changed from 1 (RGB) to 2 (YCbCr). The port's own configured colour (+0x94) stays 1.
- Patch 2 sits in `FUN_004723b0` (colour normaliser, used by SetRouteAndColor, cs_direct and configure).
  For analog ports (+0x40 = 2 or 3) it uses the port's configured colour +0x94 instead of the request.
  - Hook: 0x4723c0 `80040000` (lwz r0,0(r4)) → `48249B40` (b 0x6bbf00).
  - Cave: 0x6bbf00 (unused tail of the text page) =
    `800300405400003C2F80000280040000409E000C80030094900400004BDB64A8`
  - Undo: put `80040000` back at 0x4723c0 (the cave can stay).
- Both patches are RAM only and must be re-applied after every reboot.

## 2026-11-25: root cause found in the AV packets; patch 3 (`avfix`)
- Patch 2 kept the VSH colour state at RGB but the picture stayed green, so it was removed
  (0x4723c0 is back to 80040000).
- A logging hook on libavset's `sys_uart_send` wrapper (0x5ded54; hook at 0x5ded64) captured the packets
  (`snaps/avlog_*.txt`, decoded by `scripts/readlog.py`). On DVD launch the AVB_PARAM (0x04000001) packet has:
  - VIDEO_MODE (0x01000002) word6 = 9 (YCbCr bus); on the XMB it's 0.
  - AV_VIDEO_CS (0x00010001) for avport 0x10: cs_out = 0 (RGB), cs_in = 1 (YCbCr); on the XMB it's 0/0.
  - The SCART encoder doesn't convert, so YCbCr goes out on the RGB pins: green.
- Patch 3 (`scripts/mkcave_fix.py`, cave 0x6bbeb0..0x6bc000, hook 0x5ded64 `38A00002` → `480DD14C`):
  in AVB packets with an AV_VIDEO_CS for port 0x10/0x11 it sets cs_in = 0 and every VIDEO_MODE word6 = 0,
  then logs the packet (log at 0x751500, polls 0x0003000[45] skipped).
- Undo: put `38A00002` back at 0x5ded64.

## 2026-11-26: WORKING
- The final cave zeroes the whole cs_out/cs_in word (`stw r0,12(r6)`) as well as video-mode word6.
  The user confirmed correct colour on DVD playback over RGB SCART.
  The launch packet (`snaps/avlog_launch_fixed.txt` #53) now matches the XMB one: RGB bus, cs 0/0.
- Active patches: `nomv` (0x473a48) and `avfix` (hook 0x5ded64 → cave 0x6bbeb0). Both are RAM only.
- Re-apply after a reboot: `scripts/ps3-dvd-rgb-apply.sh [ip]`. It's idempotent and checks bytes first.
