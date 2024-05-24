from parameter import *


def is_unconfident(ctr: int) -> bool:
    pos_unconfident = ctr == (1 << (TAGE_CTR_BITS - 1))  # ctr == b011
    neg_unconfident = ctr == (1 << (TAGE_CTR_BITS - 1)) - 1  # ctr == b100
    return pos_unconfident or neg_unconfident


def get_tagged_idx(pc: int, idx_fh: int) -> int:
    return idx_fh ^ (pc >> 1) & 0x7ff  # index是11位


def get_tagged_tag(pc: int, tag_fh: int, all_tag_fh: int):
    return tag_fh ^ all_tag_fh ^ (pc >> 1) & 0xff  # tag是8位


def get_idx_tag(pc: int, idx_fh: int, tag_fh: int, all_tag_fg: int) -> tuple[int, int]:
    """
    :param pc: pc
    :param idx_fh: 文档中的fh
    :param tag_fh:  文档中的fh1
    :param all_tag_fg: 文档中的fh2
    :return: 访问表项的索引和对应的哈希值
    """
    idx = idx_fh ^ (pc >> 1) & 0x7ff  # index是11位
    tag = tag_fh ^ all_tag_fg ^ (pc >> 1) & 0xff  # tag是8位
    return idx, tag


class TaggedEntry:
    tag = 0
    ctr = 0
    valid = False
    us = 0


class TaggedPredictor:
    def __init__(self):
        self.table: tuple[tuple[TaggedEntry, ...], ...] = tuple(
            (TaggedEntry(), TaggedEntry()) for _ in range(BT_SIZE)
        )

    def is_hit(self, idx: int, tag: int, way: int) -> bool:
        t = self.table[idx][way]
        return t.valid and t.tag == tag

    def are_hit(self, idx: int, tag: int) -> tuple[bool, ...]:
        return tuple(t.valid and t.tag == tag for t in self.table[idx])

    def get(self, idx: int, way: int) -> TaggedEntry:
        return self.table[idx][way]

    def gets(self, idx: int) -> tuple[TaggedEntry, ...]:
        return self.table[idx]

    def train(self, idx: int, taken: int, way: int) -> None:
        t: TaggedEntry = self.table[idx][way]
        t.ctr = max(0, min(0b111, t.ctr + (1 if taken else -1)))

    def reset_entry(self, idx: int, tag: int, taken: bool, way: int) -> None:
        t: TaggedEntry = self.table[idx][way]
        t.valid = 1
        t.tag = tag
        t.ctr = 0b100 if taken else 0b011
        t.us = 0

    def set_us(self, idx: int, value: int, way: int) -> None:
        self.table[idx][way].us = value

    def clear_us(self, way: int) -> None:
        for i in range(BT_SIZE):
            self.table[i][way].us = 0
