from collections import namedtuple
from math import floor
from typing import Optional

from mlvp import debug, warning

from parameter import RESET_VECTOR, PREDICT_WIDTH_BYTES
from util.executor import Executor

__all__ = ["FakeFTBEntry", "FakeIFU"]



Branch = namedtuple('Branch', ['pc', 'target', 'taken'])
BrSlotEntry = namedtuple('BrSlotEntry', ['valid', 'taken', 'target', 'len'])
TailSlotEntry = namedtuple('TailSlotEntry', ['valid', 'taken', 'target', 'sharing', 'len'])


class FakeFTBEntry:
    def __init__(self):
        self.pc = -1
        self.br_slot = BrSlotEntry(False, False, 0, -1)
        self.tail_slot = TailSlotEntry(False, False, 0, False, -1)

    @property
    def is_empty(self):
        return not self.br_slot.valid and not self.tail_slot.valid

    def __str__(self):
        return f"[FTB Entry]: PC({self.pc}), {self.br_slot}, {self.tail_slot}"


class FakeIFU:
    def __init__(self, filename, reset_vector=RESET_VECTOR):
        self.executor = Executor(filename)
        self._pc = reset_vector
        self._block: Optional[FakeFTBEntry] = None
        self._set_predict_block_and_update_executor()

    def _set_predict_block_and_update_executor(self):
        entry = FakeFTBEntry()
        entry.pc = self._pc
        # 未来的分支指令，可能是当前指令，也有可能是后面的指令
        current = self.executor.current_branch['pc']
        fallthrough_addr = self._pc + PREDICT_WIDTH_BYTES

        # assert self._pc < current, "Can't start after the first branch instruction."

        while current < fallthrough_addr:
            branch = self.executor.current_branch

            self.executor.jump_to_current_branch()
            current = self.executor.current_branch['pc']

            is_cond = self.executor.is_cond_branch_inst(branch)
            inst_len = self.executor.branch_inst_len(branch)
            if is_cond and not entry.tail_slot.valid:
                # is condition and tail_slot is free
                if not entry.br_slot.valid:
                    entry.br_slot = BrSlotEntry(True, branch['taken'], branch['target'], inst_len)
                else:
                    entry.tail_slot = TailSlotEntry(True, branch['taken'], branch['target'], True, inst_len)
            elif not entry.tail_slot.valid:
                # is jump and tail_slot_is free
                entry.tail_slot = TailSlotEntry(True, branch['taken'], branch['target'], False, inst_len)
                break
            else:
                break
        self._block = entry

    @property
    def current_block(self):
        return self._block

    def get_predict_block_and_update_executor(self):
        block = self.current_block
        current = self.executor.current_branch['pc']

        debug(f'FakeIFU: Fetch a instruction block at {hex(block.pc)}, with content: {block}')
        if not block.is_empty:
            if block.tail_slot.valid and block.tail_slot.taken:
                # 当前块中最后一条指令跳转的话(有2条指令）
                target = block.tail_slot.target
                bias = floor((current - target) / 32) * 32
                self._pc = target + bias
            elif block.br_slot.valid and block.br_slot.taken:
                # 当前块中最后一条指令跳转的话(有1条指令)
                target = block.tail_slot.target
                bias = floor((current - target) / 32) * 32
                self._pc = target + bias
            else:
                # 当前块中没有跳转的分支
                self._pc += floor((current - block.pc) / 32) * 32
        else:
            # 如果当前块中没有条件分支指令
            self._pc += floor((current - block.pc) / 32) * 32
            warning("FakeIFU: Error! Block doesn't have any instruction.")

        self._set_predict_block_and_update_executor()
        return block
