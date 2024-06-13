from models.sc import SC
from models.tage import Tage
from util.lfsr import LFSR_64
from collections import namedtuple
from util.meta_parser import MetaParser
from models.env.global_history import GlobalHistory
from models.folded_history import FoldedHistory



def get_tage_folded_history(ghv: GlobalHistory) -> list[FoldedHistory]:
    return [
        FoldedHistory(*[ghv.get_fh(folded_len, 8) for folded_len in (8, 8, 7)]),
        FoldedHistory(*[ghv.get_fh(folded_len, 13) for folded_len in (11, 8, 7)]),
        FoldedHistory(*[ghv.get_fh(folded_len, 32) for folded_len in (11, 8, 7)]),
        FoldedHistory(*[ghv.get_fh(folded_len, 119) for folded_len in (11, 8, 7)]),
    ]


def get_sc_folded_history(ghv: GlobalHistory) -> list[int]:
    return [
        ghv.get_fh(0, 0),
        ghv.get_fh(4, 4),
        ghv.get_fh(8, 10),
        ghv.get_fh(8, 16),
    ]


class RefTageSC:
    def __init__(self, predict_ghv, train_ghv):
        self.lfsr = LFSR_64(0x1234567887654321)
        self.tage = Tage(self.lfsr)
        self.sc = SC()
        self.predict_ghv = predict_ghv
        self.train_ghv = train_ghv

    def predict(self, pc: int, way: int) -> bool:
        tage_ctr, t0 = self.tage.get_tagged_ctr_and_bimodal_predict(pc, get_tage_folded_history(self.predict_ghv), way)
        if tage_ctr is not None:
            sc_ctr_sum = self.sc.get_sc_ctr_sum(pc, get_sc_folded_history(self.predict_ghv), tage_ctr.taken, way)
            tage_ctr_centered = (2 * (tage_ctr.value - 4) + 1) << 3
            total_sum = sc_ctr_sum + tage_ctr_centered
            return (total_sum >= 0) if abs(total_sum) > self.sc.get_threshold(way) else tage_ctr.taken
        else:
            return t0

    def train(self, pc: int, train_meta: int, train_taken: bool, way: int):
        parser = MetaParser(train_meta)
        """
        Require values: old_total_sum(sc_meta_ctr, providerResps_ctr), provider, tage_predict, sc_predict, alt_taken, taken, 
        """
        self.tage.train(
            pc, get_tage_folded_history(self.train_ghv), parser.providers_valid[way], parser.providers[way],
            parser.providerResps_ctr[way] >= 0b100, parser.basecnts[way], train_taken, way
        )
        if parser.providers_valid[way]:
            old_total_sum = 0
            for x in parser.scMeta.sc_ctrs[way]:
                old_total_sum += (x << 1) + 1
