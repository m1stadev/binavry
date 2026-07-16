from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Self

from tibs import Tibs

from .insns import InstructionData, Instructions


@dataclass(frozen=True)
class Operand:
    op_type: 'OpType'
    value: int
    index: list[int]


class OpType(StrEnum):
    REG_DST = 'd'
    REG_SRC = 'r'

    REG_X = 'x'
    REG_XDEC = 'xdec'
    REG_XINC = 'xinc'
    REG_Y = 'y'
    REG_YDEC = 'ydec'
    REG_YINC = 'yinc'
    REG_Z = 'z'
    REG_ZDEC = 'zdec'
    REG_ZINC = 'zinc'

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

    @staticmethod
    def _decode_operands(data: Tibs, idata: InstructionData) -> tuple[Operand]:
        operands = list()
        for arg in idata.op_order:
            idx = [i for i, o in enumerate(idata.sig) if o == arg]

            op = Tibs(data[i] for i in idx)
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
                            # if '_rc' in idata.name:
                            #    value = op.u if 0 <= op.u <= 127 else None
                            # else:
                            value = ((op.i + 1) * 2) if -0x40 <= op.i < 0x40 else None
                        case 12:
                            value = ((op.i + 1) * 2) if -0x800 <= op.i < 0x800 else None
                        case 16:
                            value = (op.u * 2) if 0 < op.u <= 0x7FFF else None
                        case 22:
                            if idata.name == 'CALL':
                                # TODO: Fix fail on SoCs with a 22-bit PC
                                value = (op.u * 2) if 0 <= op.u <= 0x7FFF else None
                            elif idata.name == 'JMP':
                                value = (op.u * 2) if 0 <= op.u <= 0x1FFFFF else None

                case OpType.IMM | OpType.ADDR_DIS | OpType.ADDR_IO:
                    value = op.u if 0 <= op.u <= ((2 ** len(idx)) - 1) else None

            if value is None:
                raise ValueError('Invalid operand in instruction data')

            operands.append(Operand(op_type=op_type, value=value, index=idx))

        if idata in (
            Instructions.CLR,
            Instructions.LSL,
            Instructions.ROL,
            Instructions.TST,
        ):
            if operands[0].value != operands[1].value:
                raise ValueError(
                    f'Different registers cannot be passed to {idata.name}'
                )

            operands.pop(-1)

        if '_' in idata.name:
            op_type = OpType(idata.name.split('_')[-1])
            match op_type:
                case OpType.REG_XINC | OpType.REG_YINC | OpType.REG_ZINC:
                    value = 1

                case OpType.REG_XDEC | OpType.REG_YDEC | OpType.REG_ZDEC:
                    value = -1

                case OpType.REG_X | OpType.REG_Y | OpType.REG_Z:
                    op = next(
                        (op for op in operands if op.op_type == OpType.ADDR_DIS), None
                    )
                    if op is not None:
                        value = op.value
                        operands.remove(op)
                    else:
                        value = 0

            if idata.mnem in ('st', 'std'):
                idx = 0

            else:
                idx = 1

            operands.insert(idx, Operand(op_type, value, [-1]))

        return tuple(operands)

    @classmethod
    @lru_cache
    def decode(cls, data: bytes, byte_swapped: bool = True) -> Self:
        if len(data) < 2:
            raise ValueError('Data is too small to contain instruction')

        for idata in sorted(
            [idata.value for idata in Instructions],
            key=lambda i: len(i.sig),
            reverse=True,
        ):
            mask, val = idata.maskval

            if (len(mask) == 32) and (len(data) >= 4):
                single: Tibs = Tibs.from_bytes(data[:4])

            elif (len(mask) == 16) and (len(data) >= 2):
                single: Tibs = Tibs.from_bytes(data[:2])

            else:
                continue

            if byte_swapped:
                single = single.byte_swapped(2)

            if (single & mask) != val:
                continue

            if idata.is_base:
                for alt in [
                    alt.value for alt in Instructions if alt.value.base == idata
                ]:
                    try:
                        return cls.decode_as(data, alt)
                    except ValueError:
                        pass

            operands = cls._decode_operands(single, idata)
            return cls(single.to_bytes(), idata=idata, operands=operands)

        raise ValueError('No valid instruction found in data')

    @classmethod
    def decode_as(
        cls, data: bytes, idata: InstructionData, byte_swapped: bool = True
    ) -> Self:
        mask, val = idata.maskval

        if (len(mask) == 32) and (len(data) >= 4):
            single: Tibs = Tibs.from_bytes(data[:4])

        elif (len(mask) == 16) and (len(data) >= 2):
            single: Tibs = Tibs.from_bytes(data[:2])

        else:
            raise ValueError('No valid instruction found in data')

        if byte_swapped:
            single = single.byte_swapped(2)

        if (single & mask) != val:
            raise ValueError('No valid instruction found in data')

        operands = cls._decode_operands(single, idata)
        return cls(single.to_bytes(), idata=idata, operands=operands)
