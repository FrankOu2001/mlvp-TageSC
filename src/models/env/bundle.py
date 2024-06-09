from mlvp import Bundle

from parameter import *

__all__ = ["EnableCtrlBundle", "PipelineCtrlBundle", "BranchPredictionReq", "BranchPredictionResp", "UpdateBundle"]


class EnableCtrlBundle(Bundle):
    """
    @DynamicAttrs
    io_ctrl_
    """
    signals_list = ["tage_enable", "sc_enable"]


class PipelineCtrlBundle(Bundle):
    """
    @DynamicAttrs
    io_s{x}_fire
    """
    signals_list = [
        # ctrl of s{i} stage, 0->BPU, 1->Tage, 3->SC
        *[f"s{i}_fire_{j}" for i in range(4) for j in range(4)],
    ]


class FoldedHistoryBundle(Bundle):
    signals_list = [f"hist_{i}_folded_hist" for i in range(18)]


class FTBSlotBundle(Bundle):
    signals_list = ["offset", "lower", "tarStat", "sharing", "valid"]


class FTBEntryBundle(Bundle):
    signals_list = [
        "valid", "pftAddr", "carry",
        "isCall", "isRet", "isJalr", "last_may_be_rvi_call",
        *[f"always_taken_{i}" for i in range(NUM_BR)]
    ]
    sub_bundles = [
        ("brSlots_0", lambda dut: FTBSlotBundle.from_prefix(dut, "brSlots_0_")),
        ("tailSlot", lambda dut: FTBSlotBundle.from_prefix(dut, "tailSlot_"))
    ]


class FullBranchPredictionBundle(Bundle):
    signals_list = [
        "hit",
        *[f"{type}_{i}" for i in range(NUM_BR) for type in ["slot_valids", "targets", "offsets", "br_taken_mask"]],
        "fallThroughAddr", "fallThroughErr",
        "is_jal", "is_jalr", "is_call", "is_ret", "is_br_sharing",
        "last_may_be_rvi_call",
        "jalr_target"
    ]


class BranchPredictionBundle(Bundle):
    signals_list = ["pc", "valid", "hasRedirect", "ftq_idx"]
    sub_bundles = [
        (f"full_pred", lambda dut: FullBranchPredictionBundle.from_regex(dut, r"full_pred_\d_(.*)"))
    ]


class BranchPredictionReq(Bundle):
    """
    @DynamicAttrs
    io_in_
    """
    signals_list = [f"bits_s0_pc_{i}" for i in range(4)]
    sub_bundles = [
        # TageTables' folded histories
        ("fh_tage", lambda dut: FoldedHistoryBundle.from_prefix(dut, "bits_folded_hist_1_")),
        # SCTables' folded histories
        ("fh_sc", lambda dut: FoldedHistoryBundle.from_prefix(dut, "bits_folded_hist_3_"))
    ]


class BranchPredictionResp(Bundle):
    """
    @DynamicAttrs
    io_out_
    """
    signals_list = ["last_stage_meta"]
    sub_bundles = [
        (f"s{i}", lambda dut: BranchPredictionBundle.from_prefix(dut, f"s{i}_")) for i in range(2, 4)
    ]


class BranchPredictionUpdate(Bundle):
    signals_list = [
        "pc", "meta", "old_entry",
        *[f"br_taken_mask_{i}" for i in range(NUM_BR)],
        *[f"mispred_mask_{i}" for i in range(NUM_BR + 1)],
        "jmp_taken", "full_target",
        "cfi_idx"
    ]
    sub_bundles = [
        ("ftb_entry", lambda dut: FTBEntryBundle.from_prefix(dut, "ftb_entry_")),
        ("folded_hist", lambda dut: FoldedHistoryBundle.from_prefix(dut, "spec_info_folded_hist_"))
    ]


class UpdateBundle(Bundle):
    """
    @DynamicAttrs
    io_update_
    """
    signals_list = ["valid"]
    sub_bundles = [("bits", lambda dut: BranchPredictionUpdate.from_prefix(dut, "bits_"))]
