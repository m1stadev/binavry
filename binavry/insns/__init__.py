from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from frozendict import frozendict
from tibs import Tibs


@dataclass(frozen=True)
class InstructionData:
    name: str
    mnem: str
    sig: str
    op_order: str = ''
    flags: str = ''

    @cached_property
    def maskval(self) -> tuple[Tibs, Tibs]:
        if set(self.op_order) != {c for c in self.sig if not c.isdigit()}:
            raise ValueError("op_order doesn't match with sig?")

        mask = Tibs([c.isdigit() for c in self.sig])
        val = Tibs([int(c) if c.isdigit() else 0 for c in self.sig])

        return (mask, val)

    @cached_property
    def base(self) -> InstructionData | None:
        return _get_base_insn(self)

    @cached_property
    def is_base(self) -> bool:
        return _is_base(self)


from .bit import _BIT_INSNS
from .ctrl import _CTRL_INSNS
from .data import _DATA_INSNS
from .flow import _FLOW_INSNS
from .logic import _LOGIC_INSNS


class _InstructionsEnum:
    def __eq__(self, other) -> bool:
        if isinstance(other, InstructionData):
            return getattr(self, 'value') == other

        elif isinstance(other, Instructions):
            return getattr(self, 'value') == other.value

        return False

    def __hash__(self):
        return hash(getattr(self, '_name_'))


Instructions = Enum(
    value='Instructions',
    names=[
        (insn.name, insn)
        for insn in (
            *_BIT_INSNS,
            *_CTRL_INSNS,
            *_DATA_INSNS,
            *_FLOW_INSNS,
            *_LOGIC_INSNS,
        )
    ],
    type=_InstructionsEnum,
)

_ALT_INSTRUCTIONS: frozendict[Instructions, tuple[Instructions]] = frozendict(
    {
        Instructions.ADC: (Instructions.ROL,),
        Instructions.ADD: (Instructions.LSL,),
        Instructions.AND: (Instructions.TST,),
        Instructions.BRBC: (
            Instructions.BRCC,
            Instructions.BRGE,
            Instructions.BRHC,
            Instructions.BRID,
            Instructions.BRNE,
            Instructions.BRPL,
            Instructions.BRSH,
            Instructions.BRTC,
            Instructions.BRVC,
        ),
        Instructions.BRBS: (
            Instructions.BRCS,
            Instructions.BREQ,
            Instructions.BRHS,
            Instructions.BRIE,
            Instructions.BRLO,
            Instructions.BRLT,
            Instructions.BRMI,
            Instructions.BRTS,
            Instructions.BRVS,
        ),
        Instructions.BCLR: (
            Instructions.CLC,
            Instructions.CLH,
            Instructions.CLI,
            Instructions.CLN,
            Instructions.CLS,
            Instructions.CLT,
            Instructions.CLV,
            Instructions.CLZ,
        ),
        Instructions.BSET: (
            Instructions.SEC,
            Instructions.SEH,
            Instructions.SEI,
            Instructions.SEN,
            Instructions.SES,
            Instructions.SET,
            Instructions.SEV,
            Instructions.SEZ,
        ),
        Instructions.EOR: (Instructions.CLR,),
        Instructions.LDI: (Instructions.SER,),
    }
)  # ty:ignore[invalid-assignment]


def _get_base_insn(idata: InstructionData) -> InstructionData | None:
    for base, alts in _ALT_INSTRUCTIONS.items():
        if any(idata == alt for alt in alts):
            return base.value


def _is_base(idata: InstructionData) -> bool:
    return Instructions(idata) in _ALT_INSTRUCTIONS.keys()
