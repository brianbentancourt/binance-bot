# main.py
import json
import math
import os
import traceback
import time
import threading
from dotenv import load_dotenv
from binance.client import Client
from config import load_config
from strategy import MovingAverageCrossover
from logger import log_trade

STATE_FILE = "state.json"

class Bot:
    def __init__(self, log_queue=None):
        self.log_queue = log_queue
        self.stop_event = threading.Event()
        self.bot_thread = None

        self.client = None
        self.cfg = None
        self.state = {}
        self.symbol_info = {}

    def _log(self, message):
        """Envía un mensaje a la cola de la GUI si existe, si no, lo imprime."""
        if self.log_queue:
            self.log_queue.put(message)
        else:
            print(message)

    def _save_state(self):
        """Guarda el estado actual en un archivo JSON."""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=4)
        self._log(f"Estado guardado: {self.state}")

    def _load_state(self):
        """Carga el estado desde un archivo JSON."""
        initial_state = {"btc_balance": 0.0, "entry_price": 0.0, "highest_price_since_buy": 0.0}
        if not os.path.exists(STATE_FILE):
            self.state = initial_state
            return
        try:
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.state = initial_state

    def setup(self):
        """Configura el bot, carga la configuración y se conecta al cliente."""
        try:
            self._log("Cargando configuración...")
            load_dotenv()
            self.cfg = load_config()
            api_key = self.cfg["api_key"]
            api_secret = self.cfg["api_secret"]
            testnet = self.cfg["testnet"]

            self._log("Inicializando cliente de Binance...")
            self.client = Client(api_key, api_secret, testnet=testnet)
            self.client.ping() # Verificar conexión
            self._log("Conexión con Binance exitosa.")

            self._log(f"Obteniendo reglas de trading para {self.cfg['symbol']}...")
            self.symbol_info = self.client.get_symbol_info(self.cfg['symbol'])
            
            lot_size = next(f for f in self.symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            price_filter = next(f for f in self.symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
            notional = next(f for f in self.symbol_info['filters'] if f['filterType'] == 'NOTIONAL')

            self.symbol_info['step_size'] = float(lot_size['stepSize'])
            self.symbol_info['qty_precision'] = int(round(-math.log(self.symbol_info['step_size'], 10), 0))
            self.symbol_info['tick_size'] = float(price_filter['tickSize'])
            self.symbol_info['price_precision'] = int(round(-math.log(self.symbol_info['tick_size'], 10), 0))
            self.symbol_info['min_notional'] = float(notional['minNotional'])
            self._log("Reglas de trading obtenidas.")
            
            return True
        except Exception as e:
            self._log(f"Error en la configuración: {e}")
            traceback.print_exc()
            return False

    def run(self):
        """El bucle principal del bot."""
        if not self.setup():
            self._log("Finalizando el bot debido a un error en la configuración.")
            return

        strat = MovingAverageCrossover(self.cfg["ma_fast"], self.cfg["ma_slow"])
        self._load_state()
        self._log(f"Estado inicial cargado: {self.state}")

        self._log(f"🚀 Bot iniciado para {self.cfg['symbol']}")
        self._log(f"   Capital: {self.cfg['usdt_amount']:.2f} USDT | Riesgo: {self.cfg['risk']*100:.1f}% | Trailing: {self.cfg['trailing_stop']*100:.1f}%")

        while not self.stop_event.is_set():
            try:
                self._log(f"\nLoop a las {time.strftime('%H:%M:%S')}")
                
                btc_balance = self.state.get('btc_balance', 0.0)
                entry_price = self.state.get('entry_price', 0.0)
                highest_price_since_buy = self.state.get('highest_price_since_buy', 0.0)

                actual_usdt_balance = float(self.client.get_asset_balance("USDT")["free"])
                self._log(f"USDT: {actual_usdt_balance:.2f} | BTC: {btc_balance:.{self.symbol_info['qty_precision']}f}")

                klines = self.client.get_klines(symbol=self.cfg['symbol'], interval=self.cfg['interval'], limit=100)
                closes = [float(k[4]) for k in klines]
                current_price = closes[-1]

                if entry_price == 0:
                    if strat.should_buy(closes):
                        self._log("Señal de compra detectada.")
                        capital_to_risk = self.cfg['usdt_amount'] * self.cfg['risk']
                        if actual_usdt_balance < capital_to_risk:
                            self._log(f"Fondos insuficientes. Se necesitan {capital_to_risk:.2f} USDT.")
                        else:
                            qty = capital_to_risk / current_price
                            adjusted_qty = math.floor(qty / self.symbol_info['step_size']) * self.symbol_info['step_size']
                            if adjusted_qty * current_price < self.symbol_info['min_notional']:
                                self._log(f"Valor nocional ({adjusted_qty * current_price:.2f}) es menor que el mínimo ({self.symbol_info['min_notional']}).")
                            else:
                                self._log("Intentando colocar orden de compra...")
                                order = self.client.order_market_buy(symbol=self.cfg['symbol'], quantity=f"{adjusted_qty:.{self.symbol_info['qty_precision']}f}")
                                self.state['btc_balance'] = float(order["executedQty"])
                                cost = float(order["cummulativeQuoteQty"])
                                self.state['entry_price'] = cost / self.state['btc_balance']
                                self.state['highest_price_since_buy'] = self.state['entry_price']
                                self._log(f"🔔 BUY {self.state['btc_balance']:.{self.symbol_info['qty_precision']}f} BTC @ {self.state['entry_price']:.{self.symbol_info['price_precision']}f} USDT")
                                log_trade(action="BUY", symbol=self.cfg['symbol'], price=self.state['entry_price'], quantity=self.state['btc_balance'], cost=cost)
                                self._save_state()
                else:
                    if current_price > highest_price_since_buy:
                        self.state['highest_price_since_buy'] = current_price
                        self._save_state()
                        self._log(f"Nuevo precio máximo: {self.state['highest_price_since_buy']:.{self.symbol_info['price_precision']}f} USDT")
                    
                    trailing_stop_price = self.state['highest_price_since_buy'] * (1 - self.cfg['trailing_stop'])
                    self._log(f"Precio: {current_price:.{self.symbol_info['price_precision']}f} | Stop: {trailing_stop_price:.{self.symbol_info['price_precision']}f}")

                    if current_price < trailing_stop_price:
                        self._log(f"🔴 Trailing Stop activado. Vendiendo...")
                        order = self.client.order_market_sell(symbol=self.cfg['symbol'], quantity=f"{self.state['btc_balance']:.{self.symbol_info['qty_precision']}f}")
                        sold_qty = float(order['executedQty'])
                        revenue = float(order['cummulativeQuoteQty'])
                        pnl = revenue - (self.state['entry_price'] * sold_qty)
                        self._log(f"🔔 SELL {sold_qty:.{self.symbol_info['qty_precision']}f} BTC → PnL = {pnl:.2f} USDT")
                        log_trade(action="SELL", symbol=self.cfg['symbol'], price=(revenue/sold_qty), quantity=sold_qty, revenue=revenue, pnl=pnl)
                        self.state = {"btc_balance": 0.0, "entry_price": 0.0, "highest_price_since_buy": 0.0}
                        self._save_state()

            except Exception as e:
                self._log(f"⚠️ Error en bucle principal: {e}")
                traceback.print_exc()
            
            # Esperar 60 segundos o hasta que el evento de parada sea activado
            self.stop_event.wait(60)
        
        self._log("Bucle del bot detenido.")

    def start(self):
        """Inicia el bot en un hilo separado."""
        self.stop_event.clear()
        self.bot_thread = threading.Thread(target=self.run, daemon=True)
        self.bot_thread.start()
        self._log("Hilo del bot iniciado.")

    def stop(self):
        """Detiene el bot."""
        if self.bot_thread and self.bot_thread.is_alive():
            self.stop_event.set()
            self._log("Señal de detención enviada al bot.")
            # No es necesario hacer join aquí para no bloquear la GUI

# El bot ahora se inicia desde gui.py, no desde aquí.
