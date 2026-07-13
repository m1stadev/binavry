from binaryninja import (
    ArchAndAddr,
    Architecture,
    BasicBlock,
    BasicBlockAnalysisContext,
    BranchType,
    Function,
    InstructionInfo,
    InstructionTextToken,
    InstructionTextTokenType,
    LowLevelILFunction,
    RegisterInfo,
    RegisterName,
    Symbol,
    SymbolType,
)
from binaryninja.lowlevelil import ExpressionIndex

from . import Instruction, Instructions, Operand, OpType, get_base_insn


class AVRArch(Architecture):
    name = 'AVR'
    address_size = 3
    default_int_size = 1
    instr_alignment = 2
    max_instr_length = 4

    regs = {
        'r0': RegisterInfo('r0', 1),
        'r1': RegisterInfo('r1', 1),
        'r2': RegisterInfo('r2', 1),
        'r3': RegisterInfo('r3', 1),
        'r4': RegisterInfo('r4', 1),
        'r5': RegisterInfo('r5', 1),
        'r6': RegisterInfo('r6', 1),
        'r7': RegisterInfo('r7', 1),
        'r8': RegisterInfo('r8', 1),
        'r9': RegisterInfo('r9', 1),
        'r10': RegisterInfo('r10', 1),
        'r11': RegisterInfo('r11', 1),
        'r12': RegisterInfo('r12', 1),
        'r13': RegisterInfo('r13', 1),
        'r14': RegisterInfo('r14', 1),
        'r15': RegisterInfo('r15', 1),
        'r16': RegisterInfo('r16', 1),
        'r17': RegisterInfo('r17', 1),
        'r18': RegisterInfo('r18', 1),
        'r19': RegisterInfo('r19', 1),
        'r20': RegisterInfo('r20', 1),
        'r21': RegisterInfo('r21', 1),
        'r22': RegisterInfo('r22', 1),
        'r23': RegisterInfo('r23', 1),
        'r24': RegisterInfo('r24', 1),
        'r25': RegisterInfo('r25', 1),
        'X': RegisterInfo('X', 2),
        'r26': RegisterInfo('X', 1, 0),
        'r27': RegisterInfo('X', 1, 1),
        'Y': RegisterInfo('Y', 2),
        'r28': RegisterInfo('Y', 1, 0),
        'r29': RegisterInfo('Y', 1, 1),
        'Z': RegisterInfo('Z', 2),
        'r30': RegisterInfo('Z', 1, 0),
        'r31': RegisterInfo('Z', 1, 1),
        'SP': RegisterInfo('SP', 2),
    }

    global_regs = ['r0', 'r1']
    stack_pointer = 'SP'

    def analyze_basic_blocks(
        self, func: Function, context: BasicBlockAnalysisContext
    ) -> None:
        # NOTE: The entry point does not call this function,
        # so IO regs are not displayed correctly in the RESET irq

        data = func.view
        blocks_to_process = [func.start]
        finished = []
        arch_context = {'mapped_io': {}}

        while len(blocks_to_process) > 0:
            if data.analysis_is_aborted:
                break

            addr = blocks_to_process.pop()
            if addr in finished:
                continue

            finished.append(addr)

            block: BasicBlock = context.create_basic_block(func.arch, addr)  # ty:ignore[invalid-assignment]
            while True:
                try:
                    insn = Instruction.decode(data.read(addr, 4))
                except ValueError:
                    break

                block.add_instruction_data(insn.data)

                idata = Instructions(get_base_insn(insn.idata) or insn.idata)
                if idata not in (
                    Instructions.BRBC,
                    Instructions.BRBS,
                    Instructions.JMP,
                    Instructions.RET,
                    Instructions.RETI,
                    Instructions.RJMP,
                ):
                    match idata:
                        case Instructions.IN | Instructions.OUT:
                            io_offset = data.get_section_by_name('ROM').length
                            op = next(
                                op
                                for op in insn.operands
                                if op.op_type == OpType.ADDR_IO
                            )
                            io_reg = data.get_symbol_at(
                                io_offset + op.value + 0x20,
                                namespace=SymbolType.DataSymbol,
                            )
                            if io_reg is None:
                                # Wide register?
                                io_reg = data.get_symbol_at(
                                    io_offset + op.value + 0x19,
                                    namespace=SymbolType.DataSymbol,
                                )

                            arch_context['mapped_io'][addr] = {
                                'name': io_reg.short_name,
                                'addr': io_reg.address,
                            }

                        case Instructions.CALL | Instructions.RCALL:
                            if idata == Instructions.RCALL:
                                val = addr + insn.operands[-1].value
                            else:
                                val = insn.operands[-1].value

                            data.define_auto_symbol_and_var_or_function(
                                Symbol(SymbolType.FunctionSymbol, val, f'sub_{val:x}')
                            )
                            data.add_function(val)
                            context.add_direct_code_reference(
                                val, ArchAndAddr(self, addr)
                            )

                    addr += len(insn.data)
                    continue

                match idata:
                    case Instructions.JMP | Instructions.RJMP:
                        val = insn.operands[0].value
                        if insn.idata == Instructions.RJMP:
                            val += addr

                        blocks_to_process.append(val)
                        block.add_pending_outgoing_edge(
                            BranchType.UnconditionalBranch,
                            val,
                            func.arch,
                        )

                    case Instructions.BRBC | Instructions.BRBS:
                        val = addr + insn.operands[-1].value
                        blocks_to_process += [val, addr + 2]

                        block.add_pending_outgoing_edge(
                            BranchType.TrueBranch,
                            val,
                            func.arch,
                        )

                        block.add_pending_outgoing_edge(
                            BranchType.FalseBranch,
                            addr + 2,
                            func.arch,
                        )

                    # case (
                    #    Instructions.EICALL
                    #    | Instructions.EIJMP
                    #    | Instructions.ICALL
                    #    | Instructions.IJMP
                    # ):
                    #    info.add_branch(BranchType.IndirectBranch)

                block.end = addr + len(insn.data)
                context.add_basic_block(block)
                break

        if len(arch_context['mapped_io']) > 0:
            context.function_arch_context = arch_context

        context.finalize()

    def get_instruction_info(self, data: bytes, addr: int) -> InstructionInfo | None:
        try:
            insn = Instruction.decode(data)
        except ValueError:
            return None

        info = InstructionInfo(len(insn.data))

        match Instructions(get_base_insn(insn.idata) or insn.idata):
            case Instructions.CALL:
                info.add_branch(BranchType.CallDestination, insn.operands[0].value)

            case Instructions.RCALL:
                info.add_branch(
                    BranchType.CallDestination, (addr + insn.operands[0].value)
                )

            case Instructions.JMP:
                info.add_branch(BranchType.UnconditionalBranch, insn.operands[0].value)

            case Instructions.RJMP:
                info.add_branch(
                    BranchType.UnconditionalBranch, (addr + insn.operands[0].value)
                )

            case Instructions.BRBC | Instructions.BRBS:
                info.add_branch(BranchType.TrueBranch, (addr + insn.operands[-1].value))
                info.add_branch(BranchType.FalseBranch, (addr + 2))

            case Instructions.RET | Instructions.RETI:
                info.add_branch(BranchType.FunctionReturn)

            case (
                Instructions.EICALL
                | Instructions.EIJMP
                | Instructions.ICALL
                | Instructions.IJMP
            ):
                info.add_branch(BranchType.IndirectBranch)

        return info

    def get_instruction_text_with_context(
        self, data: bytes, addr: int, context: dict | None
    ) -> tuple[list[InstructionTextToken], int] | None:
        try:
            insn = Instruction.decode(data)
        except ValueError:
            return None

        tokens, length = self.get_instruction_text(data, addr, insn=insn)  # ty:ignore[not-iterable]

        if (context is not None) and (addr in context['mapped_io'].keys()):
            io_reg = context['mapped_io'][addr]
            op = next(op for op in insn.operands if op.op_type == OpType.ADDR_IO)

            token = next(tokens.index(t) for t in tokens if t.value == op.value)
            tokens[token] = InstructionTextToken(
                InstructionTextTokenType.DataSymbolToken,
                io_reg['name'],
                io_reg['addr'],
            )

        return (tokens, length)

    def get_instruction_text(
        self, data: bytes, addr: int, insn: Instruction | None = None
    ) -> tuple[list[InstructionTextToken], int] | None:
        if insn is None:
            try:
                insn = Instruction.decode(data)
            except ValueError:
                return None

        tokens = [
            InstructionTextToken(InstructionTextTokenType.InstructionToken, insn.mnem),
            InstructionTextToken(InstructionTextTokenType.TextToken, ' '),
        ]

        for op in insn.operands:
            match op.op_type:
                case OpType.REG_DST | OpType.REG_SRC:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.RegisterToken, f'r{op.value}'
                        )
                    )

                case OpType.IMM:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken,
                            hex(op.value),
                            op.value,
                        )
                    )

                case OpType.ADDR_DIS:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.RegisterToken,
                            insn.name[-1].upper(),
                        )
                    )
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.OperationToken, '+'
                        )
                    )
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken,
                            str(op.value),
                            op.value,
                        )
                    )

                case OpType.ADDR_IMM:
                    if len(op.index) in (7, 12):
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.PossibleAddressToken,
                                hex(addr + op.value),
                                addr + op.value,
                            )
                        )

                    else:
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.PossibleAddressToken,
                                hex(op.value),
                                op.value,
                            )
                        )

                case OpType.ADDR_IO:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.PossibleAddressToken,
                            hex(op.value),
                            op.value,
                        )
                    )

                case OpType.BIT_REG | OpType.BIT_SREG:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken,
                            str(op.value),
                            op.value,
                        )
                    )

                case _:
                    match op.op_type:
                        case OpType.REG_XINC | OpType.REG_YINC | OpType.REG_ZINC:
                            tokens += [
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    op.op_type.value[0].upper(),
                                ),
                                InstructionTextToken(
                                    InstructionTextTokenType.OperationToken, '+'
                                ),
                            ]

                        case OpType.REG_XDEC | OpType.REG_YDEC | OpType.REG_ZDEC:
                            tokens += [
                                InstructionTextToken(
                                    InstructionTextTokenType.OperationToken, '-'
                                ),
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    op.op_type.value[0].upper(),
                                ),
                            ]

                        case OpType.REG_X | OpType.REG_Y | OpType.REG_Z:
                            tokens.append(
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    op.op_type.value[0].upper(),
                                )
                            )
                            match op.value:
                                case op.value if op.value < 0:
                                    tokens += [
                                        InstructionTextToken(
                                            InstructionTextTokenType.OperationToken, '-'
                                        ),
                                        InstructionTextToken(
                                            InstructionTextTokenType.IntegerToken,
                                            str(op.value),
                                            op.value,
                                        ),
                                    ]

                                case op.value if op.value > 0:
                                    tokens += [
                                        InstructionTextToken(
                                            InstructionTextTokenType.OperationToken, '+'
                                        ),
                                        InstructionTextToken(
                                            InstructionTextTokenType.IntegerToken,
                                            str(op.value),
                                            op.value,
                                        ),
                                    ]

            if op != insn.operands[-1]:
                tokens.append(
                    InstructionTextToken(
                        InstructionTextTokenType.OperandSeparatorToken, ', '
                    )
                )

        return (tokens, len(insn.data))

    def get_instruction_low_level_il(
        self, data: bytes, addr: int, il: LowLevelILFunction
    ) -> int | None:
        return None
