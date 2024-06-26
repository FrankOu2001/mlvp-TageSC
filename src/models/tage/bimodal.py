import mlvp
from mlvp.modules import TwoBitsCounter

from parameter import BT_SIZE, INST_OFFSET_BITS
from util import get_phy_br_idx

__all__ = ["BimodalPredictor"]


class BimodalPredictor:
    """
    T0预测器的基类
    包含2位饱和计数器, 2路各2048项
    槽里有一条指令就用一路的数据，有两条就用两路的数据
    通过PC[11:1]直接索引(PC)为预测块的索引
    返回数据的数据为s1_cnt
    """

    def __init__(self):
        self.tables: tuple[tuple[TwoBitsCounter, ...], ...] = tuple(
            (TwoBitsCounter(), TwoBitsCounter()) for _ in range(BT_SIZE)
        )

    def train(self, pc: int, taken: bool, way: int) -> None:
        """
        训练基础预测器
        :param pc: 更新的pc地址
        :param taken: 指令的实际执行情况
        :param way: 哪一路
        :return:
        """
        # u_idx = pc & 0x7ff  # pc[10:0]
        # br_lgc_idx = get_lgc_br_idx(u_idx, way)
        # self.tables[u_idx][br_lgc_idx].update(taken)
        self.get_ctr(pc, way).update(taken)
        mlvp.debug(f"T0 update finish, {pc:x} way{way}, train_taken: {taken}, t0_ctr(after update): {self.get_ctr(pc, way).counter}")

    def predict(self, pc: int, way: int) -> bool:
        """
        :param pc:预测块的pc地址
        :param way: 哪一路
        :return: 预测结果 taken/not taken
        """
        return self.get_ctr(pc, way).get_prediction()

    def gets(self, pc: int) -> tuple[bool, ...]:
        """
        :param pc:预测块的pc地址
        :return: pc对应的两个槽的分支预测结果
        """
        return tuple(self.predict(pc, way) for way in range(2))

    def get_ctr(self, pc: int, way: int) -> TwoBitsCounter:
        idx = (pc & 0xfff) >> INST_OFFSET_BITS # pc[11:1]
        logical_way = get_phy_br_idx(idx, way)
        mlvp.debug(f"From T0, pc: {pc:x} -> idx: {idx:x}, physical way: {way} -> logical_way: {logical_way}, value: {self.tables[idx][logical_way].counter}")
        return self.tables[idx][logical_way]
