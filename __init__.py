# from binaryninja import Architecture, BinaryViewType, Endianness

from .binavry.plugin import AVRArch, AVRView  # ty:ignore[unresolved-import]

AVRArch.register()
AVRView.register()

# BinaryViewType['ELF'].register_arch(83, Endianness.LittleEndian, Architecture['AVR'])
