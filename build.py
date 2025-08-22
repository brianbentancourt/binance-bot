# build.py
import subprocess
import os
import platform

if __name__ == "__main__":
    print("Iniciando el proceso de compilación...")

    main_script = "gui.py"
    exe_name = "BinanceBot"
    icon_path = "logo.ico"

    # Opciones de PyInstaller
    pyinstaller_options = [
        "--noconfirm",
        "--onefile",      # Crear un solo ejecutable
        "--windowed",     # Sin consola de fondo al ejecutar la GUI
        f"--name={exe_name}",
    ]

    if icon_path and os.path.exists(icon_path):
        pyinstaller_options.append(f"--icon={icon_path}")

    # Archivos de datos que deben incluirse. PyInstaller los buscará y añadirá.
    # El separador es ':' para todas las plataformas según la documentación de PyInstaller.
    data_to_add = [
        "config.py",
        "strategy.py",
        "logger.py",
        ".env",
        "logo.png",
        "logo.ico"
    ]

    for data_file in data_to_add:
        if os.path.exists(data_file):
            print(f"Añadiendo archivo de datos: {data_file}")
            pyinstaller_options.append(f"--add-data={data_file}:.")
        else:
            print(f"Advertencia: No se encontró el archivo opcional '{data_file}'. No se incluirá.")

    # --- SOLUCIÓN para el error de 'dateparser' ---
    # PyInstaller no encuentra los datos de esta librería, hay que añadirla manualmente.
    try:
        import dateparser
        # La ruta a los datos de dateparser
        dateparser_path = os.path.join(os.path.dirname(dateparser.__file__), "data")
        if os.path.exists(dateparser_path):
            print(f"Añadiendo datos de la librería 'dateparser' desde: {dateparser_path}")
            # Se usa os.pathsep que es ';' en Windows y ':' en Linux/Mac
            pyinstaller_options.append(f"--add-data={dateparser_path}{os.pathsep}dateparser/data")
    except ImportError:
        print("Advertencia: No se pudo importar 'dateparser'. Si es una dependencia, la compilación podría fallar.")
    # --- FIN DE LA SOLUCIÓN ---

    # Comando completo
    command = ["pyinstaller"] + pyinstaller_options + [main_script]

    print("\nComando de PyInstaller a ejecutar:")
    print(f"==> {' '.join(command)}\n")

    try:
        subprocess.run(command, check=True, shell=True)
        print("\n" + "*"*50)
        print("¡ÉXITO!")
        print(f"El ejecutable se ha creado en: {os.path.join(os.getcwd(), 'dist', f'{exe_name}.exe')}")
        print("*"*50 + "\n")
    except subprocess.CalledProcessError as e:
        print(f"\nError durante la compilación: {e}")
        print("Asegúrate de que todas las dependencias están instaladas correctamente.")
    except FileNotFoundError:
        print("\nError: PyInstaller no está instalado.")
        print("Por favor, instálalo ejecutando: pip install pyinstaller")
