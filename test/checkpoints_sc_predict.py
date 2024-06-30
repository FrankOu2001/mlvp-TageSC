import mlvp

from UT_Tage_SC import DUTTage_SC
from mlvp.funcov import CovGroup
from util.meta_parser import MetaParser

__all__ = ["get_coverage_group_of_sc_predict"]


def currying(v: int):
    mlvp.error(f"v: {v}")

    def f(dut: DUTTage_SC):
        return dut.io_s1_ready.value == v

    return f


def is_total_sum_correct(way: int):
    def total_sum_correct(dut: DUTTage_SC) -> bool:
        valid = dut.io_s1_ready.value != 0 and dut.io_s2_fire_3.value != 0
        sc_w = "1_" if way else ""
        sc_table_sum_0 = getattr(dut, f"Tage_SC_s2_scTableSums_{sc_w}0").S()
        sc_table_sum_1 = getattr(dut, f"Tage_SC_s2_scTableSums_{sc_w}1").S()
        total_w = "_1" if way else ""
        # total_sum's width is 10bit
        total_sum_0 = getattr(dut, f"Tage_SC_s2_totalSums_0{total_w}").S()
        total_sum_1 = getattr(dut, f"Tage_SC_s2_totalSums_1{total_w}").S()
        tage = getattr(dut, f"Tage_SC_s2_providerResps_{way}_ctr").value
        centered = ((tage - 4) * 2 + 1) * 8

        if valid:
            assert ((total_sum_0 == sc_table_sum_0 + centered) and (total_sum_1 == sc_table_sum_1 + centered)), \
                "SC total_sum error."

        return valid and ((total_sum_0 == sc_table_sum_0 + centered) and (total_sum_1 == sc_table_sum_1 + centered))

    return total_sum_correct


def is_tage_take_from_t0(way: int, tn_hit: int):
    def tage_taken_from_t0(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_out_last_stage_meta.value)
        valid = dut.io_s1_ready.value != 0
        tage_taken_from_t0 = meta_parser.altUsed[way] != 0
        provided = meta_parser.providers_valid[way] != 0
        sc_used = meta_parser.scMeta.sc_used[way] != 0

        return valid and tage_taken_from_t0 and not sc_used and (tn_hit == provided)

    return tage_taken_from_t0


def is_tage_taken_from_tn(way: int, use_sc: int):
    def tage_taken_from_tn(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_out_last_stage_meta.value)
        provided = meta_parser.providers_valid[way] != 0
        tage_taken_from_tn = meta_parser.altUsed[way] == 0
        sc_used = meta_parser.scMeta.sc_used[way] != 0
        valid = dut.io_s1_ready.value != 0 and provided and tage_taken_from_tn and (sc_used == use_sc)
        return valid

    return tage_taken_from_tn


def get_coverage_group_of_sc_predict(dut: DUTTage_SC) -> CovGroup:
    g = CovGroup("SC Predict", False)
    """SC Predict function coverage begin"""
    # 判断第w条指令槽的totalSum的计算结果是否正确，因为其中涉及到无符号数转有符号数
    for w in range(2):
        s = f"TotalSum of way{w} is correct"
        g.add_watch_point(dut, {"correct": is_total_sum_correct(w)}, name=s)

    # 判断第w条指令槽的TAGE预测结果来自T0，Tn命中/未命中，SC没有改变预测的结果
    hit_s = ["not hit", "hit"]
    for w in range(2):
        for hit in range(2):
            s = "".join(["Use TO and sc is not used, Tn is ", hit_s[hit], " of way", str(w)])
            g.add_watch_point(dut, {"sc used": is_tage_take_from_t0(w, hit)}, name=s)

    # 判断第w条指令槽的TAGE结果来自Tn，SC改变/不改变预测的结果
    sc_use_s = ["use sc", "does NOT use sc"]
    for w in range(2):
        for use_sc in range(2):
            s = "".join(["Tn is hit and ", sc_use_s[use_sc], " of way", str(w)])
            g.add_watch_point(dut, {sc_use_s[w]: is_tage_taken_from_tn(w, use_sc)}, name=s)

    return g
