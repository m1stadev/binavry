from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from binaryninja import InstructionInfo
from tibs import Tibs

from .insns import InstructionData, Instructions


@dataclass(frozen=True)
class Operand:
    insn: 'Instruction'
    op_type: 'OpType'
    value: int

    def __int__(self) -> int:
        return self.value


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
        data = Tibs(data).byte_swapped(2)  # ty:ignore[invalid-assignment]
        for i in Instructions:
            mask, val = i.maskval
            if len(data) != len(mask):
                continue


            if (data & mask) == val:
                insn = i
                break
        else:
            raise ValueError('No valid instructions found in data')

        obj = cls(data=data, idata=insn)
        for arg in insn.op_order:
            idx = [i for i, o in enumerate(insn.sig) if o == arg]

            op = Operand(
                insn=obj,
                op_type=OpType(arg),
                value=Tibs(data[i] for i in idx).to_u()
            )

            verify = None
            match OpType(arg):
                case OpType.REG_DST | OpType.REG_SRC:
                    match len(idx):
                        case 2:
                            verify = lambda op: 0 <= op <= 4  # noqa: E731
                        case 3:
                            verify = lambda op: 16 <= op <= 23  # noqa: E731
                        case 4:
                            verify = lambda op: 16 <= op <= 31 # noqa: E731
                        case 5:
                            verify = lambda op: 0 <= op <= 31  # noqa: E731
                case OpType.BIT_REG | OpType.BIT_SREG:
                    pass
                case OpType.ADDR_DIS | OpType.ADDR_IMM | OpType.ADDR_IO:
                    pass
                case OpType.IMM:
                    pass

            if (verify is not None) and verify(op):
                obj.add_operand(op)

        return obj





