from mlvp import Bundle

from parameter import *

__all__ = ["EnableCtrlBundle", "PipelineCtrlBundle", "BranchPredictionReq", "BranchPredictionResp", "UpdateBundle"]


class EnableCtrlBundle(Bundle):
    """
    @DynamicAttrs
    io_ctrl_
    """
    signals = ["tage_enable", "sc_enable"]


class PipelineCtrlBundle(Bundle):
    """
    @DynamicAttrs
    io_s{x}_fire
    """
    signals = [
        # ctrl of s{i} stage, 0->BPU, 1->Tage, 3->SC
        *[f"s{i}_fire_{j}" for i in range(3) for j in range(4)],
    ]


class FoldedHistoryBundle(Bundle):
    signals = [f"hist_{i}_folded_hist" for i in range(18)]


class FTBSlotBundle(Bundle):
    signals = ["valid", "sharing"]


class FTBEntryBundle(Bundle):
    signals = [
        *[f"always_taken_{i}" for i in range(NUM_BR)]
    ]

    def __init__(self):
        super().__init__()
        self.brSlots_0 = FTBSlotBundle.from_prefix("brSlots_0_")
        self.tailSlot = FTBSlotBundle.from_prefix("tailSlot_")


class FullBranchPredictionBundle(Bundle):
    signals = [
        # "hit",
        *[f"{type}_{i}" for i in range(NUM_BR) for type in
          # ["slot_valids", "targets", "offsets", "br_taken_mask"]],
          ["br_taken_mask"]],
        # "fallThroughAddr", "fallThroughErr",
        # "is_jal", "is_jalr", "is_call", "is_ret", "is_br_sharing",
        # "last_may_be_rvi_call",
        # "jalr_target"
    ]


class BranchPredictionBundle(Bundle):
    # signals = ["pc", "valid", "hasRedirect", "ftq_idx"]
    signals = []

    def __init__(self):
        super().__init__()
        self.full_pred = FullBranchPredictionBundle.from_regex(r"full_pred_\d_(.*)")


class BranchPredictionReq(Bundle):
    """
    @DynamicAttrs
    io_in_
    """
    signals = [f"bits_s0_pc_{i}" for i in [0, 1, 3]]

    def __init__(self):
        super().__init__()
        self.fh_tage = FoldedHistoryBundle.from_prefix("bits_folded_hist_1_")
        self.fh_sc = FoldedHistoryBundle.from_prefix("bits_folded_hist_3_")


class BranchPredictionResp(Bundle):
    """
    @DynamicAttrs
    io_out_
    """
    signals = ["last_stage_meta"]

    def __init__(self):
        super().__init__()
        self.s2 = BranchPredictionBundle.from_prefix("s2_")
        self.s3 = BranchPredictionBundle.from_prefix("s3_")


class BranchPredictionUpdate(Bundle):
    signals = [
        "pc", "meta",
        *[f"br_taken_mask_{i}" for i in range(NUM_BR)],
        *[f"mispred_mask_{i}" for i in range(NUM_BR)]
    ]

    def __init__(self):
        super().__init__()
        self.ftb_entry = FTBEntryBundle.from_prefix("ftb_entry_")
        self.folded_hist = FoldedHistoryBundle.from_prefix("spec_info_folded_hist_")


class UpdateBundle(Bundle):
    """
    @DynamicAttrs
    io_update_
    """
    signals = ["valid"]

    def __init__(self):
        super().__init__()
        self.bits = BranchPredictionUpdate.from_prefix("bits_")
