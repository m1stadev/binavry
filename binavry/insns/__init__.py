from dataclasses import dataclass
from functools import cached_property

from tibs import Tibs


@dataclass(frozen=True)
class InstructionData:
    name: str
    mnem: str
    sig: str
    op_order: str = ''

    @cached_property
    def maskval(self) -> tuple[Tibs, Tibs]:
        if set(self.op_order) != {c for c in self.sig if not c.isdigit()}:
            raise ValueError("op_order doesn't match with sig?")

        mask = Tibs([c.isdigit() for c in self.sig])
        val = Tibs([int(c) if c.isdigit() else 0 for c in self.sig])

        return (mask, val)


from .bit import _BIT_INSNS
from .ctrl import _CTRL_INSNS
from .data import _DATA_INSNS
from .flow import _FLOW_INSNS
from .logic import _LOGIC_INSNS

Instructions = tuple(
    sorted(
        [
            i
            for i in (
                *_BIT_INSNS,
                *_CTRL_INSNS,
                *_DATA_INSNS,
                *_FLOW_INSNS,
                *_LOGIC_INSNS,
            )
        ],
        key=lambda i: len(i.sig),
        reverse=True,
    )
)
