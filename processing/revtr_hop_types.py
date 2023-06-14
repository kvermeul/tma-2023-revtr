import enum
from enum import IntEnum

class RevtrHopType(IntEnum):
    DUMMY                                         = 0
    DST_REV_SEGMENT                               = 1
    DST_SYM_REV_SEGMENT                           = 2
    TR_TO_SRC_REV_SEGMENT                         = 3
    TR_TO_SRC_REV_SEGMENT_BETWEEN                 = 4
    RR_REV_SEGMENT                                = 5
    SPOOF_RR_REV_SEGMENT                          = 6
    TS_ADJ_REV_SEGMENT                            = 7
    SPOOF_TS_ADJ_REV_SEGMENT                      = 8
    SPOOF_TS_ADJ_REV_SEGMENT_TS_ZERO              = 9
    SPOOF_TS_ADJ_REV_SEGMENT_TS_ZERO_DOUBLE_STAMP = 10

