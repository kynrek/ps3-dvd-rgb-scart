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

## 11. Before the 4.93 upgrade (2026-11-26)
- GitHub: private repo https://github.com/kynrek/ps3-dvd-rgb-scart (`~/projects/ps3-dvd-rgb-scart`).
  It has the docs, scripts, packet logs and autoexec.bat. The SCE package key was removed from ps3fw.py (env var), along with the MAC.
- Backups in `backup/`:
  - the NOR dump;
  - `devflash_4.92_20261126/` (dev_flash, dev_flash2, dev_flash3);
  - `hdd0_config_20261126/` (autoexec.bat, boot_plugins.txt, the webMAN sprx files, wm_config.bin, cobra_cfg.bin).
- The current CFW is Evilnat 4.92 CEX Cobra 8.5. The network-menu XML points at evilnat.github.io, and that site is now 404.
- WARNING: github.com/PlayStation-3-Slim-Evilnat-CFW is a FAKE Evilnat org. Its README is copied from PS3HEN, and its download button goes
  to a third-party file host. Don't use it. Real releases: the Evilnat thread on PSX-Place (it blocks automated fetches).

## 12. 4.93 support (prepared 2026-11-26, before the upgrade)
- Official 4.93 VSH vs the console's 4.92 VSH: same segment layout. 14,429 of 1.75M code words differ, mostly TOC/data
  offsets. The patched functions (sys_uart_send wrapper 0x5ded54, FUN_00473a28) and the cave area are byte-identical.
  The 4.93 bss is 0xc0 bytes longer (ends 0x751548 instead of 0x751488), so on 4.93 the packet log moves to **0x751600**.
  The 4.93 cave differs from the 4.92 one in a single word (0x6bbf88, `ori r9,r9,0x1600`).
- `scripts/mkcave_fix.py --fw=4.92|4.93` and `scripts/mkbat.py` generate:
  - `ps3files/autoexec.bat`: waits for the XMB, skips if L1 is held, then `call`s both version scripts;
  - `ps3files/ps3-dvd-rgb/fix-4.92.bat` and `fix-4.93.bat`: each starts with `abort if not Firmware X`.
- On the PS3: `/dev_hdd0/autoexec.bat`, `/dev_hdd0/ps3-dvd-rgb/fix-4.92.bat`, and `fix-4.93.bat.off`.
  The 4.93 script stays switched off until the upgraded console's VSH bytes have been checked live. Then rename it to `fix-4.93.bat`.
- Tested on 4.92: I removed the patches and ran the dispatcher, and they were reapplied (cave identical). Running fix-4.93.bat directly
  on 4.92 aborted with no writes (the 0x751600 marker and the cave were unchanged).
- `scripts/ps3-dvd-rgb-apply.sh` reads the firmware from webMAN's cpursx page and supports both versions.
  `PS3FW=4.93 readlog.py` reads the 4.93 log.

## 13. Evilnat 4.93 CEX PUP checked; scripts unified (2026-11-26)
- The user sent `CFW 4.93 Evilnat Cobra 8.5 [CEX].rar` over LocalSend (sha256 8735f814…). It contained README.txt, md5.txt and PS3/UPDATE/PS3UPDAT.PUP.
  The PUP MD5 d3af31ce6bdbc6790a5504cf8b3da1b2 matches md5.txt, but that only proves it wasn't damaged.
  Extracted to `cfw493/` (rar/, pup/, upd/, flash/ decrypted).
- Compared with Sony's official 4.93 (downloaded from Sony's server):
  - The PUP version string is "4.93 Evilnat [CEX]".
  - The package list is the same. CORE_OS and the dev_flash packages differ.
  - dev_flash: +37 / -2 / ~44 files, all the usual Evilnat set: stage2 Cobra, xai_plugin, trophy_unlocker, videorec,
    patched bdplayer/emus/plugins, icons, XMB XMLs. Every Evilnat addition is also on the console's current Evilnat 4.92.
  - vsh.self: 249 changed code words and 1 data word versus OFW. None are near 0x5ded54, 0x473a28 or 0x472xxx, and none
    reference the cave or the bss tail. The patch-site bytes are original. Segments are identical in size to OFW 4.93.
