from typing import Optional

import mlvp

from models.tage.bank_tick_counter import BankTickCounter as BTCtr
from models.tage.bimodal import BimodalPredictor
from models.tage.tagged import TaggedPredictor, ThreeBitCounter
from models.tage.use_alternate_counter import UseAlternateCounter as UACtr
from models.folded_history import FoldedHistory
from mlvp.modules.lfsr_64 import LFSR_64

def get_use_alt_idx(pc: int) -> int:
    return (pc >> 1) & 0x7f


class Tage:
    def __init__(self, lfsr: LFSR_64):
        self.t0 = BimodalPredictor()
        self.tn: list[TaggedPredictor] = [TaggedPredictor() for _ in range(4)]
        self.use_alt_on_na_ctrs: list[list[UACtr]] = [[UACtr(), UACtr()] for _ in range(128)]
        self.bank_tick_ctrs = (BTCtr(), BTCtr())
        self.lfsr = lfsr

    def get_tagged_ctr_and_bimodal_predict(
            self, pc: int, predict_fhs: list[FoldedHistory], way: int
    ) -> tuple[Optional[ThreeBitCounter], bool]:
        use_alt_on_na_ctr = self.use_alt_on_na_ctrs[get_use_alt_idx(pc)][way]

        t0 = self.t0.get(pc, way)
        ctr = self.__get_tage_ctr(pc, predict_fhs, way)
        use_alt = ctr is None or (use_alt_on_na_ctr.is_use_alt() and ctr.is_unconf)
        return None if use_alt else ctr.taken, t0

    def train(self, pc: int, train_fhs: list[FoldedHistory], provider_valid: bool, provider: int, provider_taken: bool,
              alt_taken: bool, train_taken: bool, way: int) -> None:
        if provider_valid:
            print(f'pc: {pc}, provider_valid: {provider_valid}, provider: {provider}, train_fhs: {train_fhs}')
            tagged = self.tn[provider]
            idx_fh, tag_fh, all_tag_fh = train_fhs[provider]
            ctr = tagged.get_ctr(pc, idx_fh, tag_fh, all_tag_fh, way)
            predict_diff = provider_taken != alt_taken
            provider_mispred = provider_taken != train_taken
            # Train tagged
            tagged.train(pc, idx_fh, tag_fh, all_tag_fh, way, train_taken)
            if predict_diff:
                u_idx = (pc >> 1) & 0x7f
                if ctr.is_unconf:
                    self.use_alt_on_na_ctrs[u_idx][way].update(provider_mispred)

                if provider_mispred:
                    # Tn predict incorrectly
                    tagged.set_us(pc, idx_fh, False, way)
                    # Allocate new entry
                    self.__allocate_tage_entry(pc, train_fhs, provider, train_taken, way)
                else:
                    tagged.set_us(pc, idx_fh, True, way)
        else:
            # Only t0 hit
            print("Train T0", train_taken)
            self.t0.train(pc, train_taken, way)
            # Allocate new entry
            self.__allocate_tage_entry(pc, train_fhs, provider, train_taken, way)
            pass
        pass

    def __get_tage_ctr(self, pc: int, folded_histories: list[FoldedHistory], way: int) -> Optional[ThreeBitCounter]:
        ctr = None
        for i in range(3, -1, -1):
            ctr = self.tn[i].get_ctr(pc, *folded_histories[i], way)
            if ctr is not None:
                break

        return ctr

    def __allocate_tage_entry(self, pc: int, train_fhs: list[FoldedHistory],
                              provider: int, train_taken: bool, way: int) -> None:
        if provider == 3:
            mlvp.warning("[Tage._alloc]: Can't allocate for t4.")
            return
        avail, unavail = 0, 0
        is_allocatable = False
        allocatable_slots = [0] * 4
        for i in range(4):
            valid, entry = self.tn[i].get_entry(pc, *train_fhs[i], way)
            allocatable = (not valid and not entry.us) and (i > provider)
            is_allocatable |= allocatable
            allocatable_slots[i] = allocatable
            if allocatable:
                avail += 1
            else:
                unavail += 1
        pass
        # 在每次需要分配表时，进行动态重置usefulness标志位
        b: BTCtr = self.bank_tick_ctrs[way]
        b.update(avail, unavail)
        if b.reset_when_max():
            self.tn[provider].clear_us(way)
        if not is_allocatable:
            mlvp.error("Tage分配失败")
            return

        rand = self.lfsr.rand & 0xf
        rand_status = [(rand >> i) & 1 for i in range(4)]
        first_entry, masked_entry = 0, 0
        for i in range(4):
            if not allocatable_slots[i]:
                continue
            first_entry = i if not first_entry else 0
            masked_entry = i if not masked_entry and rand_status[i] else 0
        allocate = masked_entry if allocatable_slots[masked_entry] else first_entry
        idx_fh, tag_fh, all_tag_fh = train_fhs[allocate]
        _, allocate_entry = self.tn[allocate].get_entry(pc, idx_fh, tag_fh, all_tag_fh, way)
        allocate_entry.reset(pc, tag_fh, all_tag_fh, train_taken)
