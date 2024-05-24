import mlvp

from customtypes import *
from models.tage.bank_tick_counter import BankTickCounter as BTCtr
from models.tage.bimodal import BimodalPredictor
from models.tage.tagged import TaggedPredictor, get_idx_tag
from models.tage.use_alternate_counter import UseAlternateCounter as UACtr
from typing import Optional


class Tage:
    def __init__(self, lfsr):
        self.t0 = BimodalPredictor()
        self.tn: tuple[TaggedPredictor, ...] = tuple(TaggedPredictor() for _ in range(4))
        self.use_alt_on_na_ctrs: tuple[tuple[UACtr, ...], ...] = tuple((UACtr(), UACtr()) for _ in range(128))
        self.bank_tick_ctrs: tuple[tuple[BTCtr, ...], ...] = (BTCtr(), BTCtr())
        self.lfsr = lfsr

    def get_tage_ctr(self, pc: int, folded_history: FoldedHistory, way: int) -> Optional[int]:
        ctr = None
        for i in range(3, -1, -1):
            idx, tag = get_idx_tag(pc, *folded_history)
            tp: TaggedPredictor = self.tn[i]
            if tp.is_hit(idx, tag, way):
                resp = tp.get(idx, way)
                is_weak = resp.ctr == 0b100 or resp.ctr == 0b011  # unconfident
                ctr = ctr if is_weak and resp.us else resp.ctr
                break
        return ctr

    def get(self, pc: int, folded_history: FoldedHistory, way: int) -> bool:
        t0 = self.t0.gets(pc)[way]
        ctr = self.get_tagged_ctr(self, folded_history, way)
        return ctr >= 0b100 if ctr is not None else t0

    def gets(self, pc: int, folded_histories: tuple[tuple[FoldedHistory, ...], ...]) -> tuple[bool, ...]:
        return tuple(self.get(pc, folded_histories[w], w) for w in range(2))
        # res = [*self.t0.gets(pc)]
        # for way in range(2):
        #     for i in range(3, -1, -1):
        #         idx, tag = get_idx_tag(pc, *folded_histories[i])
        #         p: TaggedPredictor = self.tn[i]
        #         if p.is_hit(idx, tag, way):
        #             resp = p.get(idx, way)
        #             is_weak = resp.ctr == 0b100 or resp.ctr == 0b011  # unconfident
        #             tagged_predict_taken = resp.ctr >= 0b100
        #             res[way] = res[way] if is_weak and resp.us else tagged_predict_taken
        #             break
        # return tuple(res)

    def train(self, tage_info: TageUpdateInfo, way: int) -> None:
        if tage_info.provider:
            # Tagged命中时
            t: TaggedPredictor = self.tn[tage_info.provider]
            idx, tag = get_idx_tag(tage_info.pc, *tage_info.folded_history[tage_info.provider])
            resp = t.get(idx, way)
            is_weak = resp.ctr == 0b100 or resp.ctr == 0b011
            predict_diff = tage_info.provider_taken ^ tage_info.alt_taken
            provider_mis = tage_info.provider_taken ^ tage_info.train_taken
            alt_mis = tage_info.alt_taken ^ tage_info.train_taken
            # 更新Tagged
            t.train(idx, tage_info.train_taken, way)
            if predict_diff:
                # T0和Tn不相同
                if is_weak:
                    u_idx = (tage_info.pc >> 1) & 0x7f
                    self.use_alt_on_na_ctrs[u_idx][way].update(provider_mis)
                if provider_mis:
                    # Tn错误
                    t.set_us(idx, 0, way)
                    self._alloc(idx, tag, tage_info.provider, tage_info.train_taken, way)
                else:
                    # Tn正确
                    t.set_us(idx, 1, way)
            elif provider_mis:
                # T0和Tn相同, 且都预测错误
                self._alloc(idx, tag, tage_info.provider, tage_info.train_taken, way)
                pass

        else:
            # Tagged没有命中, 基础预测器提供结果
            self.t0.train(tage_info.pc, tage_info.alt_taken, way)
            idx, tag = get_idx_tag(tage_info.pc, *tage_info.folded_history[tage_info.provider])
            self._alloc(idx, tag, tage_info.provider, tage_info.train_taken, way)
        pass

    def _alloc(self, idx: int, tag: int, provider: int, train_taken: bool, way: int) -> None:
        if provider == 4:
            mlvp.warning("[Tage._alloc]: Can't allocate for t4.")
            return

        avail, unavail = 0, 0
        tagged_responses = [t.get(idx, way) for t in self.tn]
        rand = self.lfsr.get_random() & 0xf
        rand_status = tuple((rand >> i) & 1 for i in range(4))
        allocatable_status = tuple(
            (not tagged_responses[i].valid or not self.tn[i].us) and i > (provider - 1) for i in range(4)
        )
        allocatable = False
        for x in allocatable_status:
            allocatable |= x
            if x:
                avail += 1
            else:
                unavail += 1
        # 在每次需要分配表时，进行动态重置usefulness标志位
        b: BTCtr = self.bank_tick_ctrs[way]
        b.update(avail, unavail)
        if b.reset_when_max():
            self.tn[provider].clear_us(way)
        if not allocatable:
            mlvp.error("Tage分配失败")
            return

        first_entry, masked_entry = 0, 0
        for i in range(4):
            if not allocatable_status[i]:
                continue
            first_entry = i if not first_entry else 0
            masked_entry = i if not masked_entry and rand_status[i] else 0

        allocate = masked_entry if allocatable_status[masked_entry] else first_entry
        t: TaggedPredictor = self.tn[allocate]
        t.reset_entry(idx, tag, train_taken, way)


if __name__ == '__main__':
    t = Tage(0)
    fhs = [FoldedHistory(0, 0, 0) for i in range(4)]
    info = TageUpdateInfo(0, fhs, False, 1, False, True)
    t.train(info, 0)
    t.gets(0, fhs)
