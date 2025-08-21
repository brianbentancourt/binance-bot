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
    if not os.path.exists(STATE_FILE):
        return {"btc_balance": 0.0, "entry_price": 0.0}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Si el archivo está corrupto o vacío, empieza de cero por seguridad.
        return {"btc_balance": 0.0, "entry_price": 0.0}

# --- Lógica Principal del Bot ---
def run_bot():
    # 1) Cargar configuración desde archivos .env y config.py
    load_dotenv()
    cfg = load_config()
    api_key         = cfg["api_key"]
    api_secret      = cfg["api_secret"]
    symbol          = cfg["symbol"]
    interval        = cfg["interval"]
    trading_capital = cfg["usdt_amount"]
    risk            = cfg["risk"]
    take_profit     = cfg["take_profit"]
    stop_loss       = cfg["stop_loss"]
    testnet         = cfg["testnet"]

    # 2) Inicializar cliente de Binance
    client = Client(api_key, api_secret, testnet=testnet)

    # 3) Obtener reglas de trading del exchange para el símbolo
    try:
        symbol_info = client.get_symbol_info(symbol)
        
        # Regla para la CANTIDAD (LOT_SIZE)
        lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        step_size = float(lot_size_filter['stepSize'])
        qty_precision = int(round(-math.log(step_size, 10), 0))

        # Regla para el PRECIO (PRICE_FILTER)
        price_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
        tick_size = float(price_filter['tickSize'])
        price_precision = int(round(-math.log(tick_size, 10), 0))

        # Regla para el VALOR NOCIONAL (NOTIONAL)
        notional_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL')
        min_notional = float(notional_filter['minNotional'])
        
        print(f"Reglas para {symbol}: Precisión Cantidad = {qty_precision}, Precisión Precio = {price_precision}.")
        print(f"Valor Nocional Mínimo: {min_notional} USDT.")

    except Exception:
        print("Error obteniendo información del símbolo. Ocurrió una excepción:")
        traceback.print_exc()
        return

    # 4) Inicializar estrategia
    strat = MovingAverageCrossover(cfg["ma_fast"], cfg["ma_slow"])

    # 5) Cargar estado de la posición desde el archivo state.json
    state = load_state()
    btc_balance = state.get('btc_balance', 0.0)
    entry_price = state.get('entry_price', 0.0)
    print(f"Estado inicial cargado: {state}")

    print(f"🚀 Bot iniciado para {symbol}")
    print(f"   Capital base: {trading_capital:.2f} USDT | Riesgo: {risk*100:.1f}% | TP: {take_profit*100:.1f}% | SL: {stop_loss*100:.1f}%")

    # 6) Bucle principal
    while True:
        try:
            print(f"\nLoop a las {time.strftime('%H:%M:%S')}")

            # Sincronizar balance de USDT real desde la API
            actual_usdt_balance = float(client.get_asset_balance("USDT")["free"])
            print(f"USDT disponible: {actual_usdt_balance:.2f} | Posición en BTC: {btc_balance:.{qty_precision}f}")

            # Obtener datos de mercado
            klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
            closes = [float(k[4]) for k in klines]
            current_price = closes[-1]

            # --- Lógica de Decisión ---

            # A) Lógica de COMPRA
            # Solo compramos si no estamos ya en una posición (entry_price == 0)
            if strat.should_buy(closes) and entry_price == 0:
                print("Señal de compra detectada.")
                capital_to_risk = trading_capital * risk

                if actual_usdt_balance < capital_to_risk:
                    print(f"Fondos insuficientes. Se necesitan {capital_to_risk:.2f} USDT pero solo hay {actual_usdt_balance:.2f}.")
                else:
                    qty = capital_to_risk / current_price
                    adjusted_qty = math.floor(qty / step_size) * step_size
                    
                    if adjusted_qty * current_price < min_notional:
                        print(f"Valor nocional ({adjusted_qty * current_price:.2f} USDT) es menor que el mínimo ({min_notional} USDT). Omitiendo.")
                    else:
                        print("Intentando colocar orden de compra...")
                        order = client.order_market_buy(symbol=symbol, quantity=f"{adjusted_qty:.{qty_precision}f}")
                        
                        # Actualizar estado con datos REALES de la orden
                        btc_balance = float(order["executedQty"])
                        cost = float(order["cummulativeQuoteQty"])
                        entry_price = cost / btc_balance

                        print(f"🔔 BUY {btc_balance:.{qty_precision}f} BTC @ {entry_price:.{price_precision}f} USDT")
                        log_trade(action="BUY", symbol=symbol, price=entry_price, quantity=btc_balance, cost=cost)
                        save_state({'btc_balance': btc_balance, 'entry_price': entry_price})

                        # Colocar orden OCO para proteger la posición
                        try:
                            tp_price = entry_price * (1 + take_profit)
                            sl_price = entry_price * (1 - stop_loss)
                            sl_limit_price = sl_price * 0.999

                            print(f"Colocando orden OCO: TP @ {tp_price:.{price_precision}f}, SL @ {sl_price:.{price_precision}f}")
                            client.create_oco_order(
                                symbol=symbol,
                                side='SELL',
                                quantity=f"{btc_balance:.{qty_precision}f}",
                                price=f"{tp_price:.{price_precision}f}",
                                stopPrice=f"{sl_price:.{price_precision}f}",
                                stopLimitPrice=f"{sl_limit_price:.{price_precision}f}",
                                stopLimitTimeInForce='GTC'
                            )
                            print("Orden OCO colocada exitosamente.")
                        except Exception as e:
                            print(f"⚠️ Error crítico al colocar la orden OCO: {e}. Considera vender manualmente.")

            # B) Lógica de "Limpieza" (detectar si la OCO se ejecutó)
            # Si estábamos en una posición pero ahora el balance de BTC en la cuenta es casi cero
            elif entry_price != 0:
                live_btc_balance = float(client.get_asset_balance(symbol[:-4])["free"])
                if live_btc_balance < step_size:
                    print(f"📈 Operación cerrada (TP o SL alcanzado). Reseteando estado.")
                    
                    # Logueamos el cierre. Usamos el btc_balance guardado como la cantidad
                    # y el precio actual como una referencia, ya que no conocemos el precio exacto de ejecución.
                    log_trade(
                        action="SELL", 
                        symbol=symbol, 
                        price=current_price,  # Usamos el precio actual como referencia
                        quantity=btc_balance, # Usamos el balance que teníamos en la posición
                        pnl="N/A (Cierre OCO)"
                    )
                    
                    btc_balance = 0.0
                    entry_price = 0.0
                    save_state({'btc_balance': btc_balance, 'entry_price': entry_price})

        except Exception as e:
            print(f"⚠️ Error inesperado en el bucle principal: {e}")
            traceback.print_exc()

        # Esperar al siguiente ciclo
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
