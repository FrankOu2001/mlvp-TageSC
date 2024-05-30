from mlvp import *

from UT_Tage_SC import DUTTage_SC as TageSC
from models.bundle import *
from models.fake_ifu import FakeIFU
from models.global_history import GlobalHistory
from models.likely_ftq import FakeFTQ
from parameter import *
from util.meta_parser import MetaParser


class Env:
    def __init__(self,
                 dut: TageSC,
                 dut_in: BranchPredictionReq,
                 dut_out: BranchPredictionResp,
                 dut_update: UpdateBundle,
                 enable_ctrl: EnableCtrlBundle,
                 pipeline_ctrl: PipelineCtrlBundle):
        # Global History
        self.ghv = GlobalHistory()
        self.meta_parser = MetaParser(dut.io_out_last_stage_meta)
        self.ifu = FakeIFU("../../../utils/ready-to-run/linux.bin", RESET_VECTOR)
        self.ftq = FakeFTQ(self.meta_parser)

        self.dut = dut
        self.dut_in = dut_in
        self.dut_out = dut_out
        self.dut_update = dut_update
        self.enable_ctrl = enable_ctrl
        self.pipeline_ctrl = pipeline_ctrl
        self.fire_s = [0 for _ in range(4)]
        self.pc_s = [0 for _ in range(4)]
        self.expect_inst = [0 for _ in range(4)]

    async def run(self):
        self.enable_ctrl.tage_enable.value = 1
        self.enable_ctrl.sc_enable.value = 0
        self.pc_s[0] = RESET_VECTOR
        self.dut.reset.value = 1
        await ClockCycles(self.dut, 10)
        self.dut.reset.value = 0
        await ClockCycles(self.dut, 10)
        self.fire_s[0] = 1
        while True:
            self.pipeline_assign()
            await ClockCycles(self.dut, 1)
            self.pipeline_update()

            npc = -1

            # Updating must be in advance of predicting.
            update, redirect = self.ftq.get_update_and_redirect(self.ghv)
            debug(f"Update Info: {update}")
            debug(f"Redirect Addr: {redirect}")
            if update is not None:
                self.dut_update.assign(update)

            if redirect is not None:
                for i in range(1, 4):
                    self.fire_s[i] = 0
                npc = redirect

            # If there is a prediction.
            if self.fire_s[3]:
                # If current instruction block is empty. This is an initial situation.
                if self.ifu.current_block.is_empty:
                    _ = self.ifu.get_predict_block_and_update_executor()
                    assert self.ifu.current_block.is_empty, "Instruction block shouldn't be empty."
                    npc = self.ifu.current_block.pc
                elif not self.ftq.has_mispred:
                    # If there are no previous incorrect predictions.
                    predicts = self.meta_parser.takens
                    block = self.ifu.get_predict_block_and_update_executor()

                    debug(
                        f"Prediction: meta_parse({predicts}), out_last_stage_meta({(self.meta_parser.meta >> 54) & 1}, {(self.meta_parser.meta >> 55) & 1})")
                    debug(
                        f"Actual Taken: {(block.br_slot.valid and block.br_slot.taken != predicts[0])} {(block.tail_slot.valid and block.tail_slot.sharing and block.tail_slot.taken != predicts[1])}")

                    if (block.tail_slot.valid and block.tail_slot.sharing and block.tail_slot.taken != predicts[1]) \
                            or (block.br_slot.valid and block.br_slot.taken != predicts[0]):
                        # If predictions are incorrect.
                        npc = 0x1145141919
                        self.ftq.add_to_ftq(block, self.ifu.current_block.pc)
                    else:
                        # If predictions are correct or block has one jump instruction.
                        npc = self.ifu.current_block.pc
                        if not block.tail_slot.valid or block.tail_slot.valid and block.tail_slot.sharing:
                            # if prediction in block, commit to IFU.
                            self.ftq.add_to_ftq(block, None)
                else:
                    # Had an incorrect prediction in previous
                    # If
                    npc = redirect if redirect is not None else 0x1145141919810

                # Flush for redirect.
                for i in range(1, 4):
                    self.fire_s[i] = 0

            if redirect:
                debug("Redirect.")
            debug(f"npc: {npc}, is_mispred: {self.ftq.has_mispred}")

            self.pc_s[0] = npc
            debug('-' * 20)
        pass

    def pipeline_assign(self):
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

    def pipeline_update(self):
        for i in range(3, 0, -1):
            self.fire_s[i] = self.fire_s[i - 1]
            self.pc_s[i] = self.pc_s[i - 1]
            self.expect_inst[i] = self.expect_inst[i - 1]
        pass

    pass
