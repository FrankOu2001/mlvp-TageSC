from collections import namedtuple
from dataclasses import dataclass
from typing import NamedTuple

# for All
FoldedHistory = namedtuple('FoldedHistory', ['idx_fh', 'tag_fh', 'all_tag_fh'])


@dataclass
class TaggedEntry:
    tag = 0
    ctr = 0
    valid = False
    us = 0


# for Tage
TageMeta = namedtuple("TageMea", [])


class TageUpdateInfo(NamedTuple):
    """
    香山的TageSC实现中, provider是提供预测信息的标签预测器, altpred是基础预测器
    """
    pc: int
    folded_history: tuple[FoldedHistory, ...]
    # mis_predict: bool
    train_taken: bool
    provider: int  # 如果provider是0, 代表没有命中的标签预测器
    provider_taken: bool
    alt_taken: bool
