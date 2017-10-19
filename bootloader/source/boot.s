
@ This is the entry point and will be overwritten once the new program is loaded.
@ We immediately jump to code after the giant space we leave.
.globl _start
_start:
    b skip

@ Create space for the program to be loaded into. We subtract 0x8004 because "b skip" is 4 bytes
.space 0x00200000 - 0x8004,0

@ Set the stack pointer to somewhere useful and execute "main"
skip:
    mov sp,#0x06000000
    bl boot_main
hang: b hang

@ Used by the ihex parsing state machine
.globl PUT32
PUT32:
    str r1,[r0]
    bx lr

@ Unconditional branch to r0
.globl BRANCHTO
BRANCHTO:
    bx r0
