# main.py
import json
import math
import os
import traceback
import time
from dotenv import load_dotenv
from binance.client import Client
from config import load_config
from strategy import MovingAverageCrossover
from logger import log_trade

# --- Gestión de Estado ---
STATE_FILE = "state.json"

def save_state(state):
    """Guarda el estado actual (posición) en un archivo JSON."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)
    print(f"Estado guardado: {state}")

def load_state():
    """Carga el estado desde un archivo JSON. Si no existe, devuelve un estado inicial."""
    initial_state = {"btc_balance": 0.0, "entry_price": 0.0, "highest_price_since_buy": 0.0}
    if not os.path.exists(STATE_FILE):
        return initial_state
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return initial_state

# --- Lógica Principal del Bot ---
def run_bot():
    # 1) Cargar configuración
    load_dotenv()
    cfg = load_config()
    api_key         = cfg["api_key"]
    api_secret      = cfg["api_secret"]
    symbol          = cfg["symbol"]
    interval        = cfg["interval"]
    trading_capital = cfg["usdt_amount"]
    risk            = cfg["risk"]
    trailing_stop   = cfg["trailing_stop"]
    testnet         = cfg["testnet"]

    # 2) Inicializar cliente de Binance
    client = Client(api_key, api_secret, testnet=testnet)

    # 3) Obtener reglas de trading del exchange
    try:
        symbol_info = client.get_symbol_info(symbol)
        lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        step_size = float(lot_size_filter['stepSize'])
        qty_precision = int(round(-math.log(step_size, 10), 0))

        price_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
        tick_size = float(price_filter['tickSize'])
        price_precision = int(round(-math.log(tick_size, 10), 0))

        notional_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL')
        min_notional = float(notional_filter['minNotional'])
        
        print(f"Reglas para {symbol}: Precisión Cantidad = {qty_precision}, Precisión Precio = {price_precision}.")
        print(f"Valor Nocional Mínimo: {min_notional} USDT.")

    except Exception:
        print("Error obteniendo información del símbolo.")
        traceback.print_exc()
        return

    # 4) Inicializar estrategia
    strat = MovingAverageCrossover(cfg["ma_fast"], cfg["ma_slow"])

    # 5) Cargar estado de la posición
    state = load_state()
    btc_balance = state.get('btc_balance', 0.0)
    entry_price = state.get('entry_price', 0.0)
    highest_price_since_buy = state.get('highest_price_since_buy', 0.0)
    print(f"Estado inicial cargado: {state}")

    print(f"🚀 Bot iniciado para {symbol}")
    print(f"   Capital base: {trading_capital:.2f} USDT | Riesgo: {risk*100:.1f}% | Trailing Stop: {trailing_stop*100:.1f}%")

    # 6) Bucle principal
    while True:
        try:
            print(f"\nLoop a las {time.strftime('%H:%M:%S')}")

            actual_usdt_balance = float(client.get_asset_balance("USDT")["free"])
            print(f"USDT disponible: {actual_usdt_balance:.2f} | Posición en BTC: {btc_balance:.{qty_precision}f}")

            klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
            closes = [float(k[4]) for k in klines]
            current_price = closes[-1]

            # --- Lógica de Decisión ---

            # A) Lógica de ENTRADA (COMPRA)
            if entry_price == 0: # Si no estamos en una posición
                if strat.should_buy(closes):
                    print("Señal de compra detectada.")
                    capital_to_risk = trading_capital * risk

                    if actual_usdt_balance < capital_to_risk:
                        print(f"Fondos insuficientes. Se necesitan {capital_to_risk:.2f} USDT.")
                    else:
                        qty = capital_to_risk / current_price
                        adjusted_qty = math.floor(qty / step_size) * step_size
                        
                        if adjusted_qty * current_price < min_notional:
                            print(f"Valor nocional ({adjusted_qty * current_price:.2f} USDT) es menor que el mínimo ({min_notional} USDT).")
                        else:
                            print("Intentando colocar orden de compra...")
                            order = client.order_market_buy(symbol=symbol, quantity=f"{adjusted_qty:.{qty_precision}f}")
                            
                            btc_balance = float(order["executedQty"])
                            cost = float(order["cummulativeQuoteQty"])
                            entry_price = cost / btc_balance
                            highest_price_since_buy = entry_price # Inicializamos el precio máximo

                            print(f"🔔 BUY {btc_balance:.{qty_precision}f} BTC @ {entry_price:.{price_precision}f} USDT")
                            log_trade(action="BUY", symbol=symbol, price=entry_price, quantity=btc_balance, cost=cost)
                            save_state({'btc_balance': btc_balance, 'entry_price': entry_price, 'highest_price_since_buy': highest_price_since_buy})

            # B) Lógica de SALIDA (TRAILING STOP)
            else: # Si estamos en una posición
                # 1. Actualizar el precio más alto si es necesario
                if current_price > highest_price_since_buy:
                    highest_price_since_buy = current_price
                    save_state({'btc_balance': btc_balance, 'entry_price': entry_price, 'highest_price_since_buy': highest_price_since_buy})
                    print(f"Nuevo precio máximo alcanzado: {highest_price_since_buy:.{price_precision}f} USDT")

                # 2. Calcular el precio del Trailing Stop
                trailing_stop_price = highest_price_since_buy * (1 - trailing_stop)

                print(f"Precio actual: {current_price:.{price_precision}f} | Trailing Stop en: {trailing_stop_price:.{price_precision}f}")

                # 3. Comprobar si el precio actual ha caído por debajo del Trailing Stop
                if current_price < trailing_stop_price:
                    print(f"🔴 Trailing Stop activado a {trailing_stop_price:.{price_precision}f}. Vendiendo...")
                    
                    order = client.order_market_sell(symbol=symbol, quantity=f"{btc_balance:.{qty_precision}f}")
                    
                    sold_qty = float(order['executedQty'])
                    revenue = float(order['cummulativeQuoteQty'])
                    pnl = revenue - (entry_price * sold_qty)

                    print(f"🔔 SELL {sold_qty:.{qty_precision}f} BTC → PnL = {pnl:.2f} USDT")
                    log_trade(action="SELL", symbol=symbol, price=(revenue/sold_qty), quantity=sold_qty, revenue=revenue, pnl=pnl)

                    # Resetear el estado para la próxima operación
                    btc_balance = 0.0
                    entry_price = 0.0
                    highest_price_since_buy = 0.0
                    save_state({'btc_balance': btc_balance, 'entry_price': entry_price, 'highest_price_since_buy': highest_price_since_buy})

        except Exception as e:
            print(f"⚠️ Error inesperado en el bucle principal: {e}")
            traceback.print_exc()

        time.sleep(60)

if __name__ == "__main__":
    run_bot()