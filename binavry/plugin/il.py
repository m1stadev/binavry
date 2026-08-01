from functools import cached_property

from binaryninja import (
    Architecture,
    LowLevelILConst,
    LowLevelILFunction,
    LowLevelILInstruction,
    LowLevelILLabel,
    RegisterName,
    SymbolType,
)
from binaryninja.lowlevelil import ExpressionIndex

from . import RAM_BEGIN, Instruction, Instructions, Operand, OpType
from .compat import add_instruction_data


class ILInstruction:
    def __init__(
        self, addr: int, data: bytes, il: LowLevelILFunction, byte_swapped: bool = True
    ):
        self._addr = addr
        self._raw = data
        self._insn = Instruction.decode(data, byte_swapped=byte_swapped)
        self._il = il

    @property
    def addr(self) -> int:
        return self._addr

    @property
    def idata(self):
        return self.insn.idata

    @property
    def insn(self) -> Instruction:
        return self._insn

    @property
    def raw(self) -> bytes:
        return self._raw

    @property
    def operands(self) -> tuple[Operand, ...]:
        return self.insn.operands

    @property
    def data(self) -> bytes:
        return self.insn.data

    def addr_expr(self, expr: ExpressionIndex) -> ExpressionIndex:
        return self._il.add(
            size=3,
            a=self.ptr(RAM_BEGIN),
            b=self._il.zero_extend(size=3, value=self.op_const(OpType.ADDR_IMM)),
        )

    def const(self, val: int) -> ExpressionIndex:
        return self._il.const(size=(((val.bit_length() + 7) // 8) or 1), value=val)

    def ptr(self, val: int) -> ExpressionIndex:
        return self._il.const_pointer(
            size=(((val.bit_length() + 7) // 8) or 1), value=val
        )

    def op(self, typ: OpType) -> int:
        return next(op.value for op in self.insn.operands if op.op_type == typ)

    def op_const(self, typ: OpType) -> ExpressionIndex:
        return self.const(self.op(typ))

    def op_ptr(self, typ: OpType):
        val = self.op(typ)
        return self._il.const_pointer(size=((val.bit_length() + 7) // 8), value=val)

    def label(self, addr: int) -> LowLevelILLabel | None:
        return self._il.get_label_for_address(arch=Architecture['AVR'], addr=addr)

    @property
    def rd_name(self) -> RegisterName:
        return RegisterName('r' + str(self.op(OpType.REG_DST)))

    @cached_property
    def rd(self) -> ExpressionIndex:
        return self._il.reg(size=1, reg=self.rd_name)

    @cached_property
    def rdw_name(self) -> tuple[str] | tuple[str, str]:
        dst = self.op(OpType.REG_DST)
        match dst:
            case 26:
                return tuple('X')

            case 28:
                return tuple('Y')

            case 30:
                return tuple('Z')

            case _:
                return ('r' + str(dst + 1), self.rd_name)

    @cached_property
    def rdw(self) -> ExpressionIndex:
        dst = self.op(OpType.REG_DST)
        match dst:
            case 26:
                return self._il.reg(size=2, reg='X')

            case 28:
                return self._il.reg(size=2, reg='Y')

            case 30:
                return self._il.reg(size=2, reg='Z')

            case _:
                return self._il.reg_split(
                    size=1, hi='r' + str(dst + 1), lo=self.rd_name
                )

    @property
    def rr_name(self) -> RegisterName:
        return RegisterName('r' + str(self.op(OpType.REG_SRC)))

    @cached_property
    def rr(self) -> ExpressionIndex:
        return self._il.reg(size=1, reg=self.rr_name)

    @cached_property
    def rrw_name(self) -> tuple[str] | tuple[str, str]:
        src = self.op(OpType.REG_SRC)
        match src:
            case 26:
                return tuple('X')

            case 28:
                return tuple('Y')

            case 30:
                return tuple('Z')

            case _:
                return ('r' + str(src + 1), self.rr_name)

    @cached_property
    def rrw(self) -> ExpressionIndex:
        src = self.op(OpType.REG_SRC)
        match src:
            case 26:
                return self._il.reg(size=2, reg='X')

            case 28:
                return self._il.reg(size=2, reg='Y')

            case 30:
                return self._il.reg(size=2, reg='Z')

            case _:
                return self._il.reg_split(
                    size=1, hi='r' + str(src + 1), lo=self.rr_name
                )

    def jump(self, addr: int) -> ExpressionIndex:
        label = None
        addr = self.const(addr)
        insn = LowLevelILInstruction.create(self._il, addr)
        if isinstance(insn, LowLevelILConst):
            label = self._il.get_label_for_address(Architecture['AVR'], insn.constant)

        if label is None:
            return self._il.jump(addr)

        else:
            return self._il.goto(label)

    def llil(self):
        base = self.idata.base or self.idata
        match [op.op_type for op in self.operands]:
            case [OpType.REG_DST, OpType.REG_SRC]:
                # MOV, MOVW, CP, CPC, CPSE, ADC, ADD, AND, EOR, FMUL/S/U, MUL/S/U, SBC, SUB
                match self.idata:
                    case Instructions.ADC | Instructions.ADD:
                        if self.idata == Instructions.ADC:
                            val = self._il.add_carry(
                                size=1,
                                a=self.rd,
                                b=self.rr,
                                carry=self._il.flag('c'),
                                flags='math',
                            )
                        else:
                            val = self._il.add(
                                size=1, a=self.rd, b=self.rr, flags='math'
                            )

                        self._il.append(
                            self._il.set_reg(
                                size=1,
                                reg=self.rd_name,
                                value=val,
                            )
                        )

                    case Instructions.AND | Instructions.EOR | Instructions.OR:
                        match self.idata:
                            case Instructions.AND:
                                op = self._il.and_expr

                            case Instructions.EOR:
                                op = self._il.xor_expr

                            case Instructions.OR:
                                op = self._il.or_expr

                        self._il.append(
                            self._il.set_reg(
                                size=1,
                                reg=self.rd_name,
                                value=op(size=1, a=self.rd, b=self.rr, flags='bit'),
                            )
                        )

                    case Instructions.CP | Instructions.CPC:
                        match self.idata:
                            case Instructions.CP:
                                expr = self._il.sub(
                                    size=1, a=self.rd, b=self.rr, flags='math'
                                )

                            case Instructions.CPC:
                                expr = self._il.sub_borrow(
                                    size=1,
                                    a=self.rd,
                                    b=self.rr,
                                    carry=self._il.flag('c'),
                                    flags='math',
                                )

                        self._il.append(expr)

                    case Instructions.CPSE:
                        pass

                    case Instructions.MOV:
                        self._il.append(
                            self._il.set_reg(size=1, reg=self.rd_name, value=self.rr)
                        )

                    case Instructions.MOVW:
                        if len(self.rdw_name) == 1:
                            self._il.append(
                                self._il.set_reg(
                                    size=2, reg=self.rdw_name[0], value=self.rrw
                                )
                            )

                        else:
                            self._il.append(
                                self._il.set_reg_split(
                                    size=1,
                                    hi=self.rdw_name[0],
                                    lo=self.rdw_name[1],
                                    value=self.rrw,
                                )
                            )

                    case Instructions.MUL | Instructions.MULS | Instructions.MULSU:
                        match self.idata:
                            case Instructions.MUL:
                                val = self._il.mult_double_prec_unsigned(
                                    size=1, a=self.rd, b=self.rr, flags='mul'
                                )

                            case Instructions.MULS:
                                val = self._il.mult_double_prec_signed(
                                    size=1, a=self.rd, b=self.rr, flags='mul'
                                )

                            case Instructions.MULSU:
                                val = None

                        if val is None:
                            self._il.append(self._il.unimplemented())

                        else:
                            self._il.append(
                                self._il.set_reg_split(
                                    size=1, hi='r1', lo='r0', value=val
                                )
                            )

                    case Instructions.SBC | Instructions.SUB:
                        match self.idata:
                            case Instructions.SUB:
                                val = self._il.sub(
                                    size=1,
                                    a=self.rd,
                                    b=self.rr,
                                )

                            case Instructions.SBC:
                                val = self._il.sub_borrow(
                                    size=1,
                                    a=self.rd,
                                    b=self.rr,
                                    carry=self._il.flag('c'),
                                )

                        self._il.append(
                            self._il.set_reg(size=1, reg=self.rd_name, value=val)
                        )

                    case _:
                        self._il.append(self._il.unimplemented())

            case [
                OpType.REG_DST
                | OpType.REG_X
                | OpType.REG_XDEC
                | OpType.REG_XINC
                | OpType.REG_Y
                | OpType.REG_YDEC
                | OpType.REG_YINC
                | OpType.REG_Z
                | OpType.REG_ZDEC
                | OpType.REG_ZINC,
                OpType.REG_SRC
                | OpType.REG_X
                | OpType.REG_XDEC
                | OpType.REG_XINC
                | OpType.REG_Y
                | OpType.REG_YDEC
                | OpType.REG_YINC
                | OpType.REG_Z
                | OpType.REG_ZDEC
                | OpType.REG_ZINC,
            ]:
                # ELPM Z/Z+, LD X/Y/Z (-/+), LDD Y/Z, LPM Z/Z+, ST X/Y/Z (-/+), STD Y/Z
                if self.idata.mnem == 'elpm':
                    self._il.append(self._il.unimplemented())

                else:
                    if self.operands[0].op_type == OpType.REG_DST:
                        xyz = self.operands[1]
                        is_load = True

                    else:
                        xyz = self.operands[0]
                        is_load = False

                    reg = None
                    match xyz.op_type:
                        case OpType.REG_X | OpType.REG_XDEC | OpType.REG_XINC:
                            reg = 'X'

                        case OpType.REG_Y | OpType.REG_YDEC | OpType.REG_YINC:
                            reg = 'Y'

                        case OpType.REG_Z | OpType.REG_ZDEC | OpType.REG_ZINC:
                            reg = 'Z'

                    pre = False
                    post = False
                    offset = 0
                    match xyz.op_type:
                        case OpType.REG_X | OpType.REG_Y | OpType.REG_Z:
                            offset = xyz.value

                        case OpType.REG_XDEC | OpType.REG_YDEC | OpType.REG_ZDEC:
                            pre = True

                        case OpType.REG_XINC | OpType.REG_YINC | OpType.REG_ZINC:
                            post = True

                    if pre is True:
                        self._il.append(
                            self._il.set_reg(
                                size=2,
                                reg=reg,
                                value=self._il.sub(
                                    size=2,
                                    a=self._il.reg(size=2, reg=reg),
                                    b=self.const(1),
                                ),
                            )
                        )

                    if offset != 0:
                        addr = self._il.add(
                            size=2,
                            a=self._il.reg(size=2, reg=reg),
                            b=self._il.zero_extend(size=3, value=self.const(offset)),
                        )

                    else:
                        addr = self._il.reg(size=2, reg=reg)

                    if self.idata.mnem != 'lpm':
                        addr = self._il.add(
                            size=3,
                            a=self.ptr(RAM_BEGIN),
                            b=self._il.zero_extend(size=3, value=addr),
                        )

                    if is_load:
                        self._il.append(
                            self._il.set_reg(
                                size=1,
                                reg=self.rd_name,
                                value=self._il.load(
                                    size=1,
                                    addr=addr,
                                ),
                            )
                        )

                    else:
                        self._il.append(
                            self._il.store(
                                size=1,
                                addr=addr,
                                value=self.rr,
                            )
                        )

                    if post is True:
                        self._il.append(
                            self._il.set_reg(
                                size=2,
                                reg=reg,
                                value=self._il.add(
                                    size=2,
                                    a=self._il.reg(size=2, reg=reg),
                                    b=self.const(1),
                                ),
                            )
                        )

            case [OpType.ADDR_IMM, OpType.REG_SRC]:
                # STS
                self._il.append(
                    self._il.store(
                        size=1,
                        addr=self._il.add(
                            size=3,
                            a=self.ptr(RAM_BEGIN),
                            b=self._il.zero_extend(
                                size=3, value=self.op_const(OpType.ADDR_IMM)
                            ),
                        ),
                        value=self.rr,
                    )
                )

            case [OpType.ADDR_IO, OpType.BIT_REG]:
                # CBI, SBI, SBIC, SBIS
                match self.idata:
                    case Instructions.CBI | Instructions.SBI:
                        addr = self._il.add(
                            size=3,
                            a=self.ptr(RAM_BEGIN),
                            b=self._il.zero_extend(
                                size=3, value=self.op_const(OpType.ADDR_IO)
                            ),
                        )

                        self._il.append(
                            self._il.store(
                                size=1,
                                addr=addr,
                                value=self._il.or_expr(
                                    size=1,
                                    a=self._il.load(
                                        size=1,
                                        addr=addr,
                                    ),
                                    b=self._il.shift_left(
                                        size=1,
                                        a=self.const(
                                            int(self.idata == Instructions.SBI)
                                        ),
                                        b=self.op_const(OpType.BIT_REG),
                                    ),
                                ),
                            )
                        )

                    case Instructions.SBIC | Instructions.SBIS:
                        pass

                    case _:
                        self._il.append(self._il.unimplemented())

            case [OpType.ADDR_IO, OpType.REG_SRC]:
                # OUT
                addr = 0x20 + self.op(OpType.ADDR_IO)
                expr = self._il.store(
                    size=1,
                    addr=self._il.add(
                        size=3,
                        a=self.ptr(RAM_BEGIN),
                        b=self._il.zero_extend(size=3, value=self.const(addr)),
                    ),
                    value=self.rr,
                )

                if self._il.view is not None:
                    reg = self._il.view.get_symbol_at(
                        RAM_BEGIN + addr,
                        namespace=SymbolType.DataSymbol,
                    )

                    if (reg is not None) and (reg.name in ('SPH', 'SPL')):
                        expr = self._il.set_reg(size=1, reg=reg.name, value=self.rr)

                self._il.append(expr)

            case [OpType.BIT_SREG, OpType.ADDR_IMM]:
                grp = None
                flag = self.op(OpType.BIT_SREG)
                match (flag, self.idata):
                    case (0, Instructions.BRBC):
                        grp = 'slt'

                    case (0, Instructions.BRBS):
                        grp = 'ult'

                    case (1, Instructions.BRBC):
                        grp = 'ne'

                    case (1, Instructions.BRBS):
                        grp = 'eq'

                    case (2, Instructions.BRBC):
                        grp = 'pos'

                    case (2, Instructions.BRBS):
                        grp = 'neg'

                    case (3, Instructions.BRBC):
                        grp = 'no'

                    case (3, Instructions.BRBS):
                        grp = 'ov'

                    case (4, Instructions.BRBC):
                        grp = 'sge'

                    case (4, Instructions.BRBS):
                        grp = 'uge'

                grp = None
                if grp is not None:
                    cond = self._il.flag_group(grp)
                else:
                    cond = self._il.flag(Architecture['AVR'].flags[flag])
                    if self.idata == Instructions.BRBC:
                        cond = self._il.not_expr(size=0, value=cond)

                t = (
                    self.label(self.addr + self.op(OpType.ADDR_IMM))
                    or LowLevelILLabel()
                )
                f = self.label(self.addr + 2) or LowLevelILLabel()

                self._il.append(self._il.if_expr(operand=cond, t=t, f=f))
                if not t.resolved:
                    self._il.mark_label(t)
                    self._il.append(self.jump(self.addr + self.op(OpType.ADDR_IMM)))

                if not f.resolved:
                    self._il.mark_label(f)

            case [OpType.REG_DST, OpType.ADDR_IMM]:
                # LDS
                self._il.append(
                    self._il.set_reg(
                        size=1,
                        reg=self.rd_name,
                        value=self._il.load(
                            size=1,
                            addr=self._il.add(
                                size=3,
                                a=self.ptr(RAM_BEGIN),
                                b=self._il.zero_extend(
                                    size=3, value=self.op_const(OpType.ADDR_IMM)
                                ),
                            ),
                        ),
                    )
                )

            case [OpType.REG_DST, OpType.IMM]:
                # LDI, CPI, ADIW, ANDI, ORI, SBCI, SBIW
                match self.idata:
                    case Instructions.LDI:
                        self._il.append(
                            self._il.set_reg(
                                size=1,
                                reg=self.rd_name,
                                value=self.op_const(OpType.IMM),
                            )
                        )

                    case Instructions.ANDI | Instructions.ORI:
                        if self.idata == Instructions.ANDI:
                            val = self._il.and_expr(
                                size=1,
                                a=self.rd,
                                b=self.op_const(OpType.IMM),
                                flags='bit',
                            )
                        else:
                            val = self._il.or_expr(
                                size=1,
                                a=self.rd,
                                b=self.op_const(OpType.IMM),
                                flags='bit',
                            )

                        self._il.append(
                            self._il.set_reg(size=1, reg=self.rd_name, value=val)
                        )

                    case Instructions.ADIW | Instructions.SBIW:
                        match self.idata:
                            case Instructions.ADIW:
                                op = self._il.add_carry

                            case Instructions.SBIW:
                                op = self._il.sub_borrow

                        val = op(
                            size=2,
                            a=self.rdw,
                            b=self.op_const(OpType.IMM),
                            carry=self._il.flag('c'),
                            flags='word',
                        )

                        if len(self.rdw_name) == 1:
                            expr = self._il.set_reg(
                                size=2, reg=self.rdw_name[0], value=val
                            )

                        else:
                            expr = self._il.set_reg_split(
                                size=1,
                                hi=self.rdw_name[0],
                                lo=self.rdw_name[1],
                                value=val,
                            )

                        self._il.append(expr)

                    case Instructions.SUBI | Instructions.SBCI:
                        match self.idata:
                            case Instructions.SUBI:
                                val = self._il.sub(
                                    size=1,
                                    a=self.rd,
                                    b=self.op_const(OpType.IMM),
                                    flags='math',
                                )

                            case Instructions.SBCI:
                                val = self._il.sub_borrow(
                                    size=1,
                                    a=self.rd,
                                    b=self.op_const(OpType.IMM),
                                    carry=self._il.flag('c'),
                                    flags='math',
                                )

                        self._il.append(
                            self._il.set_reg(size=1, reg=self.rd_name, value=val)
                        )

                    case Instructions.CPI:
                        self._il.append(
                            self._il.sub(
                                size=1,
                                a=self.rd,
                                b=self.op_const(OpType.IMM),
                                flags='math',
                            )
                        )

                    case _:
                        self._il.append(self._il.unimplemented())

            case [OpType.REG_DST, OpType.ADDR_IO]:
                # IN
                self._il.append(
                    self._il.set_reg(
                        size=1,
                        reg=self.rd_name,
                        value=self._il.load(
                            size=1,
                            addr=self._il.add(
                                size=3,
                                a=self.ptr(RAM_BEGIN),
                                b=self._il.zero_extend(
                                    size=3,
                                    value=self.const(0x20 + self.op(OpType.ADDR_IO)),
                                ),
                            ),
                        ),
                    )
                )

            case [OpType.REG_DST, OpType.BIT_REG]:
                # BLD, BST
                match self.idata:
                    case Instructions.BLD:
                        expr = self._il.set_reg(
                            size=1,
                            reg=self.rd_name,
                            value=self._il.or_expr(
                                size=1,
                                a=self.rd,
                                b=self._il.shift_left(
                                    size=1,
                                    a=self._il.flag('t'),
                                    b=self.op_const(OpType.BIT_REG),
                                ),
                            ),
                        )

                    case Instructions.BST:
                        expr = self._il.set_flag(
                            flag='t',
                            value=self._il.test_bit(
                                size=1, a=self.rd, b=self.op_const(OpType.BIT_REG)
                            ),
                        )

                self._il.append(expr)

            case [OpType.REG_SRC, OpType.BIT_REG]:
                pass

            case [OpType.REG_DST]:
                # ASR, LSR, ROR, SWAP, LAC, LAS, LAT,
                # POP, PUSH, COM, DEC, INC, NEG, SER
                match self.idata:
                    case Instructions.ASR:
                        val = self._il.arith_shift_right(
                            size=1, a=self.rd, b=self.const(1), flags='word'
                        )

                    case Instructions.CLR:
                        val = self.const(0)

                    case Instructions.COM:
                        val = self._il.sub(
                            size=1, a=self.rd, b=self.const(0xFF), flags='bit'
                        )

                    case Instructions.DEC:
                        val = self._il.sub(
                            size=1, a=self.rd, b=self.const(1), flags='bit'
                        )

                    case Instructions.INC:
                        val = self._il.add(
                            size=1, a=self.rd, b=self.const(1), flags='bit'
                        )

                    case Instructions.LSL:
                        val = self._il.shift_left(
                            size=1, a=self.rd, b=self.const(1), flags='bit'
                        )

                    case Instructions.LSR:
                        val = self._il.logical_shift_right(
                            size=1, a=self.rd, b=self.const(1), flags='word'
                        )

                    case Instructions.NEG:
                        val = self._il.neg_expr(size=1, value=self.rd, flags='math')

                    case Instructions.ROL:
                        val = self._il.rotate_left_carry(
                            size=1,
                            a=self.rd,
                            b=self.const(1),
                            carry=self._il.flag('c'),
                            flags='bit',
                        )

                    case Instructions.ROR:
                        val = self._il.rotate_right_carry(
                            size=1,
                            a=self.rd,
                            b=self.const(1),
                            carry=self._il.flag('c'),
                            flags='word',
                        )

                    case Instructions.POP:
                        val = self._il.pop(size=1)

                    case Instructions.SER:
                        val = self.const(0xFF)

                    case Instructions.SWAP:
                        val = self._il.rotate_right(size=1, a=self.rd, b=self.const(4))

                    case _:
                        val = None

                if val is not None:
                    self._il.append(
                        self._il.set_reg(size=1, reg=self.rd_name, value=val)
                    )

                else:
                    match self.idata:
                        case Instructions.PUSH:
                            self._il.append(self._il.push(size=1, value=self.rd))

                        case Instructions.TST:
                            self._il.append(
                                self._il.and_expr(
                                    size=1, a=self.rd, b=self.rd, flags='bit'
                                )
                            )

                        case _:
                            self._il.append(self._il.unimplemented())

            case [OpType.REG_SRC]:
                self._il.append(self._il.unimplemented())

            case [OpType.ADDR_IMM]:
                # RCALL, RJMP, CALL, JMP, DES, BRBC, BRBS
                match base:
                    case Instructions.CALL | Instructions.RCALL:
                        val = self.op(OpType.ADDR_IMM)
                        if base == Instructions.RCALL:
                            val += self.addr

                        self._il.append(self._il.call(self.ptr(val)))

                    case Instructions.JMP | Instructions.RJMP:
                        val = self.op(OpType.ADDR_IMM)
                        if base == Instructions.RJMP:
                            val += self.addr

                        self._il.append(self.jump(val))

                    case Instructions.BRBC | Instructions.BRBS:
                        grp = None
                        match self.idata.mnem[-2:]:
                            case 'ge':
                                grp = 'sge'

                            case 'lt':
                                grp = 'uge'

                            case 'sh':
                                grp = 'slt'

                            case 'lo':
                                grp = 'ult'

                            case 'ne':
                                grp = 'ne'

                            case 'eq':
                                grp = 'eq'

                            case 'pl':
                                grp = 'pos'

                            case 'mi':
                                grp = 'neg'

                            case 'vc':
                                grp = 'no'

                            case 'vs':
                                grp = 'ov'

                        grp = None
                        if grp is not None:
                            cond = self._il.flag_group(grp)
                        else:
                            cond = self._il.flag(
                                Architecture['AVR'].flags[
                                    Instruction.decode_as(
                                        data=self.data, idata=base, byte_swapped=False
                                    )
                                    .operands[0]
                                    .value
                                ]
                            )
                            if base == Instructions.BRBC:
                                cond = self._il.not_expr(size=0, value=cond)

                        t = (
                            self.label(self.addr + self.op(OpType.ADDR_IMM))
                            or LowLevelILLabel()
                        )
                        f = self.label(self.addr + 2) or LowLevelILLabel()

                        self._il.append(self._il.if_expr(operand=cond, t=t, f=f))
                        if not t.resolved:
                            self._il.mark_label(t)
                            self._il.append(
                                self.jump(self.addr + self.op(OpType.ADDR_IMM))
                            )

                        if not f.resolved:
                            self._il.mark_label(f)

                    case Instructions.DES:
                        self._il.append(self._il.unimplemented())

            case []:
                expr = None
                match self.idata:
                    case Instructions.BREAK:
                        expr = self._il.breakpoint()

                    case Instructions.ICALL | Instructions.IJMP:
                        val = self._il.reg(size=2, reg='Z')
                        match base:
                            case Instructions.ICALL:
                                expr = self._il.call(val)
                            case Instructions.IJMP:
                                expr = self._il.jump(val)

                    case Instructions.NOP:
                        expr = self._il.intrinsic(
                            outputs=[], intrinsic='__builtin_avr_nop', params=[]
                        )

                    case Instructions.SLEEP:
                        expr = self._il.intrinsic(
                            outputs=[], intrinsic='__builtin_avr_sleep', params=[]
                        )

                    case Instructions.WDR:
                        expr = self._il.intrinsic(
                            outputs=[], intrinsic='__builtin_avr_wdr', params=[]
                        )

                if expr is not None:
                    self._il.append(expr)
                else:
                    match base:
                        # SE(C,Z,N,V,S,H,T,I), CL(C,Z,N,V,S,H,T,I)
                        case Instructions.BSET | Instructions.BCLR:
                            if self.idata.is_base:
                                flag = Architecture['AVR'].get_flag_name(
                                    self.operands[-1].value
                                )

                            else:
                                flag = self.idata.mnem[-1]

                            self._il.append(
                                self._il.set_flag(
                                    flag=flag,
                                    value=self.const(int(base == Instructions.BSET)),
                                )
                            )

                        case Instructions.ELPM | Instructions.LPM | Instructions.SPM:
                            self._il.append(self._il.unimplemented())

                        case Instructions.EICALL | Instructions.EIJMP:
                            self._il.append(self._il.unimplemented())

                        case Instructions.RET | Instructions.RETI:
                            self._il.append(self._il.ret(dest=self._il.pop(size=2)))
                            if base == Instructions.RETI:
                                self._il.append(
                                    self._il.set_flag(flag='i', value=self.const(1))
                                )

                        case _:
                            self._il.append(self._il.unimplemented())
