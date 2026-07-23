from binaryninja import BasicBlock, BasicBlockAnalysisContext, core_version_info

_version = core_version_info().build


def add_instruction_data(
    ctx: BasicBlockAnalysisContext, block: BasicBlock, data: bytes
) -> None:
    if _version >= 10170:
        ctx.lifter_instruction_data.append(block=block, data=data)  # ty:ignore[unresolved-attribute]
    else:
        block.add_instruction_data(data=data)  # ty:ignore[unresolved-attribute]
