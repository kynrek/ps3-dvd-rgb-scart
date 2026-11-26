# PS3 DVD playback is green over RGB SCART: full work log

Sessions on 2026-11-25 and 2026-11-26, with Claude Code on r720 in `~/claude/ps3`.

## 1. The problem
- The console is a CFW PS3 (NOR model), on 4.92 CEX with Cobra 8.5 and webMAN MOD 1.47.48. On the LAN it's
  **192.168.1.239** (Ethernet, MAC <console MAC>).
- Video goes out through the AV MULTI port on an RGB SCART cable, at 480i, to a CRT TV. The XMB and games look right.
- When a DVD plays, the picture turns green. The TV's input banner pops up the moment the DVD player
  starts, so the player is resetting the video mode.
- The XMB option "BD/DVD Video Output Format (HDMI) → RGB" makes no difference, because it only covers HDMI.
- What the user asked for: fix it in the CFW or player rather than accept workarounds, and keep Macrovision off.

## 2. Outcome
**Fixed (2026-11-26):** a pressed DVD now plays in correct colour over RGB SCART. The user confirmed this.
Two RAM-only patches to VSH are applied through webMAN. They are lost on reboot. To re-apply:
```
./scripts/ps3-dvd-rgb-apply.sh            # idempotent, checks the original bytes first
```
| Patch | Where (VSH 4.92) | Bytes | What it does |
|---|---|---|---|
| `nomv` | 0x473a48 in `FUN_00473a28` | `7C9F2378` → `3BE00000` | `mr r31,r4` → `li r31,0`: every Macrovision (avset_setmv) request becomes "off" |
| `avfix` hook | 0x5ded64 in the sys_uart_send wrapper | `38A00002` → `480DD14C` (`b 0x6bbeb0`) | sends every AV packet through the cave |
| `avfix` cave | 0x6bbeb0–0x6bc000 (unused tail of the text page) | built by `scripts/mkcave_fix.py` | rewrites AVB_PARAM packets for the AV MULTI port so everything stays RGB (see §6), and logs packets to 0x751500 |

Undo: write back the original bytes above, or just reboot.

A full NOR flash backup was taken on 2026-11-26, before anything permanent was attempted (§8).

## 3. Tools built (all in `~/claude/ps3`)
- `fw/PS3UPDAT-4.93.PUP`: the official US 4.93 firmware, from Sony's update server.
  - `fw/upd/`: the PUP's update tar.
  - `fw/flash/`: the decrypted dev_flash (`*.elf` = decrypted SELF/SPRX).
  - `fw/coreos/`: lv1, lv2 and the rest of CORE_OS.
- `fw492/vsh.self(.elf)`: the console's own 4.92 VSH, pulled over FTP from `/dev_flash/vsh/module/vsh.self`.
- `scripts/ps3fw.py`: PUP unpacker, SCE package (dev_flash tar) decryptor and SELF/SPRX decryptor, in Python
  with pycryptodome. Its logic follows RPCS3's `Crypto/unself.cpp`, and it reads the keys from RPCS3's `key_vault.cpp`
  (sparse clone in `tools/rpcs3-src`).
- `scripts/cos.py`: unpacks CORE_OS.
- `scripts/dis.py`: PPC64 disassembler (capstone) that annotates TOC string references.
- `scripts/prx.py`: scans PRX import and export tables, for matching NIDs between modules.
- `ghidra/`: Ghidra 12.2 (with JDK 25 in `tools/jdk`), projects `vsh` (4.93) and `vsh492`. Decompile with
  `ghidra/decomp.sh <proj> <out> <hexaddr…>`; the output files are `ghidra/d*.txt`.
- `scripts/vshmem.py`: reads live VSH memory through webMAN's `getmem.ps3mapi` page.
- `scripts/avsnap.py`: snapshots and diffs the VSH AV-settings objects (saved in `snaps/*.json`).
- `scripts/readlog.py`: decodes the AV packet log the cave writes.
- `scripts/mkcave_log.py` and `scripts/mkcave_fix.py`: assemble the caves with keystone.
- `scripts/ps3mapi_patch.py`: PS3MAPI TCP client. Not used: PS3MAPI's port 7887 is off on this console.
- `scripts/ps3-dvd-rgb-apply.sh`: re-applies the fix.

