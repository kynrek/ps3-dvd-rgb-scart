# Combined cave for VSH 4.92 sys_uart_send (hook 0x5ded64): rewrite AVB_PARAM packets that drive the
# AV MULTI port so the RSX bus stays RGB (video-mode word6 := 0, AV_VIDEO_CS cs_in := 0), then log.
import re, sys
from keystone import *
from capstone import *
CAVE=0x6bbeb0; RET=0x5ded68
# Packet-log buffer in the unused bss page tail: 4.92 bss ends 0x751488, 4.93 bss ends 0x751548.
LOGS={'4.92':0x751500,'4.93':0x751600}
FW=next((a.split('=')[1] for a in sys.argv if a.startswith('--fw=')),'4.92'); LOG=LOGS[FW]
fix=f"""
  rldicl r5, r3, 0, 32
  lwz r0, 4(r5)
  lis r7, 0x400
  ori r7, r7, 1
  cmpw cr7, r0, r7
  bne cr7, LOG
  lhz r8, 2(r5)
  addi r8, r8, 4
  add r8, r5, r8
  li r9, 0
  addi r6, r5, 16
A1:
  addi r0, r6, 8
  cmplw cr7, r0, r8
  bgt cr7, A3
  lhz r10, 2(r6)
  addi r10, r10, 4
  cmplwi cr7, r10, 8
  blt cr7, A3
  lwz r0, 4(r6)
  lis r7, 1
  ori r7, r7, 1
  cmpw cr7, r0, r7
  bne cr7, A2
  lhz r0, 8(r6)
  rlwinm r0, r0, 0, 16, 30
  cmpwi cr7, r0, 0x10
  bne cr7, A2
  li r0, 0
  stw r0, 12(r6)
  li r9, 1
A2:
  add r6, r6, r10
  b A1
A3:
  cmpwi cr7, r9, 0
  beq cr7, LOG
  addi r6, r5, 16
B1:
  addi r0, r6, 8
  cmplw cr7, r0, r8
  bgt cr7, LOG
  lhz r10, 2(r6)
  addi r10, r10, 4
  cmplwi cr7, r10, 8
  blt cr7, LOG
  lwz r0, 4(r6)
  lis r7, 0x100
  ori r7, r7, 2
  cmpw cr7, r0, r7
  bne cr7, B2
  cmplwi cr7, r10, 0x30
  blt cr7, B2
  li r0, 0
  stw r0, 32(r6)
B2:
  add r6, r6, r10
  b B1
LOG:
  lis r9, {LOG>>16:#x}
  ori r9, r9, {LOG&0xffff:#x}
  lwz r10, 0(r9)
  lwz r0, 4(r5)
  rlwinm r0, r0, 0, 0, 30
  lis r7, 3
  ori r7, r7, 4
  cmpw cr7, r0, r7
  beq cr7, L3
  cmpwi cr7, r4, 0
  beq cr7, L3
  add r7, r10, r4
  addi r7, r7, 4
  cmplwi cr7, r7, 0x9f0
  bgt cr7, L3
  add r6, r9, r10
  stw r4, 4(r6)
  addi r6, r6, 8
  mr r7, r5
  mtctr r4
L2:
  lbz r0, 0(r7)
  stb r0, 0(r6)
  addi r7, r7, 1
  addi r6, r6, 1
  bdnz L2
  add r10, r10, r4
  addi r10, r10, 7
  rlwinm r10, r10, 0, 0, 29
  stw r10, 0(r9)
L3:
  li r5, 2
  b {RET:#x}
"""
ks=Ks(KS_ARCH_PPC, KS_MODE_PPC64|KS_MODE_BIG_ENDIAN)
enc,_=ks.asm(re.sub(r"\br(\d+)", r"\1", fix).replace("cr7","7"), CAVE); blob=bytes(enc)
assert CAVE+len(blob) <= 0x6bc000, hex(CAVE+len(blob))
if '-v' in sys.argv:
    for i in Cs(CS_ARCH_PPC, CS_MODE_64|CS_MODE_BIG_ENDIAN).disasm(blob,CAVE): print(f'# {i.address:#x} {i.mnemonic} {i.op_str}')
print(f'END {CAVE+len(blob):#x}')
print(blob.hex().upper())
hook,_=ks.asm(f"b {CAVE:#x}", 0x5ded64); print('HOOK', bytes(hook).hex().upper())
