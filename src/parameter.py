from math import log2, ceil

# Instruction Info
INST_OFFSET_BITS = 1
PREDICT_WIDTH_OFFSET_BITS = 4
PREDICT_WIDTH_BYTES = 32

# TageSC Parameters
N_ROWS = 4096
BT_SIZE = 2048
NUM_BR = 2
TAGE_CTR_BITS = 3
UNSHUFFLE_BIT_WIDTH = ceil(log2(NUM_BR))
N_ROWS_PER_BR = N_ROWS / NUM_BR

# File
# FILE_PATH = "../../../utils/ready-to-run/linux.bin"
FILE_PATH = "../../../utils/ready-to-run/microbench.bin"
# FILE_PATH = "/home/wjy/Workspace/env-xs-ov-00-bpu/tests/mlvp-TageSC/test/case.bin"

RESET_VECTOR = 0x80000000

# Global History
GLOBAL_HISTORY_LEN = 256
