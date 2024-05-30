import logging

import mlvp

from util.executor import Executor
from collections import namedtuple
from math import floor
from mlvp import debug, error
from parameter import RESET_VECTOR
from typing import NamedTuple

PREDICT_WIDTH_BYTES = 32

Branch = namedtuple('Branch', ['pc', 'target', 'taken'])
# BrSlotEntry = namedtuple('BrSlotEntry', ['valid', 'taken', 'len'])
# TailSlotEntry = namedtuple('TailSlotEntry', ['valid', 'taken', 'len', 'sharing'])


class FakeIFU:
    def __init__(self, filename, reset_vector=RESET_VECTOR):
        self.executor = Executor(filename)
        self._pc = reset_vector
        self._block = []
        self._set_predict_block_and_update_executor()

    def _set_predict_block_and_update_executor(self):
        block = []
        num_slot = 2
        # 未来的分支指令，可能是当前指令，也有可能是后面的指令
        current = self.executor.current_branch['pc']
        fallthrough_addr = self._pc + PREDICT_WIDTH_BYTES

        # assert self._pc < current, "Can't start after the first branch instruction."

        while num_slot > 0 and current < fallthrough_addr:
            branch = self.executor.current_branch
            block.append(branch)
            num_slot -= 1
            self.executor.jump_to_current_branch()
            current = self.executor.current_branch['pc']

            is_cond = self.executor.is_cond_branch_inst(branch)
            if not is_cond:
                break

        self._block = block

    def get_predict_block(self):
        return self._pc, self._block

    def get_predict_block_and_update_executor(self):
        block_pc, block = self.get_predict_block()
        current = self.executor.current_branch['pc']

        debug(f'FakeIFU: Fetch a instruction block at {hex(block_pc)}, with content: {block}')
        if block:
            if block[-1]['taken']:
                # 当前块中最后一条指令跳转的话
                target = block[-1]['target']
                bias = floor((current - target) / 32) * 32
                self._pc = target + bias
                pass
            else:
                # 当前块中没有跳转的分支
                self._pc += floor((current - block_pc) / 32) * 32
        else:
            # 如果当前块中没有条件分支指令
            self._pc += floor((current - block_pc) / 32) * 32
            error("FakeIFU: Error! Block doesn't have any instruction.")

        self._set_predict_block_and_update_executor()
        return block_pc, block

    @property
    def current_block_pc(self):
        return self._pc

    @property
    def current_block(self):
        return


if __name__ == '__main__':
    t = FakeIFU("../../../utils/ready-to-run/linux.bin")
    print('start at', t._pc)
    for _ in range(15):
        print(t.get_predict_block_and_update_executor())

    for _ in range(3):
        print(t.get_predict_block())