# Trading Bot BTC/USDT

Este proyecto es un **bot de trading** en Python que opera sobre el par **BTC/USDT** en Binance, con estrategia de cruce de medias móviles, registro de operaciones en CSV, soporte para entorno de pruebas (Testnet), parámetro de riesgo y fácil despliegue en local, Docker o VPS.

---

## 📁 Estructura del proyecto

```
trading-bot/
├── main.py           # Loop principal y lógica del bot
├── config.py         # Carga de configuración y variables de entorno/CLI
├── strategy.py       # Estrategia de trading (MA Crossover)
├── logger.py         # Registro de operaciones en trades.csv
├── requirements.txt  # Dependencias Python
└── Dockerfile        # Instrucciones para construir imagen Docker
```

> **Nota:** Al ejecutar el bot por primera vez se generará `trades.csv` en la raíz del proyecto.

---

## 🛠️ Configuración de Binance

Para **Spot real**:

1. Inicia sesión en tu cuenta de Binance y ve a **Perfil → Gestión de API**.
2. Crea una nueva API Key (por ejemplo, “Trading-Bot”) y copia los valores:

   * `BINANCE_API_KEY`
   * `BINANCE_SECRET_KEY`
3. Habilita permisos de **Enable Spot & Margin Trading**. Si solo operas Spot, desactiva permisos de Futures.
4. (Opcional) En **IP Access Restriction**, añade la IP de tu servidor para mayor seguridad o deja sin restricción durante las pruebas.
5. Deposita USDT en tu billetera Spot: **Wallet → Billetera Spot → Deposit → USDT**.

Para **Testnet**:

1. Regístrate en [Binance Testnet](https://testnet.binance.vision/) con tu correo.
2. En Testnet Dashboard, ve a **API Keys → Create API Key** y copia:

   * `TESTNET_API_KEY`
   * `TESTNET_SECRET_KEY`
3. Ejecuta el bot con el flag `--testnet` para usar estas credenciales y el entorno de pruebas.

---

## ⚙️ Requisitos

* Python 3.9+ instalado
* Cuenta de Binance para trading real (Spot) y/o cuenta en Testnet
* API Key y Secret Key (reales y/o Testnet)
* (Opcional) Docker para contenedor
* (Recomendado) `python-dotenv` para gestión de variables de entorno

---

## 🔐 Variables de entorno (.env)

Crea un archivo `.env` en la raíz con las siguientes variables:

```dotenv
# Claves para trading real (Spot)
BINANCE_API_KEY=tu_api_key_real
BINANCE_SECRET_KEY=tu_secret_key_real

# Claves para entorno de pruebas (Testnet)
TESTNET_API_KEY=tu_api_key_testnet
TESTNET_SECRET_KEY=tu_secret_key_testnet

# Capital inicial en USDT que el bot usará para operar
USDT_AMOUNT=300

# Fracción del capital a invertir en cada operación (0.1 = 10%; por defecto 1.0)
RISK=1.0

# (Opcional) Nombre de archivo CSV de logs
# LOG_FILE=mis_trades.csv
```

> **Importante:** Añade `.env` a tu `.gitignore` para no subirlo al repositorio.

---

## 🚀 Uso local

Instalación de dependencias:

```bash
pip install -r requirements.txt
pip install python-dotenv
```

Ejecuta el bot con tus parámetros (por defecto `BTCUSDT`, intervalo `1m`, MA rápida=10, MA lenta=50, riesgo=100%):

```bash
python main.py [--testnet] --interval 1m --fast 10 --slow 50 --risk 0.1
```

* `--testnet`: activa el entorno de pruebas (usa `TESTNET_API_KEY/SECRET`).
* `--interval`: intervalo de velas (`1m`, `5m`, `15m`, etc.).
* `--fast` / `--slow`: periodos de medias móviles.
* `--risk`: fracción de USDT a invertir por trade (p.ej. `0.1` = 10%).

El bot:

* Obtiene velas cada intervalo
* Compra (BUY) cuando MA rápida cruza por encima de MA lenta
* Vende (SELL) cuando MA rápida cruza por debajo de MA lenta
* Usa solo el porcentaje de capital definido en `--risk`
* Registra cada orden en `trades.csv`

---

## 🐳 Uso con Docker

1. Construye la imagen:

   ```bash
   docker build -t trading-bot .
   ```

2. Ejecuta el contenedor leyendo `.env`:

   ```bash
   docker run -d \
     --name bot-trading \
     --env-file .env \
     trading-bot --testnet --interval 1m --fast 10 --slow 50 --risk 0.1
   ```

> Ajusta los flags según quieras entorno real o Testnet.

---

## ☁️ Despliegue en servidores / VPS

### Opciones de despliegue

* **VPS/Droplet** (DigitalOcean, Vultr, AWS Lightsail): instala Docker o Python y sigue las secciones anteriores.
* **Oracle Cloud Always Free**: crea instancia ARM, instala Docker y despliega contenedor.
* **Cloud Run / Fargate / ECS**: construye imagen, sube a registry y configura servicio.

### Puntos a considerar

* Usa el flag `--testnet` solo en desarrollo/pruebas.
* En producción, asegúrate de usar `BINANCE_API_KEY/SECRET` y no exponer tu `.env`.

---

## 📈 Estrategia por defecto

### MovingAverageCrossover

* **MA rápida**: periodo por defecto `--fast` (10)
* **MA lenta**: periodo por defecto `--slow` (50)
* **Señal BUY**: MA rápida > MA lenta
* **Señal SELL**: MA rápida < MA lenta

Puedes crear nuevas estrategias en `strategy.py` y seleccionarlas modificando `main.py`.

---

## 📝 Logging de operaciones

El archivo `trades.csv` (o el indicado en `LOG_FILE`) contiene:

| timestamp           | action | symbol  | price    | quantity | cost   | revenue | pnl  |
| ------------------- | ------ | ------- | -------- | -------- | ------ | ------- | ---- |
| 2025-05-22T12:00:00 | BUY    | BTCUSDT | 56000.00 | 0.005358 | 300.00 |         |      |
| 2025-05-22T13:15:00 | SELL   | BTCUSDT | 56500.00 | 0.005358 |        | 303.12  | 3.12 |

> Cada fila registra fecha UTC, tipo de operación, precio, cantidad, costo, revenue y PnL.

---

## 🤝 Contribuciones

1. Haz un *fork* de este repositorio.
2. Crea una rama: `git checkout -b feature/mi-mejora`.
3. Envía un *pull request* describiendo cambios.

---

## ⚖️ Licencia

Este proyecto está bajo licencia MIT. Consulta `LICENSE.md` para más detalles.

---

**¡Todo listo!** Ahora tienes instrucciones para usar tu bot con riesgo parametrizable, Spot real y Testnet, configurar, ejecutar y desplegar.
