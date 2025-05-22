# main.py

import time
from dotenv import load_dotenv
from binance.client import Client
from config import load_config
from strategy import MovingAverageCrossover
from logger import log_trade

def run_bot():
    # 1) Carga .env
    load_dotenv()

    # 2) Carga configuración
    cfg = load_config()
    api_key     = cfg["api_key"]
    api_secret  = cfg["api_secret"]
    symbol      = cfg["symbol"]
    interval    = cfg["interval"]
    usdt_balance= cfg["usdt_amount"]
    risk        = cfg["risk"]
    testnet     = cfg["testnet"]

    # 3) Inicializa cliente Binance
    client = Client(api_key, api_secret, testnet=testnet)
    if testnet:
        client.API_URL = 'https://testnet.binance.vision/api'

    # 4) Estrategia
    strat = MovingAverageCrossover(cfg["ma_fast"], cfg["ma_slow"])

    # 5) Estado de la posición
    btc_balance = 0.0
    entry_price = 0.0

    print(f"🚀 Bot iniciado para {symbol}")
    print(f"   USDT disponible: {usdt_balance} | riesgo por trade: {risk*100:.1f}%")

    # 6) Loop 24/7
    while True:
        try:
            # 0) Sincronizar balance con Binance
            usdt_balance = float(client.get_asset_balance("USDT")["free"])
            btc_balance  = float(client.get_asset_balance("BTC")["free"])

            # a) Trae últimas 100 velas
            klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
            closes = [float(k[4]) for k in klines]
            price  = closes[-1]

            # b) Señal de COMPRA
            if strat.should_buy(closes) and usdt_balance > 0:
                capital = usdt_balance * risk
                qty     = round(capital / price, 6)
                order   = client.order_market_buy(symbol=symbol, quantity=qty)

                btc_balance   += float(order["executedQty"])
                usdt_balance  -= capital
                entry_price    = price
                cost           = capital

                print(f"🔔 BUY {qty:.6f} BTC @ {price:.2f} USDT ({risk*100:.1f}% del capital)")
                log_trade(action="BUY", symbol=symbol, price=price, quantity=qty, cost=cost)

            # c) Señal de VENTA
            elif strat.should_sell(closes) and btc_balance > 0:
                order        = client.order_market_sell(symbol=symbol, quantity=btc_balance)
                sold_qty     = float(order["executedQty"])
                revenue      = sold_qty * price
                pnl          = revenue - (entry_price * sold_qty)

                usdt_balance += revenue
                print(f"🔔 SELL {sold_qty:.6f} BTC @ {price:.2f} USDT → PnL = {pnl:.2f} USDT")
                log_trade(action="SELL", symbol=symbol,
                          price=price, quantity=sold_qty,
                          revenue=revenue, pnl=pnl)

                # Reset posición
                btc_balance = 0.0
                entry_price = 0.0

        except Exception as e:
            print(f"⚠️ Error en loop: {e}")

        # d) Espera al siguiente tick (1m)
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
