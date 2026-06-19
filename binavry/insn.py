from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from binaryninja import InstructionInfo
from tibs import Tibs

from .insns import InstructionData, Instructions


@dataclass(frozen=True)
class Operand:
    op_type: 'OpType'
    value: int

class OpType(StrEnum):
    REG_DST = 'd'
    REG_SRC = 'r'

    IMM = 'K'
    
    BIT_REG = 'b'
    BIT_SREG = 's'

    ADDR_IMM = 'k'
    ADDR_IO = 'A'
    ADDR_DIS = 'q'


class Instruction:
    def __init__(self, data: bytes, idata: InstructionData, operands: list[Operand] = []):
        self._data = data
        self._idata = idata
        self._ops: list[Operand] = operands

    @property
    def idata(self) -> InstructionData:
        return self._idata

    @property
    def operands(self) -> tuple[Operand, ...]:
        return tuple(self._ops)

    def add_operand(self, op: Operand) -> None:
        self._ops.append(op)

    def rm_operand(self, op: Operand) -> None:
        if op not in self._ops:
            raise ValueError('Provided operand is not in Instruction')

        self._ops.remove(op)

    @classmethod
    def decode(cls, data: bytes) -> Self:
        data: Tibs = Tibs.from_bytes(data).byte_swapped(2)
        for i in Instructions:
            mask, val = i.maskval
            if len(data) != len(mask):
                continue

            if (data & mask) == val:
                insn = i
                break
        else:
            raise ValueError('No valid instructions found in data')

        operands = list()
        for arg in insn.op_order:
            idx = [i for i, o in enumerate(insn.sig) if o == arg]

            op = Tibs(data[i] for i in idx)
            op_type = OpType(arg)
            value = None
            match op_type:
                case OpType.REG_DST | OpType.REG_SRC:
                    match len(idx):
                        case 2:
                            value = op.u if 0 <= op.u <= 4 else None
                        case 3:
                            value = op.u if 16 <= op.u <= 23 else None
                        case 4:
                            value = op.u if 16 <= op.u <= 31 else None
                        case 5:
                            value = op.u if 0 <= op.u <= 31 else None

                case OpType.BIT_REG | OpType.BIT_SREG:
                    value = op.u if 0 <= op.u <= 7 else None

                case OpType.ADDR_IMM:
                    match len(idx):
                        case 7:
                            value = (op.u * 2) if 0 <= op.u <= ((2 ** len(idx)) - 1) else None
                        case 12:
                            value = (op.i * 2) if (-1 * (2 ** 11)) < op.i < (2 ** 11) else None
                        case 16:
                            value = (op.i * 2) if (-1 * (2 ** 11)) < op.i < ((2 ** 16) - 1) else None
                        case 22:
                            if insn.name == 'CALL':
                                #TODO: Fix fail on SoCs with a 22-bit PC
                                value = (op.u * 2) if 0 <= op.u <= ((2 ** 16) - 1) else None
                            elif insn.name == 'JMP':
                                value = (op.u * 2) if 0 <= op.u <= ((2 ** 22) - 1) else None

                case OpType.IMM | OpType.ADDR_DIS | OpType.ADDR_IO:
                    value = op.u if 0 <= op.u <= ((2 ** len(idx)) - 1) else None

            if value is not None:
                operands.append(Operand(op_type=op_type, value=value))

        return cls(data.to_bytes(), idata=insn, operands=operands)
