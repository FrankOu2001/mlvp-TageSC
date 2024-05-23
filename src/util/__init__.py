from parameter import UNSHUFFLE_BIT_WIDTH


def get_unshuffle_bits(x: int) -> int:
    """
    返回x的低UNSHUFFLE_BIT_WIDTH位
    """
    return x & ((1 << UNSHUFFLE_BIT_WIDTH) - 1)
