# config.py
import json
import os

CONFIG_FILE = "config.json"

def get_default_config():
    """Devuelve un diccionario con la configuración por defecto."""
    return {
        "api_key": "",
        "api_secret": "",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "usdt_amount": 1000.0,
        "risk": 0.01,
        "trailing_stop": 0.02,
        "testnet": True,
        "ma_fast": 10,
        "ma_slow": 50
    }

def load_config():
    """
    Carga la configuración desde config.json.
    Si no existe, crea el archivo con valores por defecto.
    """
    if not os.path.exists(CONFIG_FILE):
        print(f"No se encontró {CONFIG_FILE}, creando uno nuevo con valores por defecto.")
        default_config = get_default_config()
        save_config(default_config)
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Asegurarse de que todas las claves necesarias están presentes
        default_keys = get_default_config().keys()
        missing_keys = [key for key in default_keys if key not in config]
        if missing_keys:
            print(f"Advertencia: Faltan claves en {CONFIG_FILE}: {missing_keys}. Se añadirán con valores por defecto.")
            default_config = get_default_config()
            for key in missing_keys:
                config[key] = default_config[key]
            save_config(config)

        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer {CONFIG_FILE}: {e}. Se usará la configuración por defecto.")
        return get_default_config()

def save_config(config_data):
    """Guarda el diccionario de configuración en config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True, f"Configuración guardada en {CONFIG_FILE}"
    except IOError as e:
        return False, f"Error al guardar la configuración: {e}"