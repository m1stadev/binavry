from binaryninja import (
    BasicBlock,
    BasicBlockAnalysisContext,
    FunctionLifterContext,
    core_version_info,
)

_version = core_version_info().build


def add_instruction_data(
    ctx: BasicBlockAnalysisContext | FunctionLifterContext,
    block: BasicBlock,
    data: bytes,
) -> None:
    if _version >= 10171:
        ctx.lifter_instruction_data.append(block=block, data=data)
    else:
        block.add_instruction_data(data=data)


def get_instruction_data(
    ctx: BasicBlockAnalysisContext | FunctionLifterContext, block: BasicBlock, addr: int
) -> bytes:
    if _version >= 10171:
        return ctx.lifter_instruction_data.get(block=block, addr=addr)
    else:
        return block.get_instruction_data(addr)
