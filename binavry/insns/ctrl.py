from . import InstructionData

_CTRL_INSNS = (
    InstructionData(name='BREAK', mnem='break', sig='1001010110011000'),
    InstructionData(name='NOP',   mnem='nop',   sig='0000000000000000'),
    InstructionData(name='SLEEP', mnem='sleep', sig='1001010110001000'),
    )