import mlvp

from models.env.bundle import *
from models.env.global_history import GlobalHistory
from models.env.fake_ftq import FakeFTBEntry
from mlvp import Bundle, setup_logging
from mlvp import ClockCycles, Condition, Value
from mlvp.logger import DEBUG
from UT_Tage_SC import DUTTage_SC

__all__ = ["TageSCPins", "UpdateRecord"]

setup_logging(DEBUG)


class UpdateRecord:
    def __init__(
            self, pc: int, br_slot_valid: bool, tail_slot_valid: bool, tail_slot_sharing: bool, meta: int, ghv: int,
            br_taken_mask: tuple[int, int], mispred_mask: tuple[int, int], always_taken_0: int, always_taken_1: int
    ):
        self.pc = pc
        self.br_slot_valid = br_slot_valid
        self.tail_slot_valid = tail_slot_valid
        self.tail_slot_sharing = tail_slot_sharing
        self.meta = meta
        self.br_taken_mask = br_taken_mask
        self.mispred_mask = mispred_mask
        self.ghv = GlobalHistory(ghv)
        self.always_taken_0 = always_taken_0
        self.always_taken_1 = always_taken_1

    def as_dict(self):
        return {
            'pc': self.pc,
            'meta': self.meta,
            'br_taken_mask_0': self.br_taken_mask[0],
            'br_taken_mask_1': self.br_taken_mask[1],
            'mispred_mask_0': self.mispred_mask[0],
            'mispred_mask_1': self.mispred_mask[1],
            'ftb_entry': {
                'always_taken_0': self.always_taken_0,
                'always_taken_1': self.always_taken_1,
                'brSlots_0': {'valid': self.br_slot_valid},
                'tailSlot': {'valid': self.tail_slot_valid, 'sharing': self.tail_slot_sharing},
            },
            'folded_hist': {
                "hist_17_folded_hist": self.ghv.get_fh(11, 32),
                "hist_16_folded_hist": self.ghv.get_fh(11, 119),
                "hist_15_folded_hist": self.ghv.get_fh(7, 13),
                "hist_14_folded_hist": self.ghv.get_fh(8, 8),
                "hist_12_folded_hist": self.ghv.get_fh(4, 4),  # for sc1
                "hist_11_folded_hist": self.ghv.get_fh(8, 10),  # for sc2
                "hist_9_folded_hist": self.ghv.get_fh(7, 32),
                "hist_8_folded_hist": self.ghv.get_fh(8, 119),
                "hist_7_folded_hist": self.ghv.get_fh(7, 8),
                "hist_5_folded_hist": self.ghv.get_fh(7, 119),
                "hist_4_folded_hist": self.ghv.get_fh(8, 16),
                "hist_3_folded_hist": self.ghv.get_fh(8, 32),
                "hist_2_folded_hist": self.ghv.get_fh(8, 16),  # for sc3
                "hist_1_folded_hist": self.ghv.get_fh(11, 16),
            }
        }


class TageSCPins(Bundle):
    def __init__(self, dut: DUTTage_SC):
        super().__init__()
        self.dut = dut
        # control
        self.dut_in = BranchPredictionReq.from_prefix("io_in_")
        self.dut_out = BranchPredictionResp.from_prefix("io_out_")
        self.dut_update = UpdateBundle.from_prefix("io_update_")
        self.enable_ctrl = EnableCtrlBundle.from_prefix("io_ctrl_")
        self.pipeline_ctrl = PipelineCtrlBundle.from_prefix("io_")

        self.bind(dut)
        self.enable_ctrl.set_all(0)
        self.pipeline_ctrl.set_all(0)
        self.dut_in.set_all(0)
        self.dut_update.set_all(0)

    async def initialize(self):
        self.dut.reset.value = 1
        self.dut.Step(10)
        self.dut.reset.value = 0
        await Value(self.dut.io_s1_ready, 1)

    def set_tage_enable(self, enable: bool = True) -> None:
        self.enable_ctrl.tage_enable.value = enable

    def set_sc_enable(self, enable: bool = True) -> None:
        self.enable_ctrl.sc_enable.value = enable

    async def cmd_predict(self, pc: int, ghv: int) -> dict:
        fire_s = [0] * 4
        fire_s[0] = 1
        g = GlobalHistory(ghv)
        self.dut_in.assign({
            'bits_s0_pc_0': pc,
            'bits_s0_pc_1': pc,
            'bits_s0_pc_3': pc,
            'fh_tage': {
                'hist_17_folded_hist': g.get_fh(11, 32),
                'hist_16_folded_hist': g.get_fh(11, 119),
                'hist_15_folded_hist': g.get_fh(7, 13),
                'hist_14_folded_hist': g.get_fh(8, 8),
                'hist_9_folded_hist': g.get_fh(7, 32),
                'hist_8_folded_hist': g.get_fh(8, 119),
                'hist_7_folded_hist': g.get_fh(7, 8),
                'hist_5_folded_hist': g.get_fh(7, 119),
                'hist_4_folded_hist': g.get_fh(8, 13),
                'hist_3_folded_hist': g.get_fh(8, 32),
                'hist_1_folded_hist': g.get_fh(11, 13)
            },
            'fh_sc': {
                'hist_12_folded_hist': g.get_fh(4, 4),
                'hist_11_folded_hist': g.get_fh(8, 10),
                'hist_2_folded_hist': g.get_fh(8, 16)
            }
        })
        for _ in range(4):
            # Update fire signal
            for i in range(3):
                for j in range(4):
                    attr = getattr(self.pipeline_ctrl, f"s{i}_fire_{j}")
                    attr.value = fire_s[i]
            # self.dut.Step(1)
            await ClockCycles(self.dut, 1)
            for i in range(3, 0, -1):
                fire_s[i] = fire_s[i - 1]
            fire_s[0] = 0

        self.dut_in.set_all(0)
        self.pipeline_ctrl.set_all(0)
        return self.dut_out.as_dict()

    async def cmd_train(self, update_record: UpdateRecord) -> None:
        self.dut_update.assign({'valid': 1, 'bits': update_record.as_dict()})
        await ClockCycles(self.dut, 1)
        self.dut_update.set_all(0)
        await ClockCycles(self.dut, 4)
