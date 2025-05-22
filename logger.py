import csv
import os
from datetime import datetime

LOG_FILE = os.getenv("LOG_FILE", "trades.csv")

# Inicializa CSV con cabeceras si no existe
if not os.path.isfile(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "action", "symbol", "price", "quantity", "cost", "revenue", "pnl"])


def log_trade(action, symbol, price, quantity, cost=None, revenue=None, pnl=None):
    ts = datetime.utcnow().isoformat()
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([ts, action, symbol, price, quantity, cost or "", revenue or "", pnl or ""])