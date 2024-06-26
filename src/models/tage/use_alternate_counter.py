class UseAlternateCounter:
    """
    4-bit counter, default value is 0b1000
    """
    def __init__(self):
        self._state = 0b1000

    def update(self, taken):
        self._state = max(0, min(0b1111, self._state + (1 if taken else -1)))

    @property
    def is_use_alt(self) -> bool:
        return self._state >= 0b1000

    def __repr__(self):
        return f"UseAltOnNaCtr(value: {self._state:b}, is_use_alt={self.is_use_alt})"
