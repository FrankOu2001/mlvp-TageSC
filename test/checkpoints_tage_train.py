from UT_Tage_SC import DUTTage_SC
from mlvp.funcov import CovGroup
from util.meta_parser import MetaParser

__all__ = ["get_coverage_group_of_tage_train"]

slot_name = ["br_slot_0", "tail_slot"]


def get_idx(pc: int, way: int):
    return ((pc >> 1) & 1) ^ (way & 1)


def is_update_saturing_base_ctr(way: int, up_or_down: int):
    def base_ctr_saturing(dut: DUTTage_SC) -> bool:
        v = 0b11 if up_or_down else 0
        w_idx = get_idx(dut.io_update_bits_pc.value, way)
        valid = dut.io_s1_ready.value and dut.Tage_SC_bt_bt_io_w_req_valid.value \
                and ((dut.Tage_SC_bt_bt_io_w_req_bits_waymask.value >> w_idx) & 1)
        old_ctr = getattr(dut, f"Tage_SC_bt_oldCtrs_{way}").value
        new_ctr = getattr(dut, f"Tage_SC_bt_newCtrs_{way}").value
        taken = getattr(dut, f"Tage_SC_bt_io_update_takens_{w_idx}").value
        return valid and (new_ctr == old_ctr) and old_ctr == v and (taken == up_or_down)

    return base_ctr_saturing


def is_update_saturing_tagged_ctr(way: int, t_i: int, up_or_down: int):
    def tagged_ctr_saturing(dut: DUTTage_SC) -> bool:
        v = 0b111 if up_or_down else 0
        for b in range(4):
            bank_update_way_mask = getattr(dut, f"Tage_SC_tables_{t_i}_per_bank_update_way_mask_{b}").value
            bank_valid = getattr(dut, f"Tage_SC_tables_{t_i}_table_banks_{b}_io_w_req_valid").value
            for w in range(2):
                w_idx = get_idx(dut.io_update_bits_pc.value, way)
                way_valid = (bank_update_way_mask >> way) & 1
                valid = dut.io_s1_ready.value and bank_valid and way_valid
                bypass_idx = b * 2 + w
                bypass_suffix = "" if bypass_idx == 0 else f"_{bypass_idx}"
                bypass_data_valid = getattr(dut, f"Tage_SC_tables_{t_i}_wrbypass_data_valid" + bypass_suffix).value
                bypass_data = getattr(dut, f"Tage_SC_tables_{t_i}_per_bank_update_wdata_{b}_{w}_ctr").value
                old_ctr = getattr(dut, f"Tage_SC_tables_{t_i}_io_update_oldCtrs_{w_idx}").value
                real_old_ctr = bypass_data if bypass_data_valid else old_ctr
                new_ctr = getattr(dut, f"Tage_SC_tables_{t_i}_per_bank_update_wdata_{b}_{w}_ctr").value
                taken = getattr(dut, f"Tage_SC_tables_{t_i}_io_update_takens_{w_idx}").value
                if valid and (new_ctr == real_old_ctr) and (real_old_ctr == v) and (taken == up_or_down):
                    return True
        return False

    return tagged_ctr_saturing


def is_allocate_new_entry(way: int, except_success_or_failure: int):
    """
    #FIXME: 目前的判断逻辑还是按照Chisel代码进行的, 所以可用表项信息失效的bug依旧存在.
    """
    need_to_allocates = ["Tage_SC_needToAllocate", "Tage_SC_needToAllocate_1"]

    def allocate_new_entry(dut: DUTTage_SC) -> bool:
        valid = getattr(dut, f"Tage_SC_updateValids_{way}").value and dut.io_update_valid.value
        need_to_allocate = getattr(dut, need_to_allocates[way]).value
        allocatable_count = 0
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        for x in meta_parser.allocates[way]:
            allocatable_count += x

        return dut.io_s1_ready.value and valid and need_to_allocate \
            and ((allocatable_count > 0) if except_success_or_failure else (allocatable_count == 0))

    return allocate_new_entry


