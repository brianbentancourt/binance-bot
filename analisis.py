# analisis.py
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def analizar_trades(archivo_csv='trades.csv'):
    """
    Lee el archivo de trades, calcula el PnL por operación y grafica el PnL acumulado.
    """
    try:
        df = pd.read_csv(archivo_csv)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo_csv}'. Asegúrate de que está en la misma carpeta.")
        return

    # Asegurarse de que la columna de timestamp sea del tipo datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    trades_completados = []
    pnl_total = 0

    # Iterar por el dataframe para emparejar compras con ventas
    for i in range(0, len(df) - 1, 2):
        compra = df.iloc[i]
        venta = df.iloc[i+1]

        # Asegurarse de que estamos emparejando una COMPRA con una VENTA
        if compra['action'] == 'BUY' and venta['action'] == 'SELL':
            costo_total = compra['cost']
            
            # Para las ventas OCO, el 'revenue' no está en el CSV, así que lo calculamos
            ingreso_total = venta['price'] * compra['quantity'] # Usamos la cantidad de la compra para mayor precisión
            
            pnl_operacion = ingreso_total - costo_total
            pnl_total += pnl_operacion

            trades_completados.append({
                'fecha_cierre': venta['timestamp'],
                'pnl_operacion': pnl_operacion,
                'pnl_acumulado': pnl_total
            })

    if not trades_completados:
        print("No se encontraron operaciones completadas (pares de compra/venta) para analizar.")
        return

    # Crear un nuevo DataFrame con los resultados
    df_resultados = pd.DataFrame(trades_completados)

    print("--- Resumen de Operaciones ---")
    print(df_resultados[['fecha_cierre', 'pnl_operacion', 'pnl_acumulado']].round(4))
    print("\n---------------------------------")
    print(f"Resultado Final (PnL Total): {df_resultados['pnl_acumulado'].iloc[-1]:.4f} USDT")
    print("---------------------------------")


    # --- Graficar los resultados ---
    # CORRECCIÓN: Cambiado a un estilo más compatible como 'ggplot'
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(12, 7))

    # Graficar la línea de PnL acumulado
    ax.plot(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 
            marker='o', linestyle='-', color='royalblue', label='PnL Acumulado')

    # Rellenar el área bajo la curva para un mejor efecto visual
    ax.fill_between(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 0,
                    where=(df_resultados['pnl_acumulado'] >= 0), 
                    facecolor='green', alpha=0.3, interpolate=True)
    ax.fill_between(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 0,
                    where=(df_resultados['pnl_acumulado'] < 0), 
                    facecolor='red', alpha=0.3, interpolate=True)
    
    # Línea horizontal en cero para referencia
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

    # Formato y etiquetas
    ax.set_title('Evolución del PnL del Bot de Trading', fontsize=16)
    ax.set_ylabel('PnL Acumulado (USDT)', fontsize=12)
    ax.set_xlabel('Fecha de Operación', fontsize=12)
    
    # Formatear el eje Y para que muestre el símbolo de dólar
    formatter = mticker.FormatStrFormatter('$%1.2f')
    ax.yaxis.set_major_formatter(formatter)
    
    plt.xticks(rotation=45)
    plt.tight_layout() # Ajusta el layout para que no se corten las etiquetas
    plt.legend()
    plt.show()


if __name__ == "__main__":
    analizar_trades()