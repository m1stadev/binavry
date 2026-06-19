from . import InstructionData

_DATA_INSNS = (
    InstructionData(name='ELPM',           mnem='elpm', sig='1001010111011000'),
    InstructionData(name='ELPM_z',         mnem='elpm', sig='1001000ddddd0110', op_order='d'),
    InstructionData(name='ELPM_zinc',      mnem='elpm', sig='1001000ddddd0111', op_order='d'),

    InstructionData(name='IN',             mnem='in',   sig='10110AAdddddAAAA', op_order='dA'),
    InstructionData(name='LAC',            mnem='lac',  sig='1001001ddddd0110', op_order='d'),
    InstructionData(name='LAS',            mnem='las',  sig='1001001ddddd0101', op_order='d'),
    InstructionData(name='LAT',            mnem='lat',  sig='1001001ddddd0111', op_order='d'),

    InstructionData(name='LD_x',           mnem='ld',   sig='1001000ddddd1100', op_order='d'),
    InstructionData(name='LD_xinc',        mnem='ld',   sig='1001000ddddd1101', op_order='d'),
    InstructionData(name='LD_xdec',        mnem='ld',   sig='1001000ddddd1110', op_order='d'),
    InstructionData(name='LD_y',           mnem='ld',   sig='1000000ddddd1000', op_order='d'),
    InstructionData(name='LD_yinc',        mnem='ld',   sig='1001000ddddd1001', op_order='d'),
    InstructionData(name='LD_ydec',        mnem='ld',   sig='1001000ddddd1010', op_order='d'),
    InstructionData(name='LD_z',           mnem='ld',   sig='1000000ddddd0000', op_order='d'),
    InstructionData(name='LD_zinc',        mnem='ld',   sig='1001000ddddd0001', op_order='d'),
    InstructionData(name='LD_zdec',        mnem='ld',   sig='1001000ddddd0010', op_order='d'),

    InstructionData(name='LDD_y',          mnem='ldd',  sig='10q0qq0ddddd1qqq', op_order='dq'),
    InstructionData(name='LDD_z',          mnem='ldd',  sig='10q0qq0ddddd0qqq', op_order='dq'),

    InstructionData(name='LDI',            mnem='ldi',  sig='1110KKKKddddKKKK', op_order='dK'),

    #InstructionData(name='LDS_rc',         mnem='lds',  sig='10100kkkddddkkkk', op_order='dk'),

    InstructionData(name='LPM',            mnem='lpm',  sig='1001010111001000'),
    InstructionData(name='LPM_z',          mnem='lpm',  sig='1001000ddddd0100', op_order='d'),
    InstructionData(name='LPM_zinc',       mnem='lpm',  sig='1001000ddddd0101', op_order='d'),

    InstructionData(name='MOV',            mnem='mov',  sig='001011rdddddrrrr', op_order='dr'),
    InstructionData(name='MOVW',           mnem='movw', sig='00000001ddddrrrr', op_order='dr'),
    InstructionData(name='OUT',            mnem='out',  sig='10111AArrrrrAAAA', op_order='Ar'),
    InstructionData(name='POP',            mnem='pop',  sig='1001000ddddd1111', op_order='d'),
    InstructionData(name='PUSH',           mnem='push', sig='1001001ddddd1111', op_order='d'),

    InstructionData(name='SPM',            mnem='spm',  sig='1001010111101000'),
    #InstructionData(name='SPM_ZINC_xm_xt', mnem='spm',  sig='1001010111111000'),

    InstructionData(name='ST_x',           mnem='st',   sig='1001001rrrrr1100', op_order='r'),
    InstructionData(name='ST_xinc',        mnem='st',   sig='1001001rrrrr1101', op_order='r'),
    InstructionData(name='ST_xdec',        mnem='st',   sig='1001001rrrrr1110', op_order='r'),
    InstructionData(name='ST_y',           mnem='st',   sig='1000001rrrrr1000', op_order='r'),
    InstructionData(name='ST_yinc',        mnem='st',   sig='1001001rrrrr1001', op_order='r'),
    InstructionData(name='ST_ydec',        mnem='st',   sig='1001001rrrrr1010', op_order='r'),
    InstructionData(name='ST_z',           mnem='st',   sig='1000001rrrrr0000', op_order='r'),
    InstructionData(name='ST_zinc',        mnem='st',   sig='1001001rrrrr0001', op_order='r'),
    InstructionData(name='ST_zdec',        mnem='st',   sig='1001001rrrrr0010', op_order='r'),

    InstructionData(name='STD_y',          mnem='std',  sig='10q0qq1rrrrr1qqq', op_order='qr'),
    InstructionData(name='STD_z',          mnem='std',  sig='10q0qq1rrrrr0qqq', op_order='qr'),

    InstructionData(name='STS_rc',         mnem='sts',  sig='10101kkkrrrrkkkk', op_order='kr'),
    InstructionData(name='XCH',            mnem='xch',  sig='1001001rrrrr0100', op_order='r'),

    InstructionData(name='LDS',            mnem='lds',  sig='1001000ddddd0000kkkkkkkkkkkkkkkk', op_order='dk'),
    InstructionData(name='STS',            mnem='sts',  sig='1001001rrrrr0000kkkkkkkkkkkkkkkk', op_order='kr'),
    )