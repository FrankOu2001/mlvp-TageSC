from typing import Optional

import mlvp

from models.tage.bank_tick_counter import BankTickCounter as BTCtr
from models.tage.bimodal import BimodalPredictor
from models.tage.tagged import TaggedPredictor, ThreeBitCounter, get_idx_and_tag
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
        self.bank_tick_ctrs = [BTCtr(), BTCtr()]
        self.lfsr = lfsr

    def get_tagged_ctr_and_bimodal_predict_with_provider_and_use_alt(
            self, pc: int, predict_fhs: list[FoldedHistory], way: int
    ) -> tuple[Optional[ThreeBitCounter], bool, int, bool]:
        provider = -1
        use_alt_idx = get_use_alt_idx(pc)
        use_alt_on_na_ctr = self.use_alt_on_na_ctrs[use_alt_idx][way]

        t0 = self.t0.predict(pc, way)
        valid, entry = False, None

        for i in range(3, -1, -1):
            valid, entry = self.tn[i].get_entry(pc, *predict_fhs[i], way)
            if valid:
                provider = i
                idx, tag = get_idx_and_tag(pc, *predict_fhs[i])
                mlvp.debug(f"Choose T{i} of way{way} as longest Tn, entry: {entry}, idx: {idx}, tag: {tag}")
                break

        use_alt = not valid or (valid and use_alt_on_na_ctr.is_use_alt and entry.ctr.is_unconf)
        mlvp.debug(f">Way{way} Tn: {entry.ctr}, T0: {t0}, use_alt_idx{way}: {use_alt_idx}, use_alt: {use_alt}, use_alt_on_na_ctr: {use_alt_on_na_ctr}")
        return entry.ctr, t0, provider, use_alt
        # ctr = self.__get_tage_entry(pc, predict_fhs, way)
        # use_alt = ctr is None or (use_alt_on_na_ctr.is_use_alt and ctr.is_unconf)
        # mlvp.debug(f">Way{way} Tn: {ctr}, T0: {t0}, use_alt: {use_alt}, use_alt_on_na_ctr: {use_alt_on_na_ctr}")
        # return None if use_alt else ctr, t0

    def train(self, pc: int, train_fhs: list[FoldedHistory], providers_valid: list[bool],
              providers: list[int], providers_ctr_value: list[int], alts_used: list[bool], base_cnts: list[int],
              trains_taken: list[bool], allocates: list[list[int]],way: int) -> None:
        """ 训练Tage预测器
        根据传入的参数训练Tage预测器, 流程如下:
        1. 当预测结果来自基础预测器T0的时候(alt_used), 更新基础预测器
        2. 如果只有基础预测器T0命中, Tn申请新的表项, 设置新tag并将us设置为0
        3. 如果Tn也命中, 更新命中得到的计数器的同时:
            1. 如果T0和Tn都命中正确: 就不再做格外的操作
            2. 如果T0和Tn都命中错误: 随机申请一个新表项
            3. 如果T0正确, Tn错误: 表项的useful置为0, 在更长历史表中申请新表项; 如果Tn的结果还为弱预测, 选用T0的替代预测器+1
            4. 如果T0错误, Tn正确: 表项的useful置为1                      ; 如果Tn的结果还为弱预测, 选用T0的替代预测器-1
        """
        provider_valid = providers_valid[way]
        provider = providers[way]
        provider_taken = providers_ctr_value[way] >= 0b100
        alt_taken = base_cnts[way] >= 0b10
        alt_used = alts_used[way]
        train_taken = trains_taken[way]
        if alt_used and (way == 0 or (way == 1 and not trains_taken[0])):
            mlvp.debug(f"T0 will update, pc: {pc:x}, train_taken: {train_taken}, alt_used: {alt_used}, way: {way}")
            self.t0.train(pc, train_taken, way)

        mlvp.debug(f'Training way{way}, pc: {pc:x}, provider_valid: {provider_valid}, provider: {provider}, ' +
                   f'provider_ctr: {providers_ctr_value[way]} ,provider_taken: {provider_taken}, ' +
                   f'alt_used: {alt_used}, alt_taken: {alt_taken}, train_taken: {train_taken}, way: {way}')
        if provider_valid:
            mlvp.debug(f'Train: T{provider} Tage predictor of way{way}, {get_idx_and_tag(pc, *train_fhs[provider])}')
            tagged = self.tn[provider]
            idx_fh, tag_fh, all_tag_fh = train_fhs[provider]
            t_valid, t_entry = tagged.get_entry(pc, idx_fh, tag_fh, all_tag_fh, way)
            mlvp.debug(f"To be trained Tagged entry: {t_entry}")
            mlvp.debug(f"DUT provider valid: {provider_valid}, provider taken: {provider_taken};" +
                       f"Ref provider valid: {t_valid}, provider taken: {t_entry.ctr.taken if t_valid else None}")
            assert provider_valid == t_valid
            assert providers_ctr_value[way] == t_entry.ctr.value
            try:
                assert providers_ctr_value[way] == t_entry.ctr.value
            except AssertionError:
                mlvp.error(f"! Provider taken({providers_ctr_value[way]}) != Ref.ctr.taken({t_entry.ctr.value})")
            provider_diff = provider_taken != alt_taken
            provider_mispred = provider_taken != train_taken

            mlvp.debug(f"altDiffer: {provider_diff}, provider_mispred: {provider_mispred}, way: {way}")
            if provider_diff:
                if t_entry.ctr.is_unconf:
                    use_idx = get_use_alt_idx(pc)
                    mlvp.debug(f"UseAltOnNaCtrs{use_idx} is updated by: {alt_taken == train_taken}")
                    self.use_alt_on_na_ctrs[use_idx][way].update(alt_taken == train_taken)

                if provider_mispred and not alt_used:
                    # Tn predict incorrectly
                    tagged.set_us(pc, idx_fh, False, way)
                    # Allocate new entry
                    self.__allocate_tage_entry(pc, train_fhs, provider_valid, provider, train_taken, allocates, way)
                else:
                    tagged.set_us(pc, idx_fh, True, way)

            elif provider_mispred:  # Both predict incorrectly
                self.__allocate_tage_entry(pc, train_fhs, provider_valid, provider, train_taken, allocates, way)

            # Train tagged
            # tagged.train(pc, idx_fh, tag_fh, all_tag_fh, way, train_taken)
            t_entry.ctr.update(train_taken)
            mlvp.debug(f"Update T{provider}, taken: {train_taken}, value: {t_entry.ctr.value}(after)")
        elif alt_taken != train_taken:
            # Allocate new entry
            mlvp.debug("While train Tage, t0 mispre")
            self.__allocate_tage_entry(pc, train_fhs, provider_valid, -1, train_taken, allocates, way)

    """
    def __get_tage_entry(self, pc: int, folded_histories: list[FoldedHistory], way: int) -> Optional[ThreeBitCounter]:
        for i in range(3, -1, -1):
            # ctr = self.tn[i].get_ctr(pc, *folded_histories[i], way)
            valid, entry = self.tn[i].get_entry(pc, *folded_histories[i], way)
            if valid:
                return entry

        return None
    """

    def __allocate_tage_entry(self, pc: int, train_fhs: list[FoldedHistory], provider_valid,
                              provider: int, train_taken: bool, allocates: list[list[int]], way: int) -> None:
        if provider == 3:
            mlvp.warning("[Tage._alloc]: Can't allocate for t4.")
            return
        avail, unavail = 0, 0
        is_allocatable = False
        can_allocate_mask = allocates[way]
        for i in range(4):
            allocatable = can_allocate_mask[i]
            is_allocatable |= allocatable
            if allocatable:
                avail += 1
            else:
                unavail += 1
        pass
        mlvp.debug(f"Can allocate mask{way}: {can_allocate_mask}, provider_valid: {provider_valid} provider{way}: {provider}")
        # 在每次需要分配表时，进行动态重置usefulness标志位
        b: BTCtr = self.bank_tick_ctrs[way]
        b.update(avail, unavail)
        if b.reset_when_max():
            self.tn[provider].clear_us(way)
            mlvp.debug("Bank Tick Ctrs reach to top.")
        # TODO: 感觉没什么用处了
        """
        if not is_allocatable:
            mlvp.error(f"Tage分配失败, can_allocate_mask: {can_allocate_mask}")
            return
        """

        mlvp.debug(f'Rand: {hex(self.lfsr.rand)}')
        rand = self.lfsr.rand & 0xf
        rand_status = [(rand >> i) & 1 for i in range(4)]
        first_entry, masked_entry = None, None
        for i in range(4):
            if (provider_valid and provider >= i) or not can_allocate_mask[i]:
                mlvp.info(f"{i} is not free")
                continue
            mlvp.info(f"{i} is free")
            if first_entry is None:
                first_entry = i
            if masked_entry is None and rand_status[i]:
                masked_entry = i
            # first_entry = i if first_entry is None else None
            # masked_entry = i if (masked_entry is None) and rand_status[i] else None
        if first_entry is None and masked_entry is None:
            mlvp.error(f"!Can't allocate. First entry: {first_entry}, Masked entry: {masked_entry}, Rand status: {rand_status},  can_allocate_mask: {can_allocate_mask}")
        if masked_entry is None:
            masked_entry = 3
        allocate = masked_entry if can_allocate_mask[masked_entry] else first_entry
        idx_fh, tag_fh, all_tag_fh = train_fhs[allocate]
        _, allocate_entry = self.tn[allocate].get_entry(pc, idx_fh, tag_fh, all_tag_fh, way)
        allocate_entry.reset(pc, tag_fh, all_tag_fh, train_taken)

        idx, tag = get_idx_and_tag(pc, idx_fh, tag_fh, all_tag_fh)
        mlvp.debug(f"*Tage Allocate New Entry: T{allocate}, idx: {idx}, tag: {tag}, taken: {train_taken}, first_entry: {first_entry}, masked_entry: {masked_entry}, rand_status: {rand_status}, way: {way}")
