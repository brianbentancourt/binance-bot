# analisis.py
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BINANCE_YELLOW = "#F0B90B"
DARK_BG = "#2B2B2B"
DARK_TEXT = "#EAECEE"

def analizar_trades_para_gui(archivo_csv='trades.csv', dark_mode=False):
    """
    Lee el archivo de trades, calcula el PnL y devuelve un gráfico y un resumen en texto.
    Acepta un parámetro dark_mode para ajustar los colores del gráfico.
    """
    output_summary = []
    
    try:
        df = pd.read_csv(archivo_csv)
    except FileNotFoundError:
        return None, f"Error: No se encontró el archivo '{archivo_csv}'."

    if df.empty or len(df) < 2:
        return None, "No hay suficientes datos en trades.csv para generar un análisis."

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    trades_completados = []
    pnl_total = 0

    for i in range(0, len(df) - 1, 2):
        if i + 1 < len(df):
            compra = df.iloc[i]
            venta = df.iloc[i+1]
            if compra['action'] == 'BUY' and venta['action'] == 'SELL':
                costo_total = compra['cost']
                ingreso_total = venta['price'] * compra['quantity']
                pnl_operacion = ingreso_total - costo_total
                pnl_total += pnl_operacion
                trades_completados.append({
                    'fecha_cierre': venta['timestamp'],
                    'pnl_operacion': pnl_operacion,
                    'pnl_acumulado': pnl_total
                })

    if not trades_completados:
        return None, "No se encontraron operaciones completadas (pares de compra/venta)."

    df_resultados = pd.DataFrame(trades_completados)

    output_summary.append("--- Resumen de Operaciones ---")
    output_summary.append(df_resultados[['fecha_cierre', 'pnl_operacion', 'pnl_acumulado']].round(4).to_string())
    output_summary.append(f"\n\nResultado Final (PnL Total): {df_resultados['pnl_acumulado'].iloc[-1]:.4f} USDT")

    # --- Graficar los resultados ---
    if dark_mode:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 7), facecolor=DARK_BG)
        ax.set_facecolor("#1C1C1C")
        main_color = BINANCE_YELLOW
        text_color = DARK_TEXT
        pnl_pos_color = '#2E7D32' # Verde oscuro
        pnl_neg_color = '#C62828' # Rojo oscuro
        grid_color = '#424242'
    else:
        plt.style.use('ggplot')
        fig, ax = plt.subplots(figsize=(12, 7))
        main_color = 'royalblue'
        text_color = 'black'
        pnl_pos_color = 'green'
        pnl_neg_color = 'red'
        grid_color = None # Estilo por defecto

    ax.plot(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 
            marker='o', linestyle='-', color=main_color, label='PnL Acumulado')

    ax.fill_between(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 0,
                    where=(df_resultados['pnl_acumulado'] >= 0), 
                    facecolor=pnl_pos_color, alpha=0.5, interpolate=True)
    ax.fill_between(df_resultados['fecha_cierre'], df_resultados['pnl_acumulado'], 0,
                    where=(df_resultados['pnl_acumulado'] < 0), 
                    facecolor=pnl_neg_color, alpha=0.5, interpolate=True)
    
    ax.axhline(0, color=text_color, linewidth=0.8, linestyle='--', alpha=0.7)
    
    # Formato y etiquetas
    ax.set_title('Evolución del PnL del Bot de Trading', fontsize=16, color=text_color)
    ax.set_ylabel('PnL Acumulado (USDT)', fontsize=12, color=text_color)
    ax.set_xlabel('Fecha de Operación', fontsize=12, color=text_color)
    
    ax.tick_params(axis='x', colors=text_color)
    ax.tick_params(axis='y', colors=text_color)
    ax.spines['bottom'].set_color(text_color)
    ax.spines['top'].set_color(text_color) 
    ax.spines['right'].set_color(text_color)
    ax.spines['left'].set_color(text_color)
    if grid_color: ax.grid(color=grid_color)

    formatter = mticker.FormatStrFormatter('$%1.2f')
    ax.yaxis.set_major_formatter(formatter)
    
    fig.autofmt_xdate()
    fig.tight_layout()
    legend = ax.legend()
    plt.setp(legend.get_texts(), color=text_color)

    return fig, "\n".join(output_summary)

def analizar_trades(archivo_csv='trades.csv'):
    """Función original que muestra el gráfico y el resumen en la consola."""
    fig, summary = analizar_trades_para_gui(archivo_csv, dark_mode=False)
    if fig:
        print(summary)
        plt.show()
    else:
        print(summary)

if __name__ == "__main__":
    analizar_trades()