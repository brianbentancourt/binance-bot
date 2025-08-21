# strategy.py (Corregido)
import numpy as np

class Strategy:
    def should_buy(self, closes): ...
    def should_sell(self, closes): ...

class MovingAverageCrossover(Strategy):
    def __init__(self, fast: int, slow: int):
        self.fast, self.slow = fast, slow

    def should_buy(self, closes):
        # Necesitamos al menos 'slow' + 1 velas para comparar la actual con la anterior
        if len(closes) < self.slow + 1:
            return False

        # Medias móviles de la vela ACTUAL (la última de la lista)
        ma_fast_actual = np.mean(closes[-self.fast:])
        ma_slow_actual = np.mean(closes[-self.slow:])

        # Medias móviles de la vela ANTERIOR (todas menos la última)
        ma_fast_anterior = np.mean(closes[-self.fast-1:-1])
        ma_slow_anterior = np.mean(closes[-self.slow-1:-1])

        # La señal de compra ocurre solo en el momento del cruce
        return ma_fast_actual > ma_slow_actual and ma_fast_anterior <= ma_slow_anterior

    def should_sell(self, closes):
        # La lógica es la misma que para la compra
        if len(closes) < self.slow + 1:
            return False

        # Medias móviles de la vela ACTUAL
        ma_fast_actual = np.mean(closes[-self.fast:])
        ma_slow_actual = np.mean(closes[-self.slow:])

        # Medias móviles de la vela ANTERIOR
        ma_fast_anterior = np.mean(closes[-self.fast-1:-1])
        ma_slow_anterior = np.mean(closes[-self.slow-1:-1])

        # La señal de venta ocurre solo en el momento del cruce
        return ma_fast_actual < ma_slow_actual and ma_fast_anterior >= ma_slow_anterior