# Build the sys_uart_send packet logger cave (VSH 4.92). Prints hex for the cave at 0x6bbf40.
import re
from keystone import *
from capstone import *
CAVE=0x6bbf40; RET=0x5ded68
asm=f"""
  lis r9, 0x75
  ori r9, r9, 0x1500
  lwz r10, 0(r9)
  rldicl r5, r3, 0, 32
  lwz r0, 4(r5)
  rlwinm r0, r0, 0, 0, 30
  lis r7, 3
  ori r7, r7, 4
  cmpw cr7, r0, r7
  beq cr7, L3
  mr r8, r4
  cmplwi cr7, r8, 0x200
  ble cr7, L1
  li r8, 0x200
L1:
  cmpwi cr7, r8, 0
  beq cr7, L3
  add r7, r10, r8
  addi r7, r7, 4
  cmplwi cr7, r7, 0x9f0
  bgt cr7, L3
  add r6, r9, r10
  stw r4, 4(r6)
  addi r6, r6, 8
  rldicl r5, r3, 0, 32
  mtctr r8
L2:
  lbz r0, 0(r5)
  stb r0, 0(r6)
  addi r5, r5, 1
  addi r6, r6, 1
  bdnz L2
  add r10, r10, r8
  addi r10, r10, 7
  rlwinm r10, r10, 0, 0, 29
  stw r10, 0(r9)
L3:
  li r5, 2
  b {RET:#x}
"""
ks=Ks(KS_ARCH_PPC, KS_MODE_PPC64|KS_MODE_BIG_ENDIAN)
enc,_=ks.asm(re.sub(r"\br(\d+)", r"\1", asm).replace("cr7","7"), CAVE); blob=bytes(enc)
md=Cs(CS_ARCH_PPC, CS_MODE_64|CS_MODE_BIG_ENDIAN)
for i in md.disasm(blob,CAVE): print(f'# {i.address:#x} {i.mnemonic} {i.op_str}')
print(blob.hex().upper())
hook,_=ks.asm(f"b {CAVE:#x}", 0x5ded64); print('HOOK', bytes(hook).hex().upper())
