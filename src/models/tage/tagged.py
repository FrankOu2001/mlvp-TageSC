import mlvp

from parameter import *
from typing import Optional

__all__ = ["ThreeBitCounter", "TaggedPredictor"]


def get_idx_and_tag(pc: int, idx_fh: int, tag_fh: int, all_tag_fg: int) -> tuple[int, int]:
    """
    :param pc: pc
    :param idx_fh: 文档中的fh
    :param tag_fh:  文档中的fh1
    :param all_tag_fg: 文档中的fh2
    :return: 访问表项的索引和对应的哈希值
    """
    idx = (idx_fh ^ (pc >> 1)) & 0x7ff  # index是11位
    tag = (tag_fh ^ (all_tag_fg << 1) ^ (pc >> 1)) & 0xff  # tag是8位
    return idx, tag


def get_idx(pc: int, idx_fh: int) -> int:
    return (idx_fh ^ (pc >> 1)) & 0x7ff  # index是11位


def get_tag(pc: int, tag_fh: int, all_tag_fh: int):
    return (tag_fh ^ (all_tag_fh << 1) ^ (pc >> 1)) & 0xff  # tag是8位


class ThreeBitCounter:
    def __init__(self, taken):
        self._v = 0b100 if taken else 0b011

    def reset(self, taken):
        self._v = 0b100 if taken else 0b011

    def update(self, taken):
        self._v = max(0, min(0b111, (1 if taken else -1) + self._v))

    @property
    def value(self):
        return self._v

    @property
    def taken(self):
        return self._v >= 0b100

    @property
    def is_unconf(self):
        pos = 1 << (TAGE_CTR_BITS - 1)
        neg = pos - 1
        # return self._v in {pos, neg}
        return self._v in [0b100, 0b011]

    def __repr__(self):
        return f"pred(value={self._v}, taken={self.taken}, is_unconf={self.is_unconf})"


class TaggedEntry:
    ctr: Optional[ThreeBitCounter] = None
    tag = 0
    us = 0

    def __repr__(self):
        return f"TaggedEntry(ctr={self.ctr}, tag={self.tag}, us={self.us})"

    def reset(self, pc, tag_fh, all_tag_fh, taken):
        self.ctr = ThreeBitCounter(taken)
        self.tag = get_tag(pc, tag_fh, all_tag_fh)
        self.us = 0


class TaggedPredictor:
    def __init__(self):
        self.table: tuple[tuple[TaggedEntry, ...], ...] = tuple(
            (TaggedEntry(), TaggedEntry()) for _ in range(BT_SIZE)
        )

    def get_entry(self, pc: int, idx_fh, tag_fh, all_tag_fh, way: int) -> tuple[bool, TaggedEntry]:
        idx, tag = get_idx_and_tag(pc, idx_fh, tag_fh, all_tag_fh)
        mlvp.debug(f"Get Tagged Entry of way{way}: pc: {pc:x}, idx: {idx}, tag: {tag}")
        logical_way = (way & 1) ^ ((pc >> 1) & 1)
        t: TaggedEntry = self.table[idx][logical_way]
        return (t.ctr is not None and t.tag == tag), t

    # def train(self, pc: int, idx_fh, tag_fh, all_tag_fh, way: int, taken: bool) -> bool:
    #     valid, t = self.get_entry(pc, idx_fh, tag_fh, all_tag_fh, way)
    #     if valid:
    #         t.ctr.update(taken)
    #         mlvp.info(f"Update Tagged.")
    #         return True
    #     return False

    def set_us(self, pc: int, idx_fh: int, is_useful: bool, way: int) -> None:
        idx = get_idx(pc, idx_fh)
        self.table[idx][way].us = 1 if is_useful else 0

    def clear_us(self, way: int) -> None:
        for i in range(BT_SIZE):
            self.table[i][way].us = 0
