import mlvp
from models.sc import SC
from models.tage import Tage
from util.lfsr import LFSR_64
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
    def __init__(self, predict_ghv, train_ghv, lfsr: LFSR_64, sc_enable: bool = False):
        self.sc_enable = sc_enable
        self.tage = Tage(lfsr)
        self.sc = SC()
        self.predict_ghv = predict_ghv
        self.train_ghv = train_ghv

    def predict(self, pc: int, way: int, test_number: -1) -> tuple[bool, int, bool]:
        """ Return predict result and whether t0 is used
        """
        tage_fh = get_tage_folded_history(self.predict_ghv)
        mlvp.warning(f"Tage predict folededHistory: {tage_fh}")
        tage_ctr, t0, provider, use_alt = self.tage.get_tagged_ctr_and_bimodal_predict_with_provider_and_use_alt(pc, tage_fh, way)
        if not use_alt:
            sc_ctr_sum = self.sc.get_sc_ctr_sum(pc, get_sc_folded_history(self.predict_ghv), tage_ctr.taken, way)
            tage_ctr_centered = (2 * (tage_ctr.value - 4) + 1) << 3
            total_sum = sc_ctr_sum + tage_ctr_centered
            use_sc = self.sc_enable and abs(total_sum) > self.sc.get_threshold(way)
            mlvp.debug(f"-Way{way} total_sum: {total_sum}, use_sc: {use_sc}")
            return (total_sum >= 0) if use_sc else tage_ctr.taken, provider, False
            # return tage_ctr.taken, False
        else:
            mlvp.debug(f"Predict result from TO is {t0}")
            return t0, provider, True

    def train(self, pc: int, train_valid: bool, train_meta: int, trains_taken: list[bool], way: int):
        """ Train predictor.

        :param pc:
        :param train_valid:
        :param train_meta:
        :param train_taken:
        :param way:
        :return:
        """
        if not train_valid:
            return

        mlvp.debug(f"Train FoldHistory: {get_tage_folded_history(self.train_ghv)}")
        parser = MetaParser(train_meta)
        self.tage.train(
            pc, get_tage_folded_history(self.train_ghv), parser.providers_valid, parser.providers,
            parser.providerResps_ctr, parser.altUsed, parser.basecnts, trains_taken, parser.allocates, way
        )
        # assert parser.providers_valid[way] == parser.scMeta.sc_used[way]
        if parser.providers_valid[way]:
            old_total_sum = ((parser.providerResps_ctr[way] - 4) * 2 + 1) << 3  # tageCtrCentered
            for x in parser.scMeta.sc_ctrs[way]:
                old_total_sum += (x << 1) + 1

            mlvp.debug(f"-Way{way} old_total_sum: {old_total_sum}")
