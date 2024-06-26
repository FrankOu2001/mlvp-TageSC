class BankTickCounter:
    """
    7-bit counter, default value is 0b0000000
    当达到最大值时，Tn表对应路的表项全部清零
    """
    _state = 0

    def update(self, avail: int, unavail: int) -> None:
        val = unavail - avail
        self._state = max(0, min(0b1111111, self._state + val))

    def reset_when_max(self) -> bool:
        if self._state == 0b1111111:
            self._state = 0
            return True
        else:
            return False
