import random
from collections import deque, namedtuple
from typing import NamedTuple
from typing import Optional

from mlvp import error

from models.env.fake_ifu import FakeFTBEntry
from models.env.global_history import *
from util.meta_parser import MetaParser

FTQEntry = namedtuple('FTQEntry',
                      ['pc', 'block', 'predict', 'meta', 'redirect'])


class FakeFTQEntry(NamedTuple):
    block: FakeFTBEntry
    meta: int
    redirect: int


class FakeFTQ:
    def __init__(self, parse: MetaParser, delay=False):
        self._q: deque[FakeFTQEntry] = deque()
        self._parse = parse
        self._mis = False
        self._delay = delay
        self._count = 2 if self._delay else 0

    def add_to_ftq(self, block: FakeFTBEntry, redirect: Optional[int], pred_ghv: GlobalHistory):
        if not block.br_slot.valid and not block.tail_slot.valid:
            error("Trying to add an empty instruction block.")
        assert block.br_slot.valid or block.tail_slot.valid, "Empty Instruction Block."
        parser = self._parse
        meta = parser.meta
        predicts = parser.takens

        if block.br_slot.valid:
            pred_ghv.update(block.br_slot.taken)
            if block.br_slot.taken != predicts[0]:
                self._mis = True

        if block.tail_slot.valid and block.tail_slot.sharing:
            pred_ghv.update(block.tail_slot.taken)
            if block.tail_slot.taken != predicts[1]:
                self._mis = True

        e = FakeFTQEntry(block, meta, redirect)
        self._q.append(e)

    def get_update_and_redirect(self, ghv: GlobalHistory):
        if self._count > 0 or len(self._q) == 0:
            self._count = max(0, self._count - 1)
            return {'valid': 0}, None

        self._count = random.randint(1, 5) if self._delay else 0
        e = self._q.popleft()
        predict_takens = self._parse.get_takens(e.meta)
        redirect = e.redirect

        # update global history
        if e.block.br_slot.valid:
            ghv.update(e.block.br_slot.taken)
        if e.block.tail_slot.valid and e.block.tail_slot.sharing:
            ghv.update(e.block.tail_slot.taken)

        update = {
            'valid': 1,
            'bits': {
                'pc': e.block.pc,
                'meta': e.meta,
                'br_taken_mask_0': e.block.br_slot.taken,
                'br_taken_mask_1': e.block.tail_slot.taken,
                'mispred_mask_0': predict_takens[0] != e.block.br_slot.taken,
                'mispred_mask_1': predict_takens[1] != e.block.tail_slot.taken and e.block.tail_slot.sharing,
                'ftb_entry': {
                    'valid': True,
                    'brSlots_0': {'valid': e.block.br_slot.valid},
                    'tailSlot': {
                        'valid': e.block.tail_slot.valid,
                        'sharing': e.block.tail_slot.sharing
                    }
                },
                'folded_hist': {
                    "hist_17_folded_hist": ghv.get_fh(11),
                    "hist_16_folded_hist": ghv.get_fh(11),
                    "hist_15_folded_hist": ghv.get_fh(7),
                    "hist_14_folded_hist": ghv.get_fh(8),  # and t0.tag
                    "hist_12_folded_hist": ghv.get_fh(4),  # for sc1
                    "hist_11_folded_hist": ghv.get_fh(8),  # for sc2
                    "hist_9_folded_hist": ghv.get_fh(7),
                    "hist_8_folded_hist": ghv.get_fh(8),
                    "hist_7_folded_hist": ghv.get_fh(7),
                    "hist_5_folded_hist": ghv.get_fh(7),
                    "hist_4_folded_hist": ghv.get_fh(8),
                    "hist_3_folded_hist": ghv.get_fh(8),
                    "hist_2_folded_hist": ghv.get_fh(8),  # for sc3
                    "hist_1_folded_hist": ghv.get_fh(11),
                }
            }
        }
        self._mis = False
        ghv.apply_update()
        return update, redirect

    @property
    def has_mispred(self):
        return self._mis
