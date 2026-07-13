from binaryninja import (
    Architecture,
    BinaryView,
    RegisterInfo,
    SectionSemantics,
    SegmentFlag,
    Symbol,
    SymbolType,
)
from tibs import Tibs

from . import Instruction
from .arch import AVRArch
from .atpack import PackDownloader


class AVRView(BinaryView):
    name = 'AVR'
    is_force_loadable = True

    def __init__(self, data: BinaryView):
        super().__init__(file_metadata=data.file, parent_view=data)

        self.data = data
        self._packdownloader = PackDownloader()
        # TODO: Implement a UI window for searching device info
        self._packdownloader.update()
        self._device_info = None

    @classmethod
    def is_valid_for_data(self, data) -> bool:
        # For now, just check for 8 JMP instructions
        # at the beginning of the data (IVT)

        insn_data = data.read(0, 0x20)
        for i in range(0, 0x20, 4):
            try:
                insn = Instruction.decode(insn_data[i : i + 4])
            except ValueError:
                break

            if insn.name != 'JMP':
                break

        else:
            return True

        return False

    @property
    def device_info(self):
        return self._device_info

    def init(self) -> bool:
        self.arch = Architecture['AVR']
        self.platform = self.arch.standalone_platform  # ty:ignore[unresolved-attribute]

        # TODO: Implement setting for choosing device
        self._device_info = next(
            pack for pack in self._packdownloader.packs if pack.device == 'AT90CAN64'
        ).device_info

        rom = next(seg for seg in self.device_info.segments if seg.name == 'prog')

        if self.data.length > rom.size:
            raise ValueError('Binary too large for device flash')

        # ROM
        self.add_auto_segment(
            start=0,
            length=rom.size,
            data_offset=0,
            data_length=self.data.length,
            flags=SegmentFlag.SegmentReadable | SegmentFlag.SegmentExecutable,
        )

        self.add_auto_section(
            'ROM', 0, rom.size, SectionSemantics.ReadOnlyCodeSectionSemantics
        )

        start = 0
        for irq in self.device_info.interrupts:
            self.define_auto_symbol_and_var_or_function(
                Symbol(SymbolType.FunctionSymbol, start, irq)
            )
            if irq == 'RESET':
                self.add_entry_point(start)
            else:
                self.add_function(start)

            start += 4

        ram = next(seg for seg in self.device_info.segments if seg.name == 'data')
        self.add_auto_segment(
            start=rom.size,
            length=ram.size,
            data_offset=0,
            data_length=0,
            flags=SegmentFlag.SegmentReadable | SegmentFlag.SegmentWritable,
        )

        self.add_auto_section(
            'RAM', rom.size, ram.size, SectionSemantics.ReadWriteDataSectionSemantics
        )

        start = 0
        for sec in ram.sections:
            self.add_auto_section(
                name=sec.name,
                start=rom.size + start,
                length=sec.size,
                semantics=SectionSemantics.ReadWriteDataSectionSemantics,
            )
            start += sec.size

        for reg in sorted(self.device_info.registers, key=lambda r: r.offset):
            self.define_auto_symbol_and_var_or_function(
                Symbol(SymbolType.DataSymbol, rom.size + reg.offset, reg.name)
            )
            # self.arch.regs[reg.name] = RegisterInfo(reg.name, reg.size)

        return True

    def perform_is_executable(self) -> bool:
        return True

    def perform_get_address_size(self) -> int:
        return AVRArch.address_size

    def perform_get_entry_point(self) -> int:
        return (
            next(
                self.device_info.interrupts.index(i)
                for i in self.device_info.interrupts
                if i == 'RESET'
            )
            * 4
        )
