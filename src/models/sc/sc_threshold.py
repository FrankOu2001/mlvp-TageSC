NEUTRAL_VAL = 0b10000
MAX_VAL = 0b11111


class SCThreshold:
    def __init__(self):
        self._ctr = NEUTRAL_VAL  # 5bit
        self._thres = 6  # 8bit

    def update(self, success: bool):
        # 三者顺序不能变动
        self._update_ctr(success)
        self._update_thres_after_ctr(success)
        self._update_ctr_after_thres()

    @property
    def ctr(self):
        return self._ctr

    @property
    def signed_thres(self):
        t = self._thres
        is_neg = t & 0b10000000 > 0
        return t - (0b100000000 if is_neg else 0)

    def _update_ctr(self, success):
        val = self._ctr
        self._ctr = max(0, min(MAX_VAL, val + (1 if success else -1)))

    def _update_thres_after_ctr(self, success):
        if self._ctr == MAX_VAL and self._thres <= 31:
            self._thres += 2
        elif self._ctr == 0 and self._thres >= 6:
            self._thres -= 2

    def _update_ctr_after_thres(self):
        if self._ctr == MAX_VAL or self._ctr == 0:
            self._ctr = NEUTRAL_VAL
