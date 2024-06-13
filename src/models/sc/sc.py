from models.sc.sc_table import SCTable
from models.sc.sc_threshold import SCThreshold

__all__ = ["SC"]

HISTORY_LEN = (0, 4, 10, 16)


class SC:
    def __init__(self):
        self.tables = [SCTable(hist_len) for hist_len in HISTORY_LEN]
        self.sc_threshold = [SCThreshold(), SCThreshold()]

    def train(
        self, pc: int, sc_fhs: list[int], old_total_sum: int, tage_predict: bool, sc_predict: bool, taken: bool, way: int
    ) -> None:
        """
        sum使用的是预测时产生的oldCtrs:
        https://github.com/OpenXiangShan/XiangShan/blob/545d7be08861a078dc54ccc114bf1792e894ab54/src/main/scala/xiangshan/frontend/SC.scala#L334-L335
        """
        threshold = self.sc_threshold[way].get()
        if tage_predict != sc_predict and \
                threshold - 4 <= abs(old_total_sum) <= threshold - 2:
            success = sc_predict == taken
            self.sc_threshold[way].update(success)
        # Update SC Tables
        for i in range(4):
            self.tables[i].update(pc, sc_fhs[i], tage_predict, taken, way)

    def get_sc_ctr_sum(self, pc: int, sc_fhs: list[int], tage_predict: bool, way: int) -> int:
        sc_sum = 0

        for i in range(4):
            x = self.tables[i].get(pc, sc_fhs[i], tage_predict, way)
            sc_sum += (x << 1) + 1

        assert sc_sum != 0, "have no discussion about sc_sum = 0"
        return sc_sum

    def get_threshold(self, way: int) -> SCThreshold:
        return self.sc_threshold[way].get()

