from UT_Tage_SC import DUTTage_SC
from mlvp.funcov import CovGroup

__all__ = ["get_coverage_group_of_tage_predict"]


def is_hit_table_i(way: int, t_i: int):
    def hit_table_i(dut: DUTTage_SC) -> bool:
        provided = getattr(dut, f"Tage_SC_s2_provideds_{way}").value
        provider = getattr(dut, f"Tage_SC_s2_providers_{way}").value
        return dut.io_s1_ready.value and dut.io_s2_fire_1.value and provided and provider == t_i

    return hit_table_i


def is_hit_no_table(way: int):
    def hit_no_table(dut: DUTTage_SC) -> bool:
        provided = getattr(dut, f"Tage_SC_s2_provideds_{way}").value
        return dut.io_s1_ready.value != 0 and dut.io_s2_fire_1.value != 0 and provided == 0

    return hit_no_table


def is_hit_multiple_tables(way: int):
    def hit_multiple_tables(dut: DUTTage_SC) -> bool:
        provided = getattr(dut, f"Tage_SC_s2_provideds_{way}").value
        count = 0
        for i in range(4):
            tn_hit = getattr(dut, f"Tage_SC_tables_{i}_io_resps_{way}_valid").value
            count += tn_hit != 0
        return dut.io_s1_ready.value and dut.io_s2_fire_1.value and provided and count > 1

    return hit_multiple_tables


def is_hit_table_i_weak(way: int, t_i: int, use_alt: int):
    def hit_table_i_weak(dut: DUTTage_SC) -> bool:
        provided = getattr(dut, f"Tage_SC_s2_provideds_{way}").value
        provider = getattr(dut, f"Tage_SC_s2_providers_{way}").value
        unconfident = getattr(dut, f"Tage_SC_s2_providerResps_{way}_unconf").value
        alt_used = getattr(dut, f"Tage_SC_s2_altUsed_{way}").value
        return (dut.io_s1_ready.value and dut.io_s2_fire_1.value and provided and provider == t_i
                and unconfident != 0 and alt_used == use_alt)

    return hit_table_i_weak


def is_hit_multiple_tables_weak(way: int, use_alt: int):
    def hit_multiple_tables_weak(dut: DUTTage_SC) -> bool:
        provided = getattr(dut, f"Tage_SC_s2_provideds_{way}").value
        # provider = getattr(dut, f"Tage_SC_s2_providers_{way}")
        unconfident = getattr(dut, f"Tage_SC_s2_providerResps_{way}_unconf").value
        alt_used = getattr(dut, f"Tage_SC_s2_altUsed_{way}").value
        count = 0

        for i in range(4):
            hit = getattr(dut, f"Tage_SC_tables_{i}_io_resps_{way}_valid").value
            count += hit
        return (dut.io_s1_ready.value and dut.io_s2_fire_1.value and provided and count > 0
                and unconfident and alt_used == use_alt)

    return hit_multiple_tables_weak


def get_coverage_group_of_tage_predict(dut: DUTTage_SC) -> CovGroup:
    slot_name = ["br_slot_0", "tail_slot"]

    group = CovGroup("Tage Predict")
    for w in range(2):
        # 第w个指令槽历史表ti命中
        for i in range(4):
            group.add_watch_point(dut, {f"T{i}_hit": is_hit_table_i(w, i)}, name=f"Hit {slot_name[w]} T{i}")
        # 第w个指令槽都没命中
        group.add_watch_point(dut, {"slot_miss": is_hit_no_table(w)}, name=f"Miss {slot_name[w]}")
        # 第w个指令槽多个表命中
        group.add_watch_point(
            dut, {"multi_tables_hit": is_hit_multiple_tables(w)}, name=f"Hit {slot_name[w]} multiple tables"
        )
    # 第一个和第二个指令槽都没有命中Tn
    group.add_watch_point(
        dut, {f"{slot_name[w]}_miss": is_hit_no_table(w) for w in range(2)}, name="Miss all slots"
    )
    # 第一个和第二个指令槽命中同一个Tn
    group.add_watch_point(
        dut, {
            "Hit same Tn": lambda dut:
            (is_hit_table_i(0, 0)(dut) & is_hit_table_i(1, 0)(dut)) or (
                    is_hit_table_i(0, 1)(dut) & is_hit_table_i(1, 1)(dut)) or
            (is_hit_table_i(0, 2)(dut) & is_hit_table_i(1, 2)(dut)) or (
                    is_hit_table_i(0, 3)(dut) & is_hit_table_i(1, 3)(dut))
        },
        name="All slots hit the same table"
    )
    # 命中第w个槽的ti，弱信心，选中/没有选中替代预测
    alt_use_str = ["NOT use_alt", "use_alt"]
    for use_alt in range(2):
        for w in range(2):
            for i in range(4):
                point_name = f"Hit {slot_name[w]} T{i} weak {alt_use_str[use_alt]}"
                group.add_watch_point(dut, {f"table{i} hits weak": is_hit_table_i_weak(w, i, use_alt)}, name=point_name)
    # 第w个指令槽多表命中，最长表项弱信心，选中/没有选中替代预测
    for use_alt in range(2):
        for w in range(2):
            point_name = f"Hit multiple tables {slot_name[w]} weak {alt_use_str[use_alt]}"
            group.add_watch_point(
                dut,
                {f"{slot_name[w]} {alt_use_str[use_alt]}": is_hit_multiple_tables_weak(w, use_alt)},
                name=point_name
            )
    # 两个槽命中同一个表，弱信心，选择/没有选择替代预测
    for use_alt in range(2):
        point_name = f"All slots hit the same table weak {alt_use_str[use_alt]}"
        group.add_watch_point(
            dut,
            {
                f"all_slots_hit_same_table_weak {alt_use_str[use_alt]}": lambda d:
                (is_hit_table_i_weak(0, 0, use_alt)(d) and is_hit_table_i_weak(1, 0, use_alt)(d)) or
                (is_hit_table_i_weak(0, 1, use_alt)(d) and is_hit_table_i_weak(1, 1, use_alt)(d)) or
                (is_hit_table_i_weak(0, 2, use_alt)(d) and is_hit_table_i_weak(1, 2, use_alt)(d)) or
                (is_hit_table_i_weak(0, 3, use_alt)(d) and is_hit_table_i_weak(1, 3, use_alt)(d))
            },
            name=point_name
        )

    return group
