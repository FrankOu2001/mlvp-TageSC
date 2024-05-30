from parameter import *


def get_unshuffle_bits(x: int) -> int:
    """
    返回x的低UNSHUFFLE_BIT_WIDTH位
    """
    return x & ((1 << UNSHUFFLE_BIT_WIDTH) - 1)


def get_lgc_br_idx(unhashed_idx: int, br_pidx: int) -> int:
    """
    :param br_pidx: 预测块中指令槽的物理地址
    :return: unhashed_idx的低UNSHUFFLE_BIT_WIDTH位与br_pidx的异或
    """
    # unshuffle_bits = unhasshed_idx & (1 << unshuffled_bit_width) - 1
    return (unhashed_idx & UNSHUFFLE_BIT_WIDTH) ^ br_pidx


def get_phy_br_idx(unhashed_idx: int, br_lidx: int) -> int:
    """
    :param br_lidx: 预测块中指令槽的逻辑地址
    :return: unhashed_idx的低UNSHUFFLE_BIT_WIDTH位与br_lidx低log2(NUM_BR)位的异或
    """
    return (unhashed_idx & 1) ^ (br_lidx & UNSHUFFLE_BIT_WIDTH)  # unhashed_idx&1 ^ br_lidx&1