To write memory, use webMAN's HTTP page:
`http://192.168.1.239/setmem.ps3mapi?proc=0x1000300&addr=<hex>&oper=0&val=<hexbytes>` (VSH pid 0x01000300).

## 4. Static reverse engineering (4.93, then checked on 4.92)
- The DVD player `dev_flash/bdplayer/bdp_BDVD.self` never talks to AV hardware: it makes no sys_uart
  calls and doesn't import cellVideoOut. Only `vsh.self` contains the sys_uart_send syscall (367–369).
- VSH has a built-in **libavset**, roughly 0x5d7000–0x5e0000:
  - Command names are in the TOC (`avset_setmv`, `avset_cs_direct`, `avset_setvideomode`, …), and API thunks sit at 0x5d74ec–0x5d9d8c.
  - It sends ps3av-style packets to the lv1 AV manager through `sys_uart_send` (wrapper at 0x5ded54).
  - Port codes (`FUN_004712f4`): 0/1 = HDMI, 0x10/0x11 = AV MULTI, 0x20/0x21 = S/PDIF.
- VSH's AV port classes:
  - Configure is `0x4730e0`, which calls "SetRouteAndColor" at `0x472784`.
  - `0x4723b0` normalises the colour space, `0x472478` sends cs_direct, and `0x473a28` is the only caller of avset_setmv.
  - `0x473ba4` handles CGMS/WSS and addsigctrl.
- `bdp_plugin.sprx` gets the AV-settings interface from xsetting NID 0x4712f276 (table 0x6fdcf4).
  - Slot 0x50 is Macrovision: 0x453c00 → 0x44dc98 → 0x473a28.
  - Slot 0x110 is colour: 0x456ab0 → 0x44d6d0 → 0x472670.
- Between 4.92 and 4.93 the libavset code is byte-identical and the AV class functions sit at the same
  addresses. The data and bss addresses differ: the AV singleton pointer is at 0x738b34 on 4.92 (0x738bf4 on 4.93).

## 5. Live experiments on the console (chronological)
1. **`nomv`** (Macrovision off). Still green, so Macrovision isn't the trigger. The patch was kept because the user wanted Macrovision off.
2. **AV-object snapshots** (`avsnap.py`, XMB vs DVD).
   - The AV MULTI port object is 0x20065e50 (vtable 0x6ca268, +0x40 = 2, so port 0x10). Its state object is
     0x20065bb0, and the colour field at +0x8 goes from 1 (RGB) to 2 (YCbCr) on DVD start.
   - Patch 2 put a cave in `FUN_004723b0` so analog ports always use their configured colour (+0x94).
   - With patch 2 on, VSH's state stayed at 1 (a call counter in the cave confirmed it ran), but the picture was still green.
   - Patch 2 was removed later; see the note under step 4.
3. **AV packet logger.** I hooked `sys_uart_send` at 0x5ded64, with a cave that copies each packet to 0x751500 (the unused bss tail).
   - Status polls 0x00030004 and 0x00030005 are skipped.
   - Logs: `snaps/avlog_before_launch.txt`, `avlog_launch.txt`, `avlog_launch_fix.txt`, `avlog_launch_fixed.txt`.
   - The DVD-launch AVB_PARAM (0x04000001) packet differs from the XMB one in exactly these places:
     - VIDEO_MODE (0x01000002), data word 6 (bus/output format): XMB **0**, DVD **9**.
     - AV_VIDEO_CS (0x00010001), avport 0x0010: XMB cs_out/cs_in **0/0**, DVD **0/1**. With patch 2 removed, VSH sent cs_out = 1 instead.
     - VIDEO_FORMAT (0x01000004), head 1: XMB 7, DVD 0x10. This was left alone.
