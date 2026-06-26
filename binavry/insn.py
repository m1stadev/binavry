from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from tibs import Tibs

from .insns import InstructionData, Instructions


@dataclass(frozen=True)
class Operand:
    op_type: 'OpType'
    value: int
    index: tuple[int, ...]


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
    def __init__(
        self, data: bytes, idata: InstructionData, operands: list[Operand] = []
    ):
        self._data = data
        self._idata = idata
        self._ops: list[Operand] = operands

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def idata(self) -> InstructionData:
        return self._idata

    @property
    def name(self) -> str:
        return self._idata.name

    @property
    def mnem(self) -> str:
        return self._idata.mnem

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
        if len(data) < 2:
            raise ValueError('Data is too small to contain instruction')

        for insn in sorted(
            [insn.value for insn in Instructions],
            key=lambda i: len(i.sig),
            reverse=True,
        ):
            mask, val = insn.maskval

            if (len(mask) == 32) and (len(data) >= 4):
                single: Tibs = Tibs.from_bytes(data[:4]).byte_swapped(2)
            elif (len(mask) == 16) and (len(data) >= 2):
                single: Tibs = Tibs.from_bytes(data[:2]).byte_swapped(2)
            else:
                continue

            if (single & mask) != val:
                continue

            operands = list()
            for arg in insn.op_order:
                if insn.name == 'CLR':
                    if len(operands) == 0:
                        idx = [6, 12, 13, 14, 15]
                    else:
                        idx = [7, 8, 9, 10, 11]
                else:
                    idx = [i for i, o in enumerate(insn.sig) if o == arg]

                op = Tibs(single[i] for i in idx)
                op_type = OpType(arg)
                value = None
                match op_type:
                    case OpType.REG_DST | OpType.REG_SRC:
                        match len(idx):
                            case 2:
                                match op.u:
                                    case 0:
                                        value = 24
                                    case 1:
                                        value = 26
                                    case 2:
                                        value = 28
                                    case 3:
                                        value = 30
                            case 3:
                                value = (op.u + 0x10) if 0 <= op.u <= 0x7 else None
                            case 4:
                                value = (op.u + 0x10) if 0 <= op.u <= 0xF else None
                            case 5:
                                value = op.u if 0 <= op.u <= 0x1F else None

                    case OpType.BIT_REG | OpType.BIT_SREG:
                        value = op.u if 0 <= op.u <= 7 else None

                    case OpType.ADDR_IMM:
                        match len(idx):
                            case 7:
                                # if '_rc' in insn.name:
                                #    value = op.u if 0 <= op.u <= 127 else None
                                # else:
                                value = (op.i * 2) if -0x40 <= op.i < 0x40 else None
                            case 12:
                                value = (op.i * 2) if -0x800 <= op.i < 0x800 else None
                            case 16:
                                value = (op.u * 2) if 0 < op.u <= 0x7FFF else None
                            case 22:
                                if insn.name == 'CALL':
                                    # TODO: Fix fail on SoCs with a 22-bit PC
                                    value = (op.u * 2) if 0 <= op.u <= 0x7FFF else None
                                elif insn.name == 'JMP':
                                    value = (
                                        (op.u * 2) if 0 <= op.u <= 0x1FFFFF else None
                                    )

                    case OpType.IMM | OpType.ADDR_DIS | OpType.ADDR_IO:
                        value = op.u if 0 <= op.u <= ((2 ** len(idx)) - 1) else None

                if value is None:
                    raise ValueError('Invalid operand in instruction data')

                operands.append(Operand(op_type=op_type, value=value, index=idx))

            return cls(single.to_bytes(), idata=insn, operands=operands)

        raise ValueError('No valid instruction found in data')
