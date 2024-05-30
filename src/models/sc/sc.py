from customtypes import FoldedHistory
from models.sc.sc_table import SCTable
from models.sc.sc_threshold import SCThreshold

HISTORY_LEN = (0, 4, 10, 16)


class SC:
    def __init__(self):
        self.tables = tuple(SCTable(hist_len) for hist_len in HISTORY_LEN)
        self.thresholds = tuple(SCThreshold() for _ in range(2))

    def update_if_use_sc(self, pc: int, fh: FoldedHistory, tage_predict: bool,
                         total_sum: int, predict: bool, taken: bool, way: int) -> bool:
        for i in range(4):
            t: SCTable = self.tables[i]
            t.update(pc, fh, tage_predict, taken, way)

        thres: SCThreshold = self.thresholds[way]
        if thres - 4 <= abs(total_sum) <= thres - 2:
            thres.update(predict == taken)
            return True
        else:
            return False

    def get_threshold(self, way: int):
        t: SCThreshold = self.thresholds[way]
        return t.signed_thres

    def get_sc_ctr_sum(self, pc: int, fh: FoldedHistory, tage_predict: bool, way: int):
        sc_sum = 0
        for i in range(4):
            t: SCTable = self.tables[i]
            sc_sum += t.get(pc, fh, tage_predict, way)

        return sc_sum
