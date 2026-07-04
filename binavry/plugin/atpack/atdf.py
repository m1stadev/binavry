from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


@dataclass(frozen=True)
class MemorySection:
    name: str
    size: int


@dataclass(frozen=True)
class MemorySegment:
    name: str
    flags: str
    size: int
    sections: list[MemorySection]


@dataclass(frozen=True)
class Register:
    name: str
    offset: int
    size: int


class ATDeviceInfo:
    def __init__(self, _data: bytes):
        self._tree = etree.fromstring(_data)
        self._interrupts: list[str] = []
        self._registers: list[Register] = []
        self._segments: list[MemorySegment] = []

        for module in next(prop for prop in self._tree if prop.tag == 'modules'):
            if module.get('name') in ('FUSE', 'LOCKBIT'):
                continue

            for regs in (grp for grp in module if grp.tag == 'register-group'):
                for reg in regs:
                    self._registers.append(
                        Register(
                            name=reg.get('name'),
                            offset=int(reg.get('offset'), 16),
                            size=int(reg.get('size')),
                        )
                    )

        device = next(prop for prop in self._tree if prop.tag == 'devices')[0]
        self._name: str = device.get('name')
        self._family: str = device.get('family')

        for irq in next(i for i in device if i.tag == 'interrupts'):
            self._interrupts.append(irq.get('name'))

        for seg in next(prop for prop in device if prop.tag == 'address-spaces'):
            sections = []
            name = seg.get('id')
            match name:
                case 'prog':
                    flags = 'RX'

                case 'data':
                    flags = 'RW'

                    for sec in seg:
                        sec_size = sec.get('size')
                        if 'x' in sec_size:
                            sec_size = int(sec_size, 16)
                        else:
                            sec_size = int(sec_size)

                        sections.append(
                            MemorySection(name=sec.get('name'), size=sec_size)
                        )

                case _:
                    continue

            size = seg.get('size')
            if 'x' in size:
                size = int(size, 16)
            else:
                size = int(size)

            self._segments.append(
                MemorySegment(name=name, flags=flags, size=size, sections=sections)
            )

    @property
    def family(self) -> str:
        return self._family

    @property
    def interrupts(self) -> tuple[str, ...]:
        return tuple(self._interrupts)

    @property
    def name(self) -> str:
        return self._name

    @property
    def registers(self) -> tuple[Register, ...]:
        return tuple(self._registers)

    @property
    def segments(self) -> tuple[MemorySegment, ...]:
        return tuple(self._segments)
