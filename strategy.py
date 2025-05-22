# strategy.py
import numpy as np

class Strategy:
    def should_buy(self, closes): ...
    def should_sell(self, closes): ...

class MovingAverageCrossover(Strategy):
    def __init__(self, fast: int, slow: int):
        self.fast, self.slow = fast, slow

    def should_buy(self, closes):
        if len(closes) < self.slow: 
            return False
        ma_fast = np.mean(closes[-self.fast:])
        ma_slow = np.mean(closes[-self.slow:])
        return ma_fast > ma_slow

    def should_sell(self, closes):
        if len(closes) < self.slow:
            return False
        ma_fast = np.mean(closes[-self.fast:])
        ma_slow = np.mean(closes[-self.slow:])
        return ma_fast < ma_slow
