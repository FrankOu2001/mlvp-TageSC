from collections import namedtuple

import mlvp
from collections import deque

from parameter import GLOBAL_HISTORY_LEN

__all__ = ["GlobalHistory"]

GLOBAL_HISTORY_MASK = (1 << GLOBAL_HISTORY_LEN) - 1

SC_TABLE_HIST_LEN = (GLOBAL_HISTORY_LEN, 4, 10, 16)
SC_FOLDED_HIST_LEN = (0, 4, 8, 8)


class GlobalHistory:
    def __init__(self, gh_len: int = GLOBAL_HISTORY_LEN):
        self.ghv = 0
        self._len = gh_len
        self._q = deque()

    def update(self, taken: bool):
        # g = self._ghv
        # self._ghv = (g << 1) | taken & GLOBAL_HISTORY_MASK
        self._q.append(taken)

    def apply_update(self):
        while len(self._q):
            g = self.ghv
            self.ghv = (g << 1) | self._q.popleft() & GLOBAL_HISTORY_MASK

    def get_fh(self, folded_len: int, hist_len: int):
        if folded_len == 0:
            return 0
        res = 0
        g = self.ghv & ((1 << hist_len) - 1)
        mask = (1 << folded_len) - 1
        for _ in range(0, min(self._len, hist_len), folded_len):
            res ^= g & mask
            g >>= folded_len
        return res


if __name__ == '__main__':
    g = GlobalHistory()
