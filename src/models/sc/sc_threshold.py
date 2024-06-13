__all__ = ["SCThreshold"]

NEUTRAL_VAL = 0b10000
MAX_VAL = 0b11111


class SCThreshold:
    def __init__(self):
        self._ctr = NEUTRAL_VAL  # 5bit
        self._threshold = 6  # 8bit

    def get(self):
        return self._threshold

    def update(self, success: bool):
        # 三者顺序不能变动
        self.__update_ctr(success)
        self.__update_threshold_after_ctr()
        self.__update_ctr_after_threshold()

    def __update_ctr(self, success):
        val = self._ctr
        self._ctr = max(0, min(MAX_VAL, (1 if success else -1) + val))

    def __update_threshold_after_ctr(self):
        if self._ctr == MAX_VAL and self._threshold <= 31:
            self._threshold += 2
        elif self._ctr == 0 and self._threshold >= 6:
            self._threshold -= 2

    def __update_ctr_after_threshold(self):
        if self._ctr == MAX_VAL or self._ctr == 0:
            self._ctr = NEUTRAL_VAL
