from collections import namedtuple

from BRTParser import BRTParser

__all__ = ["Executor"]

InstInfo = namedtuple("InstInfo", ["pc", "inst_len", "branch"])


class Executor:
    """Get program real execution instruction flow."""

    def __init__(self, filename):
        self._executor = BRTParser().fetch(filename)
        self._current_branch = next(self._executor)  # 当前的指令（分支指令）

        # self.jump_to_current_branch()

    @property
    def current_branch(self):
        """Return current instruction information."""
        return self._current_branch

    def jump_to_current_branch(self):
        self._current_branch = next(self._executor)

    @staticmethod
    def random_inst_len(pc: int) -> int:
        xor_ans = 0
        for i in range(8):
            xor_ans ^= (pc >> i) & 1
        return 2 if xor_ans else 4

    @staticmethod
    def is_cond_branch_inst(branch: dict) -> bool:
        return branch["type"] == "*.CBR"

    @staticmethod
    def is_jump_inst(branch: dict) -> bool:
        return not Executor.is_cond_branch_inst(branch)

    @staticmethod
    def is_call_inst(branch: dict) -> bool:
        return ".CALL" in branch["type"]

    @staticmethod
    def is_ret_inst(branch: dict) -> bool:
        return ".RET" in branch["type"]

    @staticmethod
    def is_jal_inst(branch: dict) -> bool:
        return branch["type"] == "I.JAL" or branch["type"] == "P.JAL"

    @staticmethod
    def is_jalr_inst(branch: dict) -> bool:
        return ".JALR" in branch["type"] or ".JR" in branch["type"]

    @staticmethod
    def is_compressed_inst(branch: dict) -> bool:
        inst_type = branch["type"]
        if "C." in inst_type:
            return True
        elif Executor.is_cond_branch_inst(branch):
            return Executor.random_inst_len(branch["pc"]) == 2
        else:
            return False

    @staticmethod
    def branch_inst_len(branch: dict) -> int:
        return 2 if Executor.is_compressed_inst(branch) else 4
