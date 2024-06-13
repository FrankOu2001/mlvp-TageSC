from UT_Tage_SC.xspcomm import *
from dataclasses import dataclass
from typing import NamedTuple

__all__ = ["MetaParser"]


def bits(meta, high, low):
    assert low <= high
    mask = (1 << (high + 1)) - 1
    return (meta & mask) >> low


def bit(meta, bit):
    return (meta >> bit) & 1


class SCMeta(NamedTuple):
    sc_preds: list[int]
    sc_used: list[int]
    tage_takens: list[int]
    sc_ctrs: list[list[int]]


class MetaParser:
    """Only out_last_stage_meta needs to parse"""

    def __init__(self, meta: int):
        self._meta = meta

    @property
    def meta(self):
        return self._meta

    @property
    def providers_valid(self):
        return bit(self.meta, 84), bit(self.meta, 87)

    @property
    def providers(self):
        return bits(self.meta, 83, 82), bits(self.meta, 86, 85)

    @property
    def providerResps_ctr(self):
        return bits(self.meta, 76, 74), bits(self.meta, 81, 79)

    @property
    def altUsed(self):
        return bit(self.meta, 70), bit(self.meta, 71)

    @property
    def altDiffers(self):
        return bit(self.meta, 68), bit(self.meta, 69)

    @property
    def basecnts(self):
        """ s1_bimCtr """
        return bits(self.meta, 65, 64), bits(self.meta, 67, 66)

    @property
    def takens(self):
        return bit(self.meta, 54), bit(self.meta, 55)

    @property
    def scMeta(self):
        tage_takens = [bit(self.meta, 52), bit(self.meta, 53)]
        sc_used = [bit(self.meta, 50), bit(self.meta, 51)]
        sc_preds = [bit(self.meta, 48), bit(self.meta, 49)]
        sc_ctrs = [bits(self.meta, x + 5, x) for x in range(0, 48, 6)]
        return SCMeta(sc_preds, sc_used, tage_takens, [sc_ctrs[:4], sc_ctrs[4:]])


if __name__ == '__main__':
    print(bin(bits(0b01010101, 6, 3)))