def is_allocate_as_provider_incorrectly_predict(way: int):
    def allocate_as_provider(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        incorrect = getattr(dut, "Tage_SC_updateProviderCorrect" + ("_1" if way else "")).value == 0
        valid = dut.io_s1_ready.value and dut.io_update_valid.value and meta_parser.providers_valid[way] and incorrect
        return valid

    return allocate_as_provider


def is_update_predict_from_tagged(way: int):
    def update_predict_from_tagged(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        valid = getattr(dut, f"Tage_SC_updateValids_{way}").value and dut.io_update_valid.value
        provided = meta_parser.providers_valid[way]
        alt_used = meta_parser.altUsed[way]
        return valid and provided and not alt_used

    return update_predict_from_tagged


def is_update_use_alt_on_na_ctrs(way: int):
    def update_use_alt_on_na_ctrs(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        valid = getattr(dut, f"Tage_SC_updateValids_{way}").value
        provided = meta_parser.providers_valid[way]
        weak = meta_parser.providerResps_unconf[way]
        alt_diff = meta_parser.altDiffers[way]
        assert (meta_parser.providerResps_ctr[way] in {0b100, 0b011}) == meta_parser.providerResps_unconf[way]
        return dut.io_s1_ready.value and valid and provided and weak and alt_diff

    return update_use_alt_on_na_ctrs


def is_update_from_tagged_weak(way: int, t_correct: int, use_alt: int, alt_correct: int):
    def update_from_tagged(dut: DUTTage_SC) -> bool:
        meta_parser = MetaParser(dut.io_update_bits_meta.value)
        unconf = meta_parser.providerResps_unconf[way]
        provider_valid = meta_parser.providers_valid[way]
        # provider = meta_parser.providerResps_ctr[way]
        alt_used = meta_parser.altUsed[way]
        provider_correct = getattr(dut, "Tage_SC_updateProviderCorrect" + ("_1" if way else "")).value
        valid = (dut.io_s1_ready.value and dut.io_update_valid.value and unconf and provider_valid
                 and (alt_used == use_alt) and (provider_correct == t_correct))
        train_taken = getattr(dut, f"io_update_bits_br_taken_mask_{way}").value
        alt_pred = meta_parser.basecnts[way] >= 0b10
        return valid and ((alt_pred == train_taken) if alt_correct else (alt_pred != train_taken))

    return update_from_tagged


def get_coverage_group_of_tage_train(dut: DUTTage_SC) -> CovGroup:
    g = CovGroup("Tage Train")
    """Tage Train function coverage begin"""
    # 第w条指令槽的T0上/下饱和
    for up_or_down in range(2):
        s = "up saturing" if up_or_down else "down saturing"
        for w in range(2):
            g.add_watch_point(dut, {"": is_update_saturing_base_ctr(w, up_or_down)}, name=f"Update T0-{w} " + s)
    # 第w条指令槽的Ti上/下饱和
    for up_or_down in range(2):
        for w in range(2):
            for i in range(4):
                s = "up saturing" if up_or_down else "down saturing"
                g.add_watch_point(
                    dut,
                    {"": is_update_saturing_tagged_ctr(w, i, up_or_down)},
                    name=f"Update T{i + 1}-{w} " + s
                )
    for expect_success_or_failure in range(2):
        for w in range(2):
            bin_str = f"allocate {slot_name[w]}" + ("success" if expect_success_or_failure else "failure")
            name_str = f"Allocate new entry for {slot_name[w]} " + \
                       ("success" if expect_success_or_failure else "failure")
            # 第w条指令槽申请新表项成功/失败
            g.add_watch_point(dut, {bin_str: is_allocate_new_entry(w, expect_success_or_failure)}, name=name_str)
            # 第w条指令槽申请新表项成功/失败, 较短历史预测错误
            g.add_watch_point(
                dut,
                {
                    bin_str: is_allocate_new_entry(w, expect_success_or_failure),
                    "provider incorrect": is_allocate_as_provider_incorrectly_predict(w)
                },
                name=name_str + " for provider incorrect"
            )
    # 第w条指令槽触发重置useful位
    for w in range(2):
        g.add_watch_point(
            dut,
            {
                "initialize ready": lambda d: d.io_s1_ready.value == 1,
                f"reset u of {slot_name[w]}": lambda d: getattr(d, f"Tage_SC_updateResetU_{w}").value
            },
            name=f"Reset useful bit of {slot_name[w]}"
        )

    # TODO: always_taken
    # TODO: 更新-预测冲突发生

    # 第w条指令槽对应的Ti命中且弱信息，使用/不适用替代预测，Ti正确/错误，替代预测正确/错误
    for w in range(2):
        for use_alt in range(2):
            for provider_correct in range(2):
                for alt_correct in range(2):
                    s = " ".join([
                        f"Hit Tn-{w} weak", ("provider_correct" if provider_correct else ""),
                        ("use_alt" if use_alt else ""), ("alt_correct" if alt_correct else ""),
                    ])
                    g.add_watch_point(
                        dut,
                        {s.lower(): is_update_from_tagged_weak(w, provider_correct, use_alt, alt_correct)},
                        name=s
                    )

    # 第w条指令槽对应的useAltOnNa寄存器组正常计数增减
    for w in range(2):
        g.add_watch_point(
            dut,
            {f"use_alt_on_na_way{w}_change": is_update_use_alt_on_na_ctrs(w)},
            name=f"useAltOnNa counters of way{w} changed"
        )
    """Tage Train function coverage end"""

    return g
