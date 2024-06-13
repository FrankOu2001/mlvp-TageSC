from models.sc.signed_bit_counter import SignedBitCounter
from util import get_phy_br_idx

SC_TABLE_INFO_N_ROWS = 512
TAGE_BANKS = 2
SC_TABLE_N_ROWS = 256  # SC_TABLE_INFO_N_ROWS / TAGE_BANKS
HIST_LEN = (0, 4, 10, 16)
SC_IDX_MASK = 0xff  # (1 << ceil(log2(SC_TABLE_N_ROWS))) - 1


def get_idx(pc: int, hist_len: int, idx_fh) -> int:
    assert hist_len >= 0, "谁家历史长度能小于0？"
    idx = pc >> 1
    if hist_len:
        return idx ^ idx_fh & SC_IDX_MASK
    else:
        return idx & SC_IDX_MASK


class SCTable:
    def __init__(self, hist_len: int):
        self.hist_len = hist_len
        # 256行，4体
        self.table = [[SignedBitCounter() for w in range(2 * TAGE_BANKS)] for _ in range(SC_TABLE_N_ROWS)]

    def get(self, pc: int, idx_fh: int, tage_predict: bool, way: int) -> int:
        return self._get_ctr(pc, idx_fh, tage_predict, way).ctr

    def update(self, pc: int, idx_fh: int, tage_predict: bool, taken: bool, way: int):
        update_ctr = self._get_ctr(pc, idx_fh, tage_predict, way)
        update_ctr.update(taken)

    def _get_idx(self, pc: int, idx_fh: int):
        idx = ((pc >> 1) ^ idx_fh) if self.hist_len else (pc >> 1)
        return idx & SC_IDX_MASK

    def _get_ctr(self, pc: int, idx_fh: int, tage_predict: bool, way: int) -> SignedBitCounter:
        idx = get_idx(pc, self.hist_len, idx_fh)
        ctrs = self.table[idx]
        logical_way = get_phy_br_idx(pc >> 1, way)
        return ctrs[2 * logical_way: 2 * logical_way + 2][tage_predict]
