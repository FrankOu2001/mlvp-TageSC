from parameter import GLOBAL_HISTORY_LEN
from collections import namedtuple

__all__ = ["GlobalHistory", "FoldedHistory", "TageHistory"]

GLOBAL_HISTORY_MASK = (1 << GLOBAL_HISTORY_LEN) - 1

TABLE_HIST_LEN = (8, 13, 32, 119)
FOLDED_HIST_LEN = (
    (8, 8, 7),
    (11, 8, 7),
    (11, 8, 7),
    (11, 8, 7),
)

FoldedHistory = namedtuple('FoldedHistory', ['idx', 'tag', 'all_tag'])
TageHistory = namedtuple('TageHistory', ['t0', 't1', 't2', 't3'])


class GlobalHistory:
    def __init__(self, gh_len: int = GLOBAL_HISTORY_LEN):
        self._ghv = 0
        self._len = gh_len

    def update(self, taken: bool):
        g = self._ghv
        self._ghv = (g << 1) | taken & GLOBAL_HISTORY_MASK

    def get_fh(self, hist_len: int):
        res = 0
        g = self._ghv
        mask = (1 << hist_len) - 1
        for _ in range(0, self._len, hist_len):
            res ^= g & mask
            g >>= hist_len
        return res

    def get_all_fh(self):
        res = []
        for i, e in enumerate(FOLDED_HIST_LEN):
            mask = (1 << TABLE_HIST_LEN[i]) - 1
            res.append(
                FoldedHistory(*[self.get_fh(x) & mask for x in e])
            )
        return TageHistory(*res)

    @property
    def ghv(self):
        return self._ghv


if __name__ == '__main__':
    g = GlobalHistory()
    for i in range(10):
        g.update(i % 3 == 0)
    print(g.get_all_fh())