4. **`avfix` v1** set cs_in = 0 and word 6 = 0. Still green: patch 2 was gone by then, so VSH sent cs_out = 1 (YCbCr out).
5. **`avfix` v2** zeroes the whole cs_out/cs_in word (`stw r0,12(r6)`) as well as word 6.
   **The colour is correct.** In the log, the launch packet is now identical to the XMB's.

## 6. Root cause (as understood)
The disc player asks for a YCbCr video pipeline: the RSX output bus is set to YCbCr (format 9), and the AV port
colour space is YCbCr in and/or out. The analog AV MULTI encoder doesn't convert colour space on the SCART RGB
pins. So the Y/Cb/Cr components come out on the G/B/R lines, and Y (brightness) lands on green.
Forcing the bus format and both colour-space fields back to RGB (0) for port 0x10/0x11 gives the TV a correct RGB
signal. The DVD framebuffer format (0x10) evidently still converts correctly onto an RGB bus.

## 7. Safety notes and gotchas
- Every patch is RAM-only (VSH process memory through webMAN). Nothing in dev_flash was changed.
- I checked the original bytes before every write. I unhooked before rewriting a cave and re-hooked afterwards.
- Caves live in the unused tail of VSH's text page (0x6bbea8–0x6bc000). The log and counter live in the unused
  bss tail (0x751488–0x752000). Never store into the text page from the cave.
- The cave's copy loop guards against zero length, which would otherwise mean `mtctr 0` and an endless `bdnz`.
- These addresses are for 4.92 only. After any firmware change, run the signature checks again; the apply script refuses on mismatched bytes.
- When a capture looks empty, confirm the user actually did the step first. One "empty" log was just "not launched yet".

## 8. Flash backup (2026-11-26)
- `backup/ps3_nor_flash_4.92_20261126.bin`, 16 MiB NOR, made with webMAN `dump.ps3?flash` and fetched over FTP twice (identical).
  - It has a `.sha256` file and `README.txt` alongside it. The directory is mode 700 and the files 600.
- Checked: magic 0FACE0FF/DEADBEEF, `IFI` at 0x200, region entries (asecure_loader, eEID, cISD, cCSD, cvtrm,
  ros0/ros1, CELL_EXTNOR_AREA), both ROS banks present. Not byte-swapped.
- It holds console-unique keys, so keep it private. A copy is also on the PS3 at `/dev_hdd0/dump_flash.bin`.

## 9. Next steps
- Automatic re-apply after a reboot. Either:
  - a cron job on r720 that runs `ps3-dvd-rgb-apply.sh` every few minutes (no flash risk), or
  - a permanent patched `vsh.self` (needs this backup plus resigning; riskier).
- Optionally drop the logging part of the cave once it's no longer needed, and test Blu-ray playback too
  (the same packet path probably fixes BD output on SCART).
- Movian (HTSS00003) is installed, but it wasn't needed.

## 10. On-PS3 auto-apply at boot (2026-11-26)
- Instead of a compiled Cobra boot plugin, I used webMAN MOD's startup script: `/dev_hdd0/autoexec.bat`.
  webMAN runs it at every boot (EVENT_AUTOEXEC, main.c), and each line containing `.ps3` is run as a webMAN web command.
  It uses the same `setmem.ps3mapi` writes, in order (do_web_command is called synchronously, include/feat/script.h).
  VSH's pid 0x01000300 is hard-coded in webMAN, so it's the same on every boot.
- The source copy is `ps3files/autoexec.bat`. It runs only on firmware 4.92 (`abort if not Firmware 4.92`)
  and waits for the XMB first. It writes the cave, resets the log, applies nomv, and writes the hook last.
- Tested without a reboot: I removed all the patches, ran `http://<ps3>/mount.ps3/dev_hdd0/autoexec.bat`,
  and after about 6 s the hook, nomv and the cave were all back (cave byte-identical).
- Disable: delete `/dev_hdd0/autoexec.bat` (FTP, or webMAN's file manager) and reboot. Nothing in flash changes.
- Caveat: the script doesn't verify the original bytes. A different 4.92 vsh.self (another CFW build) would need
  the addresses checked again first.
- The TV's green flash on exit/relaunch was its green input-name banner, not the picture (user, 2026-11-26).
