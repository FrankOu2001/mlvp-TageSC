import random
import sys

import mlvp
from dotenv import dotenv_values

sys.path.extend(dotenv_values().values())
from UT_Tage_SC import DUTTage_SC
from models.env.tagesc_pins import *
from models.env.global_history import GlobalHistory
from util.meta_parser import MetaParser
from mlvp.funcov import *
from mlvp.reporter import *

from checkpoints_tage_predict import *
from checkpoints_tage_train import *


def init_tage_sc_pins():
    dut = DUTTage_SC()
    dut.init_clock("clock")
    return TageSCPins(dut)


async def rand_test(pins: TageSCPins):
    mlvp.create_task(mlvp.start_clock(pins.dut))
    """pins setting begin"""
    await pins.initialize()
    pins.set_tage_enable(True)
    pins.set_sc_enable(True)
    """pins setting end"""
    ghv = GlobalHistory()

    pc = 0x8000000  # + random.randint(0, 0xff)

    for i in range(50):
        taken = i > 25, i < 25
        p = await pins.cmd_predict(pc + 0x10, ghv.value)
        parser = MetaParser(p['last_stage_meta'])
        miss = (parser.takens[0] != taken[0], parser.takens[1] != taken[1])
        await pins.cmd_train(UpdateRecord(
            pc, True, True, True, p['last_stage_meta'], ghv.value, taken, miss, 0, 0
        ))

    for i in range(50):
        taken = True, True
        p = await pins.cmd_predict(pc + 0x10, ghv.value)
        parser = MetaParser(p['last_stage_meta'])
        miss = (parser.takens[0] != taken[0], parser.takens[1] != taken[1])
        await pins.cmd_train(UpdateRecord(
            pc, i > 25, True, True, p['last_stage_meta'], ghv.value, taken, miss, 0, 0
        ))

    for i in range(20000):
        taken = (random.randint(0, 1) > 0, random.randint(0, 1) > 0)
        # valid = (random.randint(0, 1) > 0, random.randint(0, 1) > 0) if i > 0 else (True, True)
        p = await pins.cmd_predict(pc + random.randint(0, 0xf) * 32, ghv.value)
        parser = MetaParser(p['last_stage_meta'])
        miss = (parser.takens[0] != taken[0], parser.takens[1] != taken[1])
        await pins.cmd_train(UpdateRecord(
            pc, True, True, True, p['last_stage_meta'], ghv.value, taken, miss, 0, 0
        ))
        ghv.update(taken[0])
        ghv.update(taken[1])
    pass


def test_func(request) -> None:
    pins = init_tage_sc_pins()

    g_tage_predict = get_coverage_group_of_tage_predict(pins.dut)
    g_tage_train = get_coverage_group_of_tage_train(pins.dut)

    pins.dut.StepRis(lambda _: g_tage_predict.sample())
    pins.dut.StepRis(lambda _: g_tage_train.sample())

    mlvp.run(rand_test(pins))
    pins.dut.finalize()
    set_func_coverage(request, [g_tage_predict, g_tage_train])
    set_line_coverage(request, "VTage_SC_coverage.dat")


if __name__ == '__main__':
    generate_pytest_report('report.html')
