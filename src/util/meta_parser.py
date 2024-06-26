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
    def meta(self) -> int:
        return self._meta

    @property
    def providers_valid(self) -> tuple[int, int]:
        return bit(self.meta, 84), bit(self.meta, 87)

    @property
    def providers(self) -> tuple[int, int]:
        return bits(self.meta, 83, 82), bits(self.meta, 86, 85)

    @property
    def providerResps_ctr(self) -> tuple[int, int]:
        return bits(self.meta, 76, 74), bits(self.meta, 81, 79)

    @property
    def providerResps_u(self) -> tuple[int, int]:
        return bit(self.meta, 73), bit(self.meta, 78)

    @property
    def providerResps_unconf(self) -> tuple[int, int]:
        return bit(self.meta, 72), bit(self.meta, 77)

    @property
    def altUsed(self) -> tuple[int, int]:
        return bit(self.meta, 70), bit(self.meta, 71)

    @property
    def altDiffers(self) -> tuple[int, int]:
        return bit(self.meta, 68), bit(self.meta, 69)

    @property
    def basecnts(self) -> tuple[int, int]:
        """ s1_bimCtr """
        return bits(self.meta, 65, 64), bits(self.meta, 67, 66)

    @property
    def allocates(self):
        a_0 = [bit(self.meta, i) for i in range(56, 60)]
        a_1 = [bit(self.meta, i) for i in range(60, 64)]

        return a_0, a_1

    @property
    def takens(self) -> tuple[int, int]:
        return bit(self.meta, 54), bit(self.meta, 55)

    @property
    def scMeta(self):
        tage_takens = [bit(self.meta, 52), bit(self.meta, 53)]
        sc_used = [bit(self.meta, 50), bit(self.meta, 51)]
        sc_preds = [bit(self.meta, 48), bit(self.meta, 49)]
        sc_ctrs = [bits(self.meta, x + 5, x) for x in range(0, 48, 6)]
        return SCMeta(sc_preds, sc_used, tage_takens, [sc_ctrs[:4], sc_ctrs[4:]])

    def __repr__(self):
        d = {
            'providers_valid': self.providers_valid,
            'providers': self.providers,
            'providerResps_ctr': self.providerResps_ctr,
            'providerResps_u': self.providerResps_u,
            'providerResps_unconf': self.providerResps_unconf,
            'altUsed': self.altUsed,
            'altDiffers': self.altDiffers,
            'basecnts': self.basecnts,
            'takens': self.takens,
            'scMeta': self.scMeta,
        }
        return str(d)


if __name__ == '__main__':
    print(bin(bits(0b01010101, 6, 3)))

