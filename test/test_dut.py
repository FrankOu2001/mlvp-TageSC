import logging

import mlvp

from UT_Tage_SC import DUTTage_SC as TageSC
from UT_Tage_SC.xspcomm import *
from env import Env
from models.bundle import *


async def bug_test(dut: TageSC):
    io_in = BranchPredictionReq.from_prefix(dut, "io_in_")
    enable_ctrl = EnableCtrlBundle.from_prefix(dut, "io_ctrl_")
    io_out = BranchPredictionResp.from_prefix(dut, "io_out_")
    io_update = UpdateBundle.from_prefix(dut, "io_update_")
    pipeline_ctrl = PipelineCtrlBundle.from_prefix(dut, "io_")
    # Set Imme
    for i in [dut.io_ctrl_sc_enable, dut.io_reset_vector, dut.reset]:
        i.SetWriteMode(XData.Imme)
    for i in range(4):
        for j in range(4):
            attr = getattr(pipeline_ctrl, f"s{i}_fire_{j}")
            if isinstance(attr, XData):
                attr = 0

    mlvp.create_task(mlvp.start_clock(dut))
    mlvp.create_task(Env(
        dut, io_in, io_out, io_update, enable_ctrl, pipeline_ctrl
    ).run())
    await mlvp.ClockCycles(dut, 100)


def test_dut():
    tage_sc = TageSC()
    tage_sc.init_clock("clock")

    mlvp.setup_logging(
        log_level=logging.DEBUG,
        # log_file="report/tage_sc_but_test.log"
    )
    mlvp.run(bug_test(tage_sc))

    tage_sc.finalize()
