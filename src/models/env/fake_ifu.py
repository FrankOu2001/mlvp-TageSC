from collections import namedtuple
from math import floor
from typing import Optional

from mlvp import debug, warning

from parameter import RESET_VECTOR, PREDICT_WIDTH_BYTES
from util.executor import Executor

__all__ = ["FakeFTBEntry", "FakeIFU"]

Branch = namedtuple('Branch', ['pc', 'target', 'taken'])
BrSlotEntry = namedtuple('BrSlotEntry', ['valid', 'taken', 'target'])
TailSlotEntry = namedtuple('TailSlotEntry', ['valid', 'taken', 'sharing', 'target'])


class FakeFTBEntry:
    def __init__(self, pc, br_slot_valid: bool = False, br_slot_taken: bool = False,
                 tail_slot_valid: bool = False, tail_slot_taken: bool = False, tail_slot_sharing: bool = False):
        self.pc = -1
        self.br_slot = BrSlotEntry(br_slot_valid, br_slot_taken, 0)
        self.tail_slot = TailSlotEntry(tail_slot_valid, tail_slot_taken, tail_slot_sharing, 0)

    @property
    def is_empty(self):
        return not self.br_slot.valid and not self.is_tail_slot_has_br

    @property
    def is_tail_slot_has_br(self):
        return self.tail_slot.valid and self.tail_slot.sharing

    @property
    def is_br_slot_taken(self):
        return self.br_slot.valid and self.br_slot.taken

    @property
    def is_tail_slot_taken(self):
        return self.is_tail_slot_has_br and self.tail_slot.taken

    def __str__(self):
        return f"[FakeFTB Entry]: PC({self.pc}), {self.br_slot}, {self.tail_slot}"


class FakeIFU:
    def __init__(self, filename, reset_vector=RESET_VECTOR):
        self._executor = Executor(filename)
        self._pc = reset_vector
        self._block: Optional[FakeFTBEntry] = None
        self._set_predict_block_and_update_executor()

    def _set_predict_block_and_update_executor(self):
        entry = FakeFTBEntry()
        entry.pc = self._pc
        # 未来的分支指令，可能是当前指令，也有可能是后面的指令
        current = self._executor.current_branch['pc']
        fallthrough_addr = self._pc + PREDICT_WIDTH_BYTES

        # assert self._pc < current, "Can't start after the first branch instruction."

        while current < fallthrough_addr:
            branch = self._executor.current_branch

            self._executor.jump_to_current_branch()
            current = self._executor.current_branch['pc']

            is_cond = self._executor.is_cond_branch_inst(branch)
            inst_len = self._executor.branch_inst_len(branch)
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

    def get_predict_block_and_update_executor(self) -> FakeFTBEntry:
        block = self.current_block
        current = self._executor.current_branch['pc']

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
            warning("FakeIFU: Warning! Block doesn't have any instruction.")

        self._set_predict_block_and_update_executor()
        return block
