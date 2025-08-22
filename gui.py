import tkinter
import customtkinter as ctk
from tkinter import messagebox
import queue
from PIL import Image
import sys
import os

# Importaciones de nuestro proyecto
import config
from analisis import analizar_trades_para_gui
from main import Bot

# Importaciones para el gráfico de Matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- CLASE PARA TOOLTIPS ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(tw, text=self.text, corner_radius=5, fg_color="#333333", text_color="#FFFFFF")
        label.pack(ipadx=5, ipady=3)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

# --- FUNCIÓN PARA RUTAS DE RECURSOS ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Configuración de la Apariencia ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
BINANCE_YELLOW = "#F0B90B"

TOOLTIP_TEXTS = {
    "api_key": "Tu clave API pública de Binance.",
    "api_secret": "Tu clave API secreta de Binance. Trátala como una contraseña.",
    "symbol": "El par de mercado a operar. Ejemplo: BTCUSDT, ETHUSDT.",
    "interval": "La temporalidad de las velas para la estrategia. '1h' = 1 hora.",
    "usdt_amount": "La cantidad de capital en USDT que el bot usará por operación.",
    "risk": "El porcentaje del capital a arriesgar en una sola operación. Ejemplo: 1 para 1%.",
    "trailing_stop": "El porcentaje de caída desde el precio máximo para activar la venta. Ejemplo: 2 para 2%.",
    "testnet": "Activa el modo de prueba (Paper Trading). No se usará dinero real.",
    "ma_fast": "El periodo de la media móvil rápida. Ejemplo: 10.",
    "ma_slow": "El periodo de la media móvil lenta. Ejemplo: 50."
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Binance Trading Bot")
        self.geometry("800x700")
        self.iconbitmap(resource_path('logo.ico'))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.tab_view = ctk.CTkTabview(self, fg_color="#2B2B2B")
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Bot")
        self.tab_view.add("Análisis")
        self.tab_view.add("Configuración")
        self.crear_widgets_bot(self.tab_view.tab("Bot"))
        self.crear_widgets_analisis(self.tab_view.tab("Análisis"))
        self.crear_widgets_configuracion(self.tab_view.tab("Configuración"))
        self.log_queue = queue.Queue()
        self.bot = Bot(log_queue=self.log_queue)
        self.load_config_to_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.procesar_cola_logs)

    def crear_widgets_bot(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)
        logo_image = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(48, 48))
        logo_label = ctk.CTkLabel(top_frame, image=logo_image, text="")
        logo_label.grid(row=0, column=0, rowspan=2, padx=(0, 20))
        self.status_label = ctk.CTkLabel(top_frame, text="Estado: Detenido", font=ctk.CTkFont(size=18, weight="bold"))
        self.status_label.grid(row=0, column=1, sticky="w")
        control_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        control_frame.grid(row=1, column=1, sticky="w", pady=(5,0))
        self.start_button = ctk.CTkButton(control_frame, text="Iniciar Bot", command=self.iniciar_bot, fg_color=BINANCE_YELLOW, text_color="#000000", hover_color="#D9A60A")
        self.start_button.pack(side="left", padx=(0, 5))
        self.stop_button = ctk.CTkButton(control_frame, text="Detener Bot", command=self.detener_bot, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        log_frame = ctk.CTkFrame(tab, fg_color="#1C1C1C")
        log_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_area = ctk.CTkTextbox(log_frame, wrap=tkinter.WORD, state='disabled', fg_color="transparent")
        self.log_area.pack(fill="both", expand=True, padx=10, pady=10)

    def crear_widgets_analisis(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        self.run_analysis_button = ctk.CTkButton(tab, text="Ejecutar Análisis de Trades", command=self.ejecutar_analisis, fg_color=BINANCE_YELLOW, text_color="#000000", hover_color="#D9A60A")
        self.run_analysis_button.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        self.results_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.results_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame = ctk.CTkFrame(self.results_frame, fg_color="#1C1C1C")
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.summary_text = ctk.CTkTextbox(self.results_frame, wrap=tkinter.WORD, height=150, state='disabled', fg_color="#1C1C1C")
        self.summary_text.grid(row=1, column=0, sticky="ew", pady=(10,0))

    def crear_widgets_configuracion(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        self.config_entries = {}
        
        api_frame = ctk.CTkFrame(tab, fg_color="transparent")
        api_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        api_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(api_frame, text="API de Binance", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))
        self.config_entries['api_key'] = self._crear_campo_config(api_frame, "API Key", 1, tooltip=TOOLTIP_TEXTS['api_key'])
        self.config_entries['api_secret'] = self._crear_campo_config(api_frame, "API Secret", 2, show="*", tooltip=TOOLTIP_TEXTS['api_secret'])

        market_frame = ctk.CTkFrame(tab, fg_color="transparent")
        market_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        market_frame.grid_columnconfigure(1, weight=1)
        market_frame.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(market_frame, text="Mercado y Estrategia", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,10))
        self.config_entries['symbol'] = self._crear_campo_config(market_frame, "Símbolo", 1, col=0, tooltip=TOOLTIP_TEXTS['symbol'])
        self.config_entries['interval'] = self._crear_campo_config(market_frame, "Intervalo", 1, col=2, options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], tooltip=TOOLTIP_TEXTS['interval'])
        self.config_entries['ma_fast'] = self._crear_campo_config(market_frame, "MA Rápida", 2, col=0, tooltip=TOOLTIP_TEXTS['ma_fast'])
        self.config_entries['ma_slow'] = self._crear_campo_config(market_frame, "MA Lenta", 2, col=2, tooltip=TOOLTIP_TEXTS['ma_slow'])

        risk_frame = ctk.CTkFrame(tab, fg_color="transparent")
        risk_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        risk_frame.grid_columnconfigure(1, weight=1)
        risk_frame.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(risk_frame, text="Gestión de Riesgo", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,10))
        self.config_entries['usdt_amount'] = self._crear_campo_config(risk_frame, "Capital (USDT)", 1, col=0, tooltip=TOOLTIP_TEXTS['usdt_amount'])
        self.config_entries['risk'] = self._crear_campo_config(risk_frame, "Riesgo por Trade (%)", 1, col=2, tooltip=TOOLTIP_TEXTS['risk'])
        self.config_entries['trailing_stop'] = self._crear_campo_config(risk_frame, "Trailing Stop (%)", 2, col=0, tooltip=TOOLTIP_TEXTS['trailing_stop'])

        other_frame = ctk.CTkFrame(tab, fg_color="transparent")
        other_frame.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        label_testnet = ctk.CTkLabel(other_frame, text="Testnet (Paper Trading)")
        label_testnet.pack(side="left")
        Tooltip(label_testnet, TOOLTIP_TEXTS['testnet'])
        self.config_entries['testnet'] = ctk.CTkSwitch(other_frame, text="")
        self.config_entries['testnet'].pack(side="left", padx=10)

        self.save_button = ctk.CTkButton(tab, text="Guardar Configuración", command=self.save_config_from_ui, fg_color=BINANCE_YELLOW, text_color="#000000", hover_color="#D9A60A")
        self.save_button.grid(row=4, column=0, padx=20, pady=20, sticky="w")
        self.save_status_label = ctk.CTkLabel(tab, text="")
        self.save_status_label.grid(row=4, column=0, padx=(200, 0), pady=20, sticky="w")

    def _crear_campo_config(self, master, label, row, col=0, show=None, options=None, tooltip=None):
        label_widget = ctk.CTkLabel(master, text=label)
        label_widget.grid(row=row, column=col, sticky="w", padx=(0,10))
        if tooltip:
            Tooltip(label_widget, tooltip)
        
        if options:
            entry = ctk.CTkOptionMenu(master, values=options)
        else:
            entry = ctk.CTkEntry(master, show=show)
        entry.grid(row=row, column=col+1, sticky="ew", padx=(0, 20))
        return entry

    def load_config_to_ui(self):
        cfg = config.load_config()
        for key, widget in self.config_entries.items():
            value = cfg.get(key)
            if key in ['risk', 'trailing_stop']:
                value = float(value) * 100
            
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, tkinter.END)
                widget.insert(0, str(value))
            elif isinstance(widget, ctk.CTkOptionMenu):
                widget.set(str(value))
            elif isinstance(widget, ctk.CTkSwitch):
                if value: widget.select()
                else: widget.deselect()

    def save_config_from_ui(self):
        new_cfg = {}
        try:
            for key, widget in self.config_entries.items():
                if isinstance(widget, ctk.CTkEntry):
                    new_cfg[key] = widget.get()
                elif isinstance(widget, ctk.CTkOptionMenu):
                    new_cfg[key] = widget.get()
                elif isinstance(widget, ctk.CTkSwitch):
                    new_cfg[key] = bool(widget.get())
            
            new_cfg['usdt_amount'] = float(new_cfg['usdt_amount'])
            new_cfg['risk'] = float(new_cfg['risk']) / 100.0
            new_cfg['trailing_stop'] = float(new_cfg['trailing_stop']) / 100.0
            new_cfg['ma_fast'] = int(new_cfg['ma_fast'])
            new_cfg['ma_slow'] = int(new_cfg['ma_slow'])

            success, msg = config.save_config(new_cfg)
            if success:
                self.save_status_label.configure(text="¡Guardado!", text_color="#00A765")
            else:
                self.save_status_label.configure(text=f"Error: {msg}", text_color="#FF5252")
        except (ValueError, TypeError):
            self.save_status_label.configure(text="Error: Revisa los valores numéricos.", text_color="#FF5252")
        except Exception as e:
            self.save_status_label.configure(text=f"Error inesperado: {e}", text_color="#FF5252")
        self.after(3000, lambda: self.save_status_label.configure(text=""))

    def set_config_state(self, state):
        for widget in self.config_entries.values():
            widget.configure(state=state)
        self.save_button.configure(state=state)

    def iniciar_bot(self):
        self.set_config_state("disabled")
        self.start_button.configure(state="disabled")
        self.run_analysis_button.configure(state="disabled")
        self.bot.start()
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="Estado: Corriendo")

    def detener_bot(self):
        self.log_message("Enviando señal de detención...")
        self.bot.stop()
        self.stop_button.configure(state="disabled")

    def procesar_cola_logs(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_message(message)
                if "Bucle del bot detenido." in message or "Finalizando el bot" in message:
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.status_label.configure(text="Estado: Detenido")
                    self.run_analysis_button.configure(state="normal")
                    self.set_config_state("normal")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.procesar_cola_logs)

    def on_closing(self):
        if self.bot.bot_thread and self.bot.bot_thread.is_alive():
            if messagebox.askyesno("Salir", "El bot está corriendo. ¿Estás seguro de que quieres salir?", icon='warning'):
                self.detener_bot()
                self.destroy()
        else:
            self.destroy()
    
    def ejecutar_analisis(self):
        self.log_message("Ejecutando análisis...")
        self.run_analysis_button.configure(state="disabled")
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', tkinter.END)
        try:
            fig, summary = analizar_trades_para_gui(dark_mode=True)
            if fig:
                self.mostrar_grafico(fig)
                self.summary_text.insert(tkinter.END, summary)
                self.log_message("Análisis finalizado con éxito.")
            else:
                self.summary_text.insert(tkinter.END, summary)
                self.log_message(f"Aviso de análisis: {summary}")
        except Exception as e:
            error_msg = f"Ocurrió un error inesperado durante el análisis: {e}"
            self.log_message(error_msg)
            self.summary_text.insert(tkinter.END, error_msg)
        finally:
            self.summary_text.configure(state='disabled')
            if "Corriendo" not in self.status_label.cget("text"):
                self.run_analysis_button.configure(state="normal")

    def mostrar_grafico(self, fig):
        fig.set_facecolor("#1C1C1C")
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

    def log_message(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tkinter.END, message + '\n')
        self.log_area.configure(state='disabled')
        self.log_area.see(tkinter.END)

if __name__ == "__main__":
    app = App()
    app.mainloop()