- webMAN MOD (latest source, LATEST_CFW 4.92) has no 4.93 build-date constant. On 4.93 it falls back to
  `get_firmware_version()` (syscall platform info), and I couldn't confirm statically which string that produces.
  So the log address is now **0x751600 on both versions**: it's free on both, because bss ends at 0x751488 on 4.92 and 0x751548 on 4.93.
  fix-4.92.bat and fix-4.93.bat now write byte-identical patches, so a misreported 4.92/4.93 is harmless. Any other
  string means nothing gets applied, which is safe.
- The unified cave was reapplied on 4.92 with ps3-dvd-rgb-apply.sh and verified. fix-4.93.bat is now enabled on the PS3 (the `.off` copy was removed).
- Gotcha: webMAN refuses `/mount.ps3/<script>` while a game is running ("Error! Click to quit the game").
  Run script tests from the XMB.

## 14. Upgraded to Evilnat 4.93 CEX (2026-11-26)
- The update ran from the PS3 HDD, with no USB stick:
  - Uploaded the PUP to `/dev_hdd0/GAMES/PS3UPDATE_493/PS3/UPDATE/PS3UPDAT.PUP` over FTP; its MD5 on the console matched.
  - Mounted the folder as a disc with `http://<ps3>/mount.ps3/dev_hdd0/GAMES/PS3UPDATE_493`.
  - XMB → System Update → Update via Storage Media found it on the "disc".
  - The PS3 went offline after 19 s, and webMAN was back after 254 s.
- After the update:
  - version.txt says `release:04.9300`, build 68500 (2026-01-08). webMAN 1.47.48n reports "Firmware: 4.93 CEX Cobra 8.5".
  - The installed vsh.self sha1 is e487318d…, identical to the checked Evilnat PUP copy.
  - boot_plugins.txt (webMAN) and autoexec.bat survived.
  - **The boot script applied the fix by itself.** On 4.93, hook 0x5ded64 = 480DD14C, nomv 0x473a48 = 3BE00000, and the cave is byte-identical; the log is at 0x751600.
- The PUP was deleted from the PS3 HDD at the user's request. The verified copy is kept on r720 at `cfw493/rar/PS3/UPDATE/PS3UPDAT.PUP` (md5 d3af31ce…); for Recovery Mode, copy it to a USB stick.

## 15. DVD region lock (checked 2026-11-26)
- The DVD-Video region check is in `dev_flash/vsh/module/bdp_disccheck_plugin.sprx`. Function 0x1478 returns error 0x67 when
  `bl 0x1360` (region test) fails. 0x1360 maps the console target (lhz +0x72, 0x84 = USA → DVD region 1 bit) and ANDs it with the
  disc's region mask (+0x34), so a set bit means the disc is blocked.
- **Already disabled by Cobra 8.5** (Evilnat stage2.bin): its patch table has hash 0x9940000000003000 → {0x152C, `38600001` li r3,1,
  condition_true} (stage2.bin file offset 0x17250). That's the same as MAMBA's `dvd_video_region_check_offset` ("kills standard
  dvd-video region protection, not RCE"). The hash2 top 20 bits (0x99400) match both the OFW and the Evilnat plugin.
- Evilnat's flash copy of the plugin also changes 0x15C8/0x15D4 `li r9,0x66/0x65` → `li r9,0`, which removes the 0x65/0x66 errors.
  Their bdp_BDVD.self changes are only the Cinavia stubs (0x15ECD0/0x15ECFC → blr).
- The plugin loads only when a disc goes in and comes fresh from flash each time, so a boot-time setmem (like the RGB fix) can't
  patch it; Cobra patches it at module load. To verify live, insert a DVD and search VSH memory for `808100743860000139200067`
  (patched) vs `808100744BFFFE3539200067` (original).
- Not covered: RCE discs (they read the player region from SPRM20). For those, use webMAN Setup → DVD region (Cobra
  dvd_video_region, which fakes syscall 867 0x19004 buf[3] for _main_bdp_BDVD.self).
