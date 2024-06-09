import sys
from dotenv import dotenv_values

sys.path.extend(dotenv_values().values())

import logging

import mlvp

from mlvp.reporter import set_line_coverage
from models.env.env import Env


async def bug_test():
    env = Env()
    mlvp.create_task(mlvp.start_clock(env.dut))
    mlvp.create_task(env.run())
    await mlvp.ClockCycles(env.dut, 10000)
    env.dut.finalize()


def test_dut(request):
    mlvp.setup_logging(
        log_level=logging.WARNING,
        # log_file="report/tage_sc_but_test.log"
    )
    mlvp.run(bug_test())

    set_line_coverage(request, "VTage_SC_coverage.dat")
