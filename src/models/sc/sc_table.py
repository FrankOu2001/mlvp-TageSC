from customtypes import FoldedHistory
from models.sc.signed_bit_counter import SignedBitCounter
from functools import reduce
from util import get_phy_br_idx

SC_TABLE_INFO_N_ROWS = 512
TAGE_BANKS = 2
SC_TABLE_N_ROWS = 256  # SC_TABLE_INFO_N_ROWS / TAGE_BANKS
HIST_LEN = (0, 4, 10, 16)
SC_IDX_MASK = 0xff  # (1 << ceil(log2(SC_TABLE_N_ROWS))) - 1


def get_idx(pc: int, hist_len: int, fh: FoldedHistory) -> int:
    assert hist_len >= 0, "谁家历史长度能小于0？"
    idx = pc >> 1
    if hist_len:
        return idx ^ fh.idx_fh & SC_IDX_MASK
    else:
        return idx & SC_IDX_MASK


class SCTable:
    def __init__(self, hist_len: int):
        self.hist_len = hist_len
        self.table: tuple[tuple[SignedBitCounter, ...], ...] = tuple(
            # 256行，4体
            tuple(SignedBitCounter() for w in range(2 * TAGE_BANKS)) for _ in range(SC_TABLE_N_ROWS)
        )

    def get(self, pc: int, fh: FoldedHistory, tage_predict: bool, way: int) -> int:
        return self._get_ctr(pc, fh, tage_predict, way).ctr

    def gets(self, pc: int, fh: FoldedHistory, tage_predicts: tuple[bool, bool]) -> tuple[tuple[int, ...], ...]:
        """
        返回两路预测的计数器的值
        :param pc:
        :param fh:
        :param tage_predicts:
        :return:
        """
        return tuple(self.get(pc, fh, tage_predicts[w], w) for w in range(2))

    def update(self, pc: int, fh: FoldedHistory, tage_predict: bool, taken: bool, way: int):
        update_ctr = self._get_ctr(pc, fh, tage_predict, way)
        update_ctr.update(taken)

    def updates(self, pc: int, fh: FoldedHistory, tage_predicts: tuple[bool, bool],
                takens: tuple[bool, bool]):
        # takens必须是物理索引的结果，而updateMeta中包含的是逻辑索引的顺序，所以传入先从逻辑索引转换到物理索引
        update_ctrs = self._get_ctrs(pc, fh, tage_predicts)
        # https://chatgpt.com/share/f448e315-e9d2-47f0-9f8a-78cb6be29ba3
        for ctr, taken in zip(update_ctrs, takens):
            ctr.update(takens)
        pass

    def _get_idx(self, pc: int, fh: FoldedHistory):
        idx = ((pc >> 1) ^ fh.idx_fh) if self.hist_len else (pc >> 1)
        return idx & SC_IDX_MASK

    def _get_ctr(self, pc: int, fh: FoldedHistory, tage_predict: bool, way: int) -> SignedBitCounter:
        idx = get_idx(pc, self.hist_len, fh)
        ctrs: tuple[SignedBitCounter, ...] = self.table[idx]
        l_idx = get_phy_br_idx(pc >> 1, way)
        return ctrs[2*way: 2*way+2][l_idx][tage_predict]

    def _get_ctrs(self, pc: int, fh: FoldedHistory, tage_predicts: tuple[bool, bool]) -> tuple[SignedBitCounter, ...]:
        # idx = get_idx(pc, self.hist_len, fh)
        # crts: tuple[SignedBitCounter, ...] = self.table[idx]
        # # per_br_ctrs_unshuffled = (tuple(x.ctr for x in e[:2]), tuple(x.ctr for x in e[2:]))
        # per_br_ctrs_unshuffled = tuple(crts[i:i + 2] for i in range(0, len(crts), 2))
        # per_br_ctrs: tuple[tuple[int, ...], ...] = tuple(
        #     per_br_ctrs_unshuffled[get_phy_br_idx(pc >> 1, i)] for i in range(2)
        # )
        # return tuple(per_br_ctrs[w][tage_predicts[w]] for w in range(2))
        return tuple(self._get_ctr(pc, fh, tage_predicts[w], w) for w in range(2))


if __name__ == '__main__':
    t = SCTable(1)
    print(t.gets(0, FoldedHistory(0, 0, 0), [True, True]))
