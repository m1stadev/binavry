from binaryninja import (
    ArchAndAddr,
    Architecture,
    BasicBlock,
    BasicBlockAnalysisContext,
    BranchType,
    FlagRole,
    FlagType,
    FlagWriteTypeName,
    Function,
    FunctionLifterContext,
    ILOperandType,
    ILRegisterType,
    InstructionInfo,
    InstructionTextToken,
    InstructionTextTokenType,
    IntrinsicInfo,
    IntrinsicInput,
    LowLevelILFlagCondition,
    LowLevelILFunction,
    LowLevelILLabel,
    LowLevelILOperation,
    RegisterInfo,
    RegisterName,
    SemanticClassType,
    SemanticGroupType,
    Symbol,
    SymbolType,
    Type,
)
from binaryninja.lowlevelil import ExpressionIndex

from . import RAM_BEGIN, Instruction, Instructions, Operand, OpType
from .compat import add_instruction_data, get_instruction_data
from .il import ILInstruction


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
        'SPH': RegisterInfo('SP', 1, 0),
        'SPL': RegisterInfo('SP', 1, 1),
    }

    flags = ['c', 'z', 'n', 'v', 's', 'h', 't', 'i']
    flag_roles = {
        'c': FlagRole.CarryFlagRole,
        'z': FlagRole.ZeroFlagRole,
        'n': FlagRole.NegativeSignFlagRole,
        'v': FlagRole.OverflowFlagRole,
        's': FlagRole.PositiveSignFlagRole,
        'h': FlagRole.HalfCarryFlagRole,
        't': FlagRole.SpecialFlagRole,
        'i': FlagRole.SpecialFlagRole,
    }

    flag_write_types = [
        'crry',
        'zero',
        'ngtv',
        'ovfl',
        'sign',
        'half',
        'bcpy',
        'gint',
        'bit',
        'math',
        'mul',
        'word',
    ]

    flags_written_By_flag_write_type = {
        'crry': ['c'],
        'zero': ['z'],
        'ngtv': ['n'],
        'ovfl': ['v'],
        'sign': ['s'],
        'half': ['h'],
        'bcpy': ['t'],
        'gint': ['i'],
        'bit': ['z', 'n', 'v', 's'],
        'math': ['z', 'c', 'n', 'v', 's', 'h'],
        'mul': ['z', 'c'],
        'word': ['z', 'c', 'n', 'v', 's'],
    }

    flags_required_for_flag_condition = {
        LowLevelILFlagCondition.LLFC_SGE: ['s'],
        LowLevelILFlagCondition.LLFC_UGE: ['c'],
        LowLevelILFlagCondition.LLFC_SLT: ['s'],
        LowLevelILFlagCondition.LLFC_ULT: ['c'],
        LowLevelILFlagCondition.LLFC_NE: ['z'],
        LowLevelILFlagCondition.LLFC_E: ['z'],
        LowLevelILFlagCondition.LLFC_POS: ['n'],
        LowLevelILFlagCondition.LLFC_NEG: ['n'],
        LowLevelILFlagCondition.LLFC_NO: ['v'],
        LowLevelILFlagCondition.LLFC_O: ['v'],
    }

    global_regs = ['r0', 'r1']
    stack_pointer = 'SP'

    intrinsics = {
        '__builtin_avr_nop': IntrinsicInfo(
            inputs=[IntrinsicInput(type=Type.void(), name='input')],
            outputs=[Type.void()],
        ),
        '__builtin_avr_sleep': IntrinsicInfo(
            inputs=[IntrinsicInput(type=Type.void(), name='input')],
            outputs=[Type.void()],
        ),
        '__builtin_avr_wdr': IntrinsicInfo(
            inputs=[IntrinsicInput(type=Type.void(), name='input')],
            outputs=[Type.void()],
        ),
        '__builtin_avr_swap': IntrinsicInfo(
            inputs=[IntrinsicInput(type=Type.int(width=1, sign=False), name='input')],
            outputs=[Type.int(width=1, sign=False)],
        ),
        '__builtin_avr_fmul': IntrinsicInfo(
            inputs=[
                IntrinsicInput(type=Type.int(width=1, sign=False), name='input'),
                IntrinsicInput(type=Type.int(width=1, sign=False), name='input'),
            ],
            outputs=[Type.int(width=2, sign=False)],
        ),
        '__builtin_avr_fmuls': IntrinsicInfo(
            inputs=[
                IntrinsicInput(type=Type.int(width=1, sign=True), name='input'),
                IntrinsicInput(type=Type.int(width=1, sign=True), name='input'),
            ],
            outputs=[Type.int(width=2, sign=True)],
        ),
        '__builtin_avr_fmulsu': IntrinsicInfo(
            inputs=[
                IntrinsicInput(type=Type.int(width=1, sign=True), name='input'),
                IntrinsicInput(type=Type.int(width=1, sign=False), name='input'),
            ],
            outputs=[Type.int(width=2, sign=True)],
        ),
    }

    def analyze_basic_blocks(
        self, func: Function, context: BasicBlockAnalysisContext
    ) -> None:
        # NOTE: The entry point does not call this function,
        # so IO regs are not displayed correctly in the RESET irq disasm

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

            block: BasicBlock = context.create_basic_block(func.arch, addr)
            while True:
                try:
                    insn = Instruction.decode(data.read(addr, 4))
                except ValueError:
                    break

                end_block = False
                idata = insn.idata.base or insn.idata
                if idata not in (
                    Instructions.BRBC,
                    Instructions.BRBS,
                    Instructions.CPSE,
                    Instructions.JMP,
                    Instructions.RET,
                    Instructions.RETI,
                    Instructions.RJMP,
                    Instructions.SBRC,
                    Instructions.SBRS,
                    Instructions.SBIC,
                    Instructions.SBIS,
                ):
                    match idata:
                        case Instructions.CALL | Instructions.RCALL:
                            if idata == Instructions.RCALL:
                                val = addr + insn.operands[-1].value
                            else:
                                val = insn.operands[-1].value

                            if not (0 <= val <= data.segments[0].length):
                                end_block = True
                            else:
                                data.define_auto_symbol_and_var_or_function(
                                    Symbol(
                                        SymbolType.FunctionSymbol, val, f'sub_{val:x}'
                                    )
                                )
                                data.add_function(val)
                                context.add_direct_code_reference(
                                    val, ArchAndAddr(self, addr)
                                )

                    op = next(
                        (op for op in insn.operands if op.op_type == OpType.ADDR_IO),
                        None,
                    )
                    if op is not None:
                        io_reg = data.get_symbol_at(
                            RAM_BEGIN + 0x20 + op.value,
                            namespace=SymbolType.DataSymbol,
                        )

                        arch_context['mapped_io'][addr] = {
                            'name': io_reg.name,
                            'addr': io_reg.address,
                        }

                    if end_block is False:
                        add_instruction_data(context, block, insn.data)
                        addr += len(insn.data)
                        continue

                match idata:
                    case Instructions.JMP | Instructions.RJMP:
                        val = insn.operands[0].value
                        if insn.idata == Instructions.RJMP:
                            val += addr

                        if not (0 <= val <= data.segments[0].length):
                            end_block = True
                        else:
                            blocks_to_process.append(val)
                            block.add_pending_outgoing_edge(
                                BranchType.UnconditionalBranch,
                                val,
                                func.arch,
                            )

                    case Instructions.BRBC | Instructions.BRBS:
                        val = addr + insn.operands[-1].value
                        blocks_to_process += [val, addr + 2]

                        if not (0 <= val <= data.segments[0].length):
                            end_block = True
                        else:
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

                    case (
                        Instructions.CPSE
                        | Instructions.SBRC
                        | Instructions.SBRS
                        | Instructions.SBIC
                        | Instructions.SBIS
                    ):
                        val = (
                            addr
                            + 2
                            + len(Instruction.decode(data.read(addr + 2, 4)).data)
                        )
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

                    case (
                        Instructions.EICALL
                        | Instructions.EIJMP
                        | Instructions.ICALL
                        | Instructions.IJMP
                    ):
                        block.add_pending_outgoing_edge(
                            BranchType.IndirectBranch, addr, func.arch
                        )

                if end_block is False:
                    add_instruction_data(context, block, insn.data)
                    block.end = addr + len(insn.data)
                else:
                    block.end = addr

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

        match Instructions(insn.idata.base or insn.idata):
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

            case (
                Instructions.SBRC
                | Instructions.SBRS
                | Instructions.SBIC
                | Instructions.SBIS
            ):
                try:
                    Instruction.decode(data[-2:])
                    val = 2
                except ValueError:
                    val = 4

                info.add_branch(BranchType.TrueBranch, (addr + 2 + val))
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

        if (context is not None) and (addr in context['mapped_io']):
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
        ]

        if len(insn.operands) > 0:
            tokens.append(InstructionTextToken(InstructionTextTokenType.TextToken, ' '))

        for op in insn.operands:
            match op.op_type:
                case OpType.REG_DST | OpType.REG_SRC:
                    reg = None
                    if insn.idata in (
                        Instructions.ADIW,
                        Instructions.MOVW,
                        Instructions.SBIW,
                    ):
                        match op.value:
                            case 26:
                                reg = 'X'
                            case 28:
                                reg = 'Y'
                            case 30:
                                reg = 'Z'

                        if reg is not None:
                            tokens.append(
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    reg,
                                )
                            )
                        else:
                            tokens += (
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    f'r{op.value + 1}',
                                ),
                                InstructionTextToken(
                                    InstructionTextTokenType.TextToken, ':'
                                ),
                                InstructionTextToken(
                                    InstructionTextTokenType.RegisterToken,
                                    f'r{op.value}',
                                ),
                            )

                    else:
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.RegisterToken,
                                f'r{op.value}',
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
        self,
        data: bytes,
        addr: int,
        il: LowLevelILFunction,
        insn: ILInstruction | None = None,
    ) -> int | None:
        if insn is None:
            try:
                insn = ILInstruction(addr, data, il, byte_swapped=False)
            except ValueError:
                return None

        insn.llil()
        return len(insn.data)

    def lift_function(
        self, func: LowLevelILFunction, context: FunctionLifterContext
    ) -> bool:
        data = func.view
        for block in context.blocks:
            context.prepare_block_translation(func, block.arch, block.start)
            label = func.get_label_for_address(block.arch, block.start)
            if label is not None:
                func.mark_label(label)

            addr = block.start
            while addr < block.end:
                if data.analysis_is_aborted:
                    break

                func.set_current_address(addr, block.arch)
                try:
                    insn = get_instruction_data(context, block, addr)
                except:
                    insn = data.read(addr, block.end - addr)

                try:
                    insn = ILInstruction(addr, insn, func, byte_swapped=False)
                except:
                    func.append(func.no_ret())
                    continue

                addr += self.get_instruction_low_level_il(
                    insn.data, addr, func, insn=insn
                )

                if insn.idata in (
                    Instructions.CPSE,
                    Instructions.SBIC,
                    Instructions.SBIS,
                    Instructions.SBRC,
                    Instructions.SBRS,
                ):
                    match insn.idata:
                        case Instructions.CPSE:
                            cond = func.compare_equal(size=1, a=insn.rd, b=insn.rr)

                        case Instructions.SBIC | Instructions.SBIS:
                            cond = func.test_bit(
                                size=1,
                                a=func.load(
                                    size=1,
                                    addr=insn.const(
                                        RAM_BEGIN + 0x20 + insn.op(OpType.ADDR_IO)
                                    ),
                                ),
                                b=insn.op_const(OpType.BIT_REG),
                            )

                        case Instructions.SBRC | Instructions.SBRS:
                            cond = func.test_bit(
                                size=1, a=insn.rr, b=insn.op_const(OpType.BIT_REG)
                            )

                    if insn.idata in (Instructions.SBIC, Instructions.SBRC):
                        cond = func.not_expr(size=1, value=cond)

                    next_len = len(Instruction.decode(data.read(addr, 4)).data)
                    t = LowLevelILLabel()
                    f = LowLevelILLabel()
                    func.append(func.if_expr(operand=cond, t=t, f=f))
                    func.mark_label(t)
                    func.append(func.jump(insn.ptr(addr + next_len)))
                    func.mark_label(f)

            curr_seg = data.get_segment_at(block.end - 1)
            if block.end == curr_seg.end:
                func.append(func.no_ret())
            else:
                exit_label = func.get_label_for_address(block.arch, block.end)
                if exit_label:
                    func.append(func.goto(exit_label))
                else:
                    func.append(func.jump(block.end))

        func.finalize()
        return True
