import sys
from dotenv import dotenv_values

from UT_Tage_SC import DUTTage_SC

sys.path.extend(dotenv_values().values())

import logging

import mlvp

from mlvp.reporter import set_line_coverage
from models.env.env import Env


async def bug_test(dut):
    env = Env(dut)
    mlvp.create_task(mlvp.start_clock(env.dut))
    mlvp.create_task(env.run())
    # await mlvp.ClockCycles(env.dut, 10)
    await mlvp.ClockCycles(env.dut, 2125)


def test_dut(request):
    dut = DUTTage_SC()
    dut.init_clock("clock")
    mlvp.setup_logging(
        log_level=logging.WARNING,
        # log_file="report/tage_sc_but_test.log"
    )
    mlvp.run(bug_test(dut))
    dut.finalize()
    set_line_coverage(request, "VTage_SC_coverage.dat")
