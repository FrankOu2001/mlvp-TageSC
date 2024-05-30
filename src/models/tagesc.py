from models.sc import SC
from models.tage import Tage
from util.lfsr import LFSR_64


class TageSC:
    def __init__(self):
        self.lfsr = LFSR_64()
        self.tage = Tage(self.lfsr)
        self.sc = SC()

    def predict(self, way: int):
        pass

    def update(self, way: int):
        pass
