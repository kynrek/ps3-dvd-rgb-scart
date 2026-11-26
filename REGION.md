# DVD region lock on the PS3 (4.92 / 4.93 CEX): where it is and what disables it

Short version: on a console running **Cobra 8.x** (e.g. Evilnat 4.92/4.93 CEX Cobra 8.5) the standard DVD-Video region
check is **already patched out** when the disc plugin loads. No extra patch is needed. `scripts/ps3-dvd-region-check.sh`
confirms it on a live console. Discs with RCE (Region Code Enhancement) need the webMAN *DVD Region* setting instead.

## Where the check is
- Not in the DVD player (`dev_flash/bdplayer/bdp_BDVD.self`), but in the VSH plugin
  **`dev_flash/vsh/module/bdp_disccheck_plugin.sprx`**, which VSH loads when a disc is inserted.
- Function **0x1478** (offsets are relative to the plugin's text segment) checks a disc and returns an error code:

  | Code | Check |
  |---|---|
  | 0x65 / 0x66 | a disc-vs-system type check (field +0x30 against a value from 0x0ef4); not analysed further |
  | **0x67** | **DVD-Video region**: only for disc type 0x0b, via `bl 0x1360` at **0x152C** |
  | 0x68 / 0x69 / 0x64 | other checks (0x7018 for disc type 8, fields +0x54 / +0x44); not analysed |

- **0x1360** is the region test. It reads the console's target/region code (0x0f00, halfword +0x72: 0x83 Japan,
  0x84 USA, 0x85 Europe, …), maps it through a jump table to a DVD region bit (region 1 = 0x01, 2 = 0x02, 3 = 0x04,
  4 = 0x08, 5 = 0x10, 6 = 0x20), and ANDs that with the disc's VMG region mask (byte +0x34; a set bit means "not allowed
  in this region"). It returns 1 when the disc may play.

```
0x1524: clrldi r3, r30, 0x20
0x1528: lwz    r4, 0x74(r1)
0x152c: bl     0x1360          <- region test            (80810074 4BFFFE35 39200067)
0x1530: li     r9, 0x67        <- error code if it fails
0x1534: clrlwi r3, r3, 0x18
0x1538: cmpwi  cr7, r3, 0
0x153c: beq    cr7, 0x15dc     -> return 0x67
```

## What patches it
- **Cobra 8.x stage2** patches the plugin in memory each time it is loaded (the module-load hook in `modulespatch.c`; the
  open-source MAMBA payload in ManaGunZ has the same table). For the module with hash `0x9940000000003000`
  it writes **`0x152C: 38600001` (`li r3,1`)**, so the region test always passes. In MAMBA this is
  `dvd_video_region_check_offset` ("Kills standard dvd-video region protection (not RCE one)"); it is 0x1528 on older firmware.
  - Checked in Evilnat 4.93 CEX Cobra 8.5 `dev_flash/sys/stage2.bin`: the patch table entry is at file offset 0x17250
    (`0000152C 38600001 <condition_true>`).
  - Cobra recognises the module by the XOR of 8 words at +0x2C0 in the decrypted text (top 20 bits) plus the size.
    That gives 0x99400 for both Sony's 4.93 plugin and Evilnat's modified one, so the patch applies to both.
- **Evilnat's flash copy** of the plugin also changes `0x15C8 li r9,0x66` and `0x15D4 li r9,0x65` to `li r9,0`, so the
  0x65/0x66 type mismatch returns "OK". Evilnat's `bdp_BDVD.self` changes are only the Cinavia stubs
  (0x15ECD0 and 0x15ECFC → `blr`), unrelated to region.

## Why it's not a boot script like the RGB fix
The RGB fix patches VSH itself, which stays in memory, so one write at boot is enough. `bdp_disccheck_plugin.sprx` is
loaded fresh from flash whenever a disc is inserted, so a boot-time `setmem` would be lost. The patch has to be applied as
the module loads, which Cobra already does. (On firmware without Cobra, e.g. PS3HEN, it would have to be re-applied
after inserting each disc; that isn't provided here.)

## RCE discs and the DVD Region setting
Some region 1 (and a few UK region 2) discs carry RCE: the disc's own navigation program reads the player's region
(SPRM 20) and refuses to play if it doesn't match. Patching the plugin doesn't change the player region, so for those
discs set **webMAN Setup → DVD Region** to the disc's region. That stores `dvd_video_region` in the Cobra config, and
Cobra then fakes the region byte returned by syscall 867 (`0x19004`, `buf[3]`) to `_main_bdp_BDVD.self`.

## Checking on a console
Insert a DVD (the plugin is only loaded while a disc is in), then run:
```
./scripts/ps3-dvd-region-check.sh [ps3-ip]
```
It searches VSH memory over webMAN (read-only) for the patched (`80810074 38600001 39200067`) or original
(`80810074 4BFFFE35 39200067`) bytes. Exit code: 0 = patched, 2 = not patched, 3 = plugin not loaded, 1 = PS3 offline.
