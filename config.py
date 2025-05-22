# config.py

from dotenv import load_dotenv
import os
import argparse

# Carga variables de .env en os.environ
load_dotenv()

def load_config():
    p = argparse.ArgumentParser(description="Configuración del Trading Bot")
    p.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Par de trading (por defecto BTCUSDT)"
    )
    p.add_argument(
        "--interval",
        default="1m",
        help="Intervalo de velas (p.ej. 1m, 5m, 15m; por defecto 1m)"
    )
    p.add_argument(
        "--usdt",
        type=float,
        default=None,
        help="Cantidad inicial de USDT para invertir (sobrescribe USDT_AMOUNT)"
    )
    p.add_argument(
        "--fast",
        type=int,
        default=10,
        help="Periodo de la media móvil rápida (por defecto 10)"
    )
    p.add_argument(
        "--slow",
        type=int,
        default=50,
        help="Periodo de la media móvil lenta (por defecto 50)"
    )
    p.add_argument(
        "--risk",
        type=float,
        default=None,
        help="Fracción del capital a invertir por trade (0.1 = 10%; por defecto RISK en .env o 1.0)"
    )
    p.add_argument(
        "--testnet",
        action="store_true",
        help="Usar Binance Testnet"
    )
    args = p.parse_args()

    # Credenciales según entorno
    if args.testnet:
        api_key    = os.getenv("TESTNET_API_KEY")
        api_secret = os.getenv("TESTNET_SECRET_KEY")
    else:
        api_key    = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_SECRET_KEY")

    # Capital inicial y riesgo
    usdt_amount = args.usdt if args.usdt is not None else float(os.getenv("USDT_AMOUNT", 0))
    risk = args.risk if args.risk is not None else float(os.getenv("RISK", 1.0))

    return {
        "api_key":     api_key,
        "api_secret":  api_secret,
        "symbol":      args.symbol,
        "interval":    args.interval,
        "usdt_amount": usdt_amount,
        "ma_fast":     args.fast,
        "ma_slow":     args.slow,
        "risk":        risk,
        "testnet":     args.testnet
    }
