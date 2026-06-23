from binaryninja import Architecture, BinaryView, SegmentFlag
from tibs import Tibs

from . import AVRArch
from .insn import Instruction


class AVRView(BinaryView):
    name = 'AVR'
    is_force_loadable = True

    def __init__(self, data: BinaryView):
        super().__init__(file_metadata=data.file, parent_view=data)

        self.data = data

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

    def init(self) -> bool:
        self.arch = Architecture['AVR']
        self.platform = self.arch.standalone_platform
        # ROM
        self.add_auto_segment(
            start=0,
            length=0x10000,
            data_offset=0,
            data_length=self.data.length,
            flags=SegmentFlag.SegmentReadable | SegmentFlag.SegmentExecutable,
        )
        # self.add_auto_section('ROM', 0, 0x10000)

        # Registers
        self.add_auto_segment(
            start=0x10000,
            length=0x100,
            data_offset=0x10000,
            data_length=0,
            flags=SegmentFlag.SegmentReadable | SegmentFlag.SegmentWritable,
        )
        # self.add_auto_section('REG', 0x10000, 0x100)

        # RAM
        self.add_auto_segment(
            start=0x10100,
            length=0x1000,
            data_offset=0x10000,
            data_length=0,
            flags=SegmentFlag.SegmentReadable | SegmentFlag.SegmentWritable,
        )
        # self.add_auto_section('RAM', 0x10100, 0x1000)

        return True

    def perform_is_executable(self) -> bool:
        return True

    def perform_get_address_size(self) -> int:
        return AVRArch.address_size

    def perform_get_entry_point(self) -> int:
        return 0x0
