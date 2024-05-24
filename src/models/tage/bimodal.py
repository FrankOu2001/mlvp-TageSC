from mlvp.modules import TwoBitsCounter
from parameter import BT_SIZE
from util import get_lgc_br_idx, get_phy_br_idx


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
        更新过程: 根据执行情况更新索引对应的饱和计数器
        取出对应的pc块用的是物理的idx, 但访问块中的数据是用的是虚拟idx.
        ! 但是在生成的Verilog代码中:
        ! wire        updateValids_0 =
        !   io_update_bits_ftb_entry_brSlots_0_valid & io_update_valid
        !   & ~io_update_bits_ftb_entry_always_taken_0;	// @[src/main/scala/xiangshan/frontend/Tage.scala:614:{47,50}]
        ! wire        updateValids_1 =
        !   io_update_bits_ftb_entry_tailSlot_valid & io_update_bits_ftb_entry_tailSlot_sharing
        !   & io_update_valid & ~io_update_bits_ftb_entry_always_taken_1
        !   & ~io_update_bits_br_taken_mask_0;	// @[src/main/scala/xiangshan/frontend/Tage.scala:614:{50,84}, :615:7]
        ! Tage信息的更新会说到ftb_entry的影响, 但是双方的文档都没有提到这一点
        """
        # u_idx = pc & 0x7ff  # pc[10:0]
        # br_lgc_idx = get_lgc_br_idx(u_idx, way)
        # self.tables[u_idx][br_lgc_idx].update(taken)
        self._get_ctr(pc, way).update(taken)

    def get(self, pc: int, way: int) -> bool:
        """
        :param way: 哪一路
        :param pc:预测块的pc地址
        :return: pc对应的两个槽的分支预测结果
        """
        return self._get_ctr(pc, way).get_prediction() >= 0b10

    def gets(self, pc: int) -> tuple[bool, bool]:
        """
        :param pc:预测块的pc地址
        :return: pc对应的两个槽的分支预测结果
        """
        return tuple(self.get(pc, way) for way in range(2))

    def _get_ctr(self, pc: int, way: int) -> TwoBitsCounter:
        idx = pc & 0x7ff  # pc[10:0]
        return self.tables[get_phy_br_idx(idx, way)][way]