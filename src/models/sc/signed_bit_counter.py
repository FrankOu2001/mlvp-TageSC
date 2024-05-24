class SignedBitCounter:
    def __init__(self):
        self._state = 0

    def update(self, taken: bool):
        s = self._state
        self._state = max(-32, min(31, s + (1 if taken else -1)))

    @property
    def ctr(self):
        return self._state
