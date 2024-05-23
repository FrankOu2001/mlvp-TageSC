from mlvp import Bundle


def __folded_hist_range__():
    for i in [1, 2, 3, 4, 5, 7, 8, 9, 11, 12, 14, 15, 16, 17]:
        yield i


class PredictorCtrlBundle(Bundle):
    signals_list = ["tage_enable", "sc_enable"]


class PipelineCtrlBundle(Bundle):
    """@DynamicAttrs"""
    signals_list = [
        # ctrl of s{i} stage, 0->BPU, 1->Tage, 3->SC
        *(f"s{i}_fire_{j}" for i in range(3) for j in range(4)),
        # FIXME: tage的所有表，可以执行读取结果的操作
        "s1_ready"
    ]


class BranchPredictionUpdateBundle(Bundle):
    # TODO: io_update_bits相关的信号都是从BranchPredictionUpdate来的
    # 感觉没啥用，不是所有接口都用上了
    pass


class InBundle(Bundle):
    """@DynamicAttrs"""
    """
    来自BPU的输入，即预测时提供的数据
    """
    signals_list = [
        # dup of s0_pc
        *(f"bits_s0_pc_{i}" for i in range(4)),
        # TageTables' folded histories
        *(f"bits_folded_hist_1_hist_{i}_folded_hist" for i in __folded_hist_range__()),
        # SCTables' folded histories
        *(f"bits_folded_hist_3_hist_{i}_folded_hist" for i in [2, 11, 12])
    ]


class OutBundle(Bundle):
    """@DynamicAttrs"""
    signals_list = [
        # Output of predicted result for the {j}th instruction from Tage in s2 stage,
        # {i} means {i}th duplicated result.
        *(f"s2_full_pred_{i}_br_taken_mask_{j}" for i in range(4) for j in range(2)),
        # Output of predicted result for the {j}th instruction from Tage in s3 stage,
        # {i} means {i}th duplicated result.
        *(f"s3_full_pred_{i}_br_taken_mask_{j}" for i in range(4) for j in range(2)),
        "last_stage_meta"  # haha
    ]


class FoldedHistoryBundle(Bundle):
    """@DynamicAttrs"""
    """
    对折叠历史的封装
    """
    signals_list = [
        *[f"{i}_folded_hist" for i in range(1, 18)],
    ]


class UpdateBundle(Bundle):
    """@DynamicAttrs"""
    """
    来自FTQ，即更新时的数据
    """
    signals_list = [
        # FTQ -> BPU is valid or not
        "valid",
        # prediction block's PC from backend
        "bits_pc",
        # fd history
        # *[f"bits_spec_info_folded_hist_hist_{i}_folded_hist" for i in range(1, 18)],
        "bits_ftb_entry_brSlots_0_valid",
        "bits_ftb_entry_tailSlot_sharing",
        "bits_ftb_entry_tailSlot_valid",
        "bits_ftb_entry_always_taken_0",
        "bits_ftb_entry_always_taken_1",
        "bits_br_taken_mask_0",
        "bits_br_taken_mask_1",
        "bits_mispred_mask_0",
        "bits_mispred_mask_1",
        "bits_meta"  # haha
    ]
    sub_bundles = [
        ("bits_folded_hist", lambda dut: FoldedHistoryBundle.from_prefix(dut, "bits_spec_info_folded_hist_hist_"))
    ]
