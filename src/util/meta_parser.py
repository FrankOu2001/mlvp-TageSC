from UT_Tage_SC.xspcomm import *


class MetaParser:
    """Only out_last_stage_meta needs to parse"""

    def __init__(self, meta: XPin):
        self._meta = meta

    @property
    def meta(self):
        meta = self._meta
        return meta.value

    @property
    def takens(self):
        return self._bit(self.meta, 54), self._bit(self.meta, 55)

    @classmethod
    def get_takens(cls, meta):
        return cls._bit(meta, 54), cls._bit(meta, 55)

    @staticmethod
    def _bits(meta, high, low):
        assert low <= high
        mask = (1 << high) - 1
        return (meta & mask) >> low

    @staticmethod
    def _bit(meta, bit):
        return (meta >> bit) & 1


if __name__ == '__main__':
    x = XData(200, XData.In)
    x.SetWriteMode(XData.Imme)
    x.value = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
    print(x)
    m = MetaParser(x)
    print(m.takens)
    x.value = 0xf
    print(m.takens)
