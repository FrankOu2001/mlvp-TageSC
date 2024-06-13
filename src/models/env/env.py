import mlvp
from mlvp import *

from UT_Tage_SC import DUTTage_SC as TageSC
from models.env.bundle import *
from models.env.fake_ifu import FakeIFU
from models.env.global_history import GlobalHistory
from models.env.fake_ftq import FakeFTQ
from models.ref_tagesc import RefTageSC
from util.meta_parser import MetaParser
from parameter import *
from UT_Tage_SC.xspcomm import *

__all__ = ['Env']


class Env:
    def __init__(self, dut: TageSC):
        self.dut = dut
        self.dut_in = BranchPredictionReq.from_prefix(dut, "io_in_")
        self.dut_out = BranchPredictionResp.from_prefix(dut, "io_out_")
        self.dut_update = UpdateBundle.from_prefix(dut, "io_update_")
        self.enable_ctrl = EnableCtrlBundle.from_prefix(dut, "io_ctrl_")
        self.pipeline_ctrl = PipelineCtrlBundle.from_prefix(dut, "io_")

        # Global History
        self.predict_ghv = GlobalHistory()
        self.train_ghv = GlobalHistory()
        self.ifu = FakeIFU(FILE_PATH, RESET_VECTOR)
        self.ftq = FakeFTQ(delay=False)

        self.fire_s = [0] * 4
        self.pc_s = [0] * 4

        # Reference Model
        self.ref = RefTageSC(self.predict_ghv, self.train_ghv)
        # Random Step
        self.dut.StepRis(lambda _: self.ref.lfsr.step())
        # Set Imme
        for i in [dut.io_ctrl_sc_enable, dut.io_reset_vector, dut.reset]:
            i.SetWriteMode(XData.Imme)
        for i in range(4):
            for j in range(4):
                attr = getattr(self.pipeline_ctrl, f"s{i}_fire_{j}")
                if isinstance(attr, XData):
                    attr = 0

    async def run(self):
        self.enable_ctrl.tage_enable.value = 1
        self.enable_ctrl.sc_enable.value = 0
        self.pc_s[0] = RESET_VECTOR
        self.dut.reset.value = 1
        self.dut.io_reset_vector = RESET_VECTOR
        await ClockCycles(self.dut, 1)
        self.dut.reset.value = 0
        self.dut.io_s0_fire_0.value = 1
        self.dut.io_s0_fire_1.value = 1
        self.dut.io_s0_fire_3.value = 1
        await Condition(self.dut, lambda: self.dut.io_s1_ready.value == 1)

        self.fire_s[0] = 1
        update = {'valid': 0}

        while True:
            self.assign_before_clock()
            await ClockCycles(self.dut, 1)
            self.assign_after_clock()
            s0_fire = 0
            npc = 0x114514
            # Ref Operation start:
            # Get Ref Prediction
            if self.fire_s[3]:
                predict_pass = self.compare_predict()
                error(hex(self.ref.lfsr.rand))

            # Update Ref
            # Updating must be in advance of predicting.
            if update['valid']:
                self.train_ref()
                error("Update.")

            # Ref Operation end.
            update, redirect = self.ftq.get_update_and_redirect(self.train_ghv)
            debug(f"Update Info: {update}")
            debug(f"Redirect Addr: {redirect}")

            # Set update info
            self.dut_update.assign(update)
            if update['valid']:
                error("Train dut.")

            if redirect is not None:
                for i in range(1, 4):
                    self.fire_s[i] = 0
                npc = redirect
                s0_fire = 1

            # If there is a prediction.
            if self.fire_s[3]:
                # If current instruction block is empty. This is an initial situation.
                if self.ifu.current_block.is_empty:
                    _ = self.ifu.get_predict_block_and_update_executor()
                    assert self.ifu.current_block.is_empty, "Instruction block shouldn't be empty."
                    npc = self.ifu.current_block.pc
                    s0_fire = 1
                elif not self.ftq.has_mispred:
                    last_stage_meta = self.dut.io_out_last_stage_meta.value
                    # If there are no previous incorrect predictions.
                    # predicts = self.meta_parser.takens
                    # FIXME: meta.takens are predictions from tage
                    meta_parser = MetaParser(last_stage_meta)
                    predicts = meta_parser.takens
                    block = self.ifu.get_predict_block_and_update_executor()

                    debug(
                        f"Prediction: meta_parse({predicts}), out_last_stage_meta({(meta_parser.meta >> 54) & 1}, {(meta_parser.meta >> 55) & 1})")
                    debug(
                        f"Actual Taken: {(block.br_slot.valid and block.br_slot.taken)} {(block.tail_slot.valid and block.tail_slot.sharing and block.tail_slot.taken)}")

                    if (block.tail_slot.valid and block.tail_slot.sharing and block.tail_slot.taken != predicts[1]) \
                            or (block.br_slot.valid and block.br_slot.taken != predicts[0]):
                        # If predictions are incorrect.
                        npc = 0x114514
                        s0_fire = 1
                        self.ftq.add_to_ftq(
                            block, last_stage_meta, self.ifu.current_block.pc, self.predict_ghv
                        )
                    else:
                        # If predictions are correct or block has one jump instruction.
                        npc = self.ifu.current_block.pc
                        s0_fire = 1
                        if not block.tail_slot.valid or block.tail_slot.valid and block.tail_slot.sharing:
                            # if prediction in block, commit to IFU.
                            self.ftq.add_to_ftq(
                                block, last_stage_meta, None, self.predict_ghv
                            )
                else:
                    # Had an incorrect prediction in previous
                    # If
                    npc = redirect if redirect is not None else 0x114514
                    s0_fire = 1

                # Flush for redirect.
                for i in range(1, 4):
                    self.fire_s[i] = 0

            self.dut_in.assign({
                'bits_s0_pc_0': self.pc_s[0],
                'bits_s0_pc_1': self.pc_s[0],
                'bits_s0_pc_2': self.pc_s[0],
                'bits_s0_pc_3': self.pc_s[0],
                'fh_tage': {
                    'hist_17_folded_hist': self.predict_ghv.get_fh(11, 32),
                    'hist_16_folded_hist': self.predict_ghv.get_fh(11, 119),
                    'hist_15_folded_hist': self.predict_ghv.get_fh(7, 13),
                    'hist_14_folded_hist': self.predict_ghv.get_fh(8, 8),
                    'hist_9_folded_hist': self.predict_ghv.get_fh(7, 32),
                    'hist_8_folded_hist': self.predict_ghv.get_fh(8, 119),
                    'hist_7_folded_hist': self.predict_ghv.get_fh(7, 8),
                    'hist_5_folded_hist': self.predict_ghv.get_fh(7, 119),
                    'hist_4_folded_hist': self.predict_ghv.get_fh(8, 13),
                    'hist_3_folded_hist': self.predict_ghv.get_fh(8, 32),
                    'hist_1_folded_hist': self.predict_ghv.get_fh(11, 13)
                },
                'fh_sc': {
                    'hist_12_folded_hist': self.predict_ghv.get_fh(4, 4),
                    'hist_11_folded_hist': self.predict_ghv.get_fh(8, 10),
                    'hist_2_folded_hist': self.predict_ghv.get_fh(8, 16)
                }
            })
            self.predict_ghv.apply_update()
            if redirect:
                debug("Redirect.")
                # if self.train_ghv.ghv != self.predict_ghv.ghv:
                self.predict_ghv.ghv = self.train_ghv.ghv
            else:
                debug("Continue Run.")

            self.pc_s[0] = npc
            self.fire_s[0] = s0_fire
            debug('-' * 20)

    def assign_before_clock(self):
        for i in range(4):
            for j in range(4):
                attr = getattr(self.pipeline_ctrl, f"s{i}_fire_{j}")
                attr.value = self.fire_s[i]

        # Set the value to 1 forcibly to obtain meta information
        # self.dut.io_s1_fire_0.value = 1
        # self.dut.io_s2_fire_0.value = 1

        self.dut_in.bits_s0_pc_0.value = self.pc_s[0]
        self.dut_in.bits_s0_pc_1.value = self.pc_s[0]
        self.dut_in.bits_s0_pc_2.value = self.pc_s[0]
        self.dut_in.bits_s0_pc_3.value = self.pc_s[0]

    def assign_after_clock(self):
        for i in range(3, 0, -1):
            self.fire_s[i] = self.fire_s[i - 1]
            self.pc_s[i] = self.pc_s[i - 1]

    def compare_predict(self) -> bool:
        parser = MetaParser(self.dut_out.last_stage_meta.value)
        s3_pc = self.pc_s[3]
        ref_predicts = tuple(1 if self.ref.predict(s3_pc, w) else 0 for w in range(2))
        full_pred = self.dut_out.s3.full_pred
        # dut_predicts = (full_pred.br_taken_mask_0.value > 0, full_pred.br_taken_mask_1.value > 0)
        dut_predicts = tuple(parser.takens)
        mlvp.error(f'Ref: {ref_predicts}, DUT: {dut_predicts}, {ref_predicts == dut_predicts}')

        return ref_predicts == dut_predicts

    def train_ref(self):
        mlvp.error("train.")
        train = self.ref.train
        train_meta = self.dut.io_update_bits_meta.value
        update_bits = self.dut_update.bits
        br_slot = update_bits.ftb_entry.brSlots_0
        tail_slot = update_bits.ftb_entry.tailSlot
        update_pc = update_bits.pc.value

        # train br_slot
        if br_slot.valid.value:
            train(update_pc, train_meta, update_bits.br_taken_mask_0.value, 0)
            pass

        # train tail_slot
        if br_slot.valid.value and tail_slot.valid.value and tail_slot.sharing.value:
            train(update_pc, train_meta, update_bits.br_taken_mask_1.value, 1)

