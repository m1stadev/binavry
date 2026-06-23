from binaryninja import (
    Architecture,
    InstructionInfo,
    InstructionTextToken,
    InstructionTextTokenType,
    RegisterInfo,
)

from . import Instruction, OpType


class AVRArch(Architecture):
    name = 'AVR'
    address_size = 3
    default_int_size = 1
    instr_alignment = 2
    max_instr_length = 4

    regs = {
        'r0': RegisterInfo('r0', 1),
        'r1': RegisterInfo('r1', 1),
        'r2': RegisterInfo('r2', 1),
        'r3': RegisterInfo('r3', 1),
        'r4': RegisterInfo('r4', 1),
        'r5': RegisterInfo('r5', 1),
        'r6': RegisterInfo('r6', 1),
        'r7': RegisterInfo('r7', 1),
        'r8': RegisterInfo('r8', 1),
        'r9': RegisterInfo('r9', 1),
        'r10': RegisterInfo('r10', 1),
        'r11': RegisterInfo('r11', 1),
        'r12': RegisterInfo('r12', 1),
        'r13': RegisterInfo('r13', 1),
        'r14': RegisterInfo('r14', 1),
        'r15': RegisterInfo('r15', 1),
        'r16': RegisterInfo('r16', 1),
        'r17': RegisterInfo('r17', 1),
        'r18': RegisterInfo('r18', 1),
        'r19': RegisterInfo('r19', 1),
        'r20': RegisterInfo('r20', 1),
        'r21': RegisterInfo('r21', 1),
        'r22': RegisterInfo('r22', 1),
        'r23': RegisterInfo('r23', 1),
        'r24': RegisterInfo('r24', 1),
        'r25': RegisterInfo('r25', 1),
        'X': RegisterInfo('X', 2),
        'r26': RegisterInfo('X', 1, 0),
        'r27': RegisterInfo('X', 1, 1),
        'Y': RegisterInfo('Y', 2),
        'r28': RegisterInfo('Y', 1, 0),
        'r29': RegisterInfo('Y', 1, 1),
        'Z': RegisterInfo('Z', 2),
        'r30': RegisterInfo('Z', 1, 0),
        'r31': RegisterInfo('Z', 1, 1),
    }

    global_regs = ['r0', 'r1']
    stack_pointer = 'sp'

    def get_instruction_info(self, data: bytes, addr: int) -> InstructionInfo | None:
        insn = Instruction.decode(data)
        return InstructionInfo(len(insn.data))

    def get_instruction_text(
        self, data: bytes, addr: int
    ) -> tuple[list[InstructionTextToken], int] | None:
        insn = Instruction.decode(data)
        tokens = [
            InstructionTextToken(InstructionTextTokenType.InstructionToken, insn.mnem),
            InstructionTextToken(InstructionTextTokenType.TextToken, ' '),
        ]

        for op in insn.operands:
            match op.op_type:
                case OpType.REG_DST | OpType.REG_SRC:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.RegisterToken, f'r{op.value}'
                        )
                    )
                case OpType.IMM:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken,
                            hex(op.value),
                            op.value,
                        )
                    )
                case OpType.ADDR_DIS:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.RegisterToken,
                            insn.name[-1].upper(),
                        )
                    )
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.OperationToken, '+'
                        )
                    )
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken, op.value, op.value
                        )
                    )
                case OpType.ADDR_IMM:
                    if len(op.index) in (7, 12):
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.CodeRelativeAddressToken,
                                hex(addr + op.value),
                                addr + op.value,
                            )
                        )
                    else:
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.AddressDisplayToken,
                                op.value,
                                op.value,
                            )
                        )

            if op != insn.operands[-1]:
                tokens.append(
                    InstructionTextToken(
                        InstructionTextTokenType.OperandSeparatorToken, ', '
                    )
                )

        return (tokens, len(insn.data))
