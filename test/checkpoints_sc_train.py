import mlvp

from UT_Tage_SC import DUTTage_SC
from mlvp.funcov import CovGroup
from util.meta_parser import MetaParser

__all__ = ["get_coverage_group_of_sc_train"]


def get_idx(pc: int, way: int):
    return ((pc >> 1) & 1) ^ (way & 1)


def currying(v: int):
    mlvp.error(f"v: {v}")

    def f(dut: DUTTage_SC):
        return dut.io_s1_ready.value == v

    return f


def is_sc_table_saturing(way: int, ti: int, up_or_down: int):
    def sc_table_saturing(dut: DUTTage_SC):
        v = 31 if up_or_down else -32
        w_idx = get_idx(getattr(dut, f"Tage_SC_scTables_{ti}_io_update_pc").value, way)
        mask = getattr(dut, f"Tage_SC_scTables_{ti}_io_update_mask_{w_idx}").value
        old_ctr = getattr(dut, f"Tage_SC_scTables_{ti}_oldCtr" + ("_1" if way else "")).S()
        train_taken = getattr(dut, f"Tage_SC_scTables_{ti}_taken" + ("_1" if w_idx else "")).value
        new_ctr = getattr(dut, f"Tage_SC_scTables_{ti}_update_wdata_{way}").S()
        valid = dut.io_s1_ready.value != 0 and mask != 0
        if valid and old_ctr == v and up_or_down == train_taken:
            assert old_ctr == new_ctr, f"old_ctr: {old_ctr}, new_ctr: {new_ctr}, taken: {train_taken}, mask: {mask}"
            return True
        else:
            return False

    return sc_table_saturing


def is_update_sc_ctr_saturing_to_neutral(way: int, up_or_down: int):
    def update_sc_ctr_saturing_to_neutral(dut: DUTTage_SC):
        v = 63 if up_or_down else 0
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        taken = getattr(dut, f"io_update_bits_br_taken_mask_{way}").value
        cause = 1 if meta_parser.scMeta.sc_preds[way] != taken else 0
        update_valid = getattr(dut, f"Tage_SC_updateValids_{way}").value
        total_sum = getattr(dut, "Tage_SC_sum" + ("_1" if way else "")).S()
        threshold = getattr(dut, f"Tage_SC_scThresholds_{way}_thres").value
        old_ctr = getattr(dut, f"Tage_SC_scThresholds_{way}_ctr").value
        new_ctr = getattr(dut, "Tage_SC_newThres_newCtr" + ("_1" if way else "")).value
        valid = (dut.io_s1_ready.value != 0 and dut.io_update_valid.value != 0 and update_valid
                 and (threshold - 4 <= total_sum <= threshold - 2)
                 and (old_ctr + cause == v)
                 and meta_parser.scMeta.sc_preds[way] != meta_parser.scMeta.tage_takens[way])
        if valid:
            assert new_ctr == 0b10000
            return True
        return False

    return update_sc_ctr_saturing_to_neutral


def get_coverage_group_of_sc_train(dut: DUTTage_SC) -> CovGroup:
    g = CovGroup("SC Train", False)
    # 第w条指令槽的表i结果为上/下饱和，后端返回的执行结果为taken/not taken
    saturing_s = ["Down saturing", "Up saturing"]
    for w in range(2):
        for up_or_down in range(2):
            for i in range(4):
                s = " ".join([f"SC table{i} way{w}", saturing_s[up_or_down]])
                g.add_watch_point(
                    dut,
                    {"valid": is_sc_table_saturing(w, i, up_or_down)},
                    name=s
                )

    # $abs(totalSum)介于[threshold-4, threshold-2], ctr上/下饱和，最终更新的值为'b100000
    for w in range(2):
        for up_or_down in range(2):
            s = " ".join([f"SC Threshold.ctr way{w} is", saturing_s[up_or_down]])
            g.add_watch_point(
                dut,
                {"valid": is_update_sc_ctr_saturing_to_neutral(w, up_or_down)},
                name=s
            )

    return g
