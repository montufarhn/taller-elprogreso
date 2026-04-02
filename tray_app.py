import os
import subprocess
import sys
import time
import webbrowser
from threading import Thread
from pystray import Icon, Menu, MenuItem
from PIL import Image

# --- Configuration ---
SERVER_EXE_NAME = "main.exe"  # Nombre del ejecutable del servidor FastAPI empaquetado
INDEX_HTML_NAME = "index.html"   # Nombre del archivo HTML del frontend
APP_ICON_NAME = "Logo.ico"       # Cambiado a .ico para coincidir con el instalador
SERVER_PORT = 8000          # Puerto donde se ejecuta el servidor FastAPI
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
APP_TITLE = "Taller Pro Auto"

server_process = None
tray_icon = None

# Determina la ruta base para los archivos empaquetados o instalados
def get_base_path():
    if getattr(sys, 'frozen', False):
        # Ejecutándose como un paquete de PyInstaller, usa el directorio del ejecutable
        return os.path.dirname(sys.executable)
    else:
        # Ejecutándose como un script Python
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

def start_server():
    global server_process
    if server_process and server_process.poll() is None:
        print("Server is already running.")
        return

    print(f"Starting server: {SERVER_EXE_NAME}")
    server_path = os.path.join(BASE_PATH, SERVER_EXE_NAME)
    
    if not os.path.exists(server_path):
        print(f"Error: Server executable not found at {server_path}")
        return

    try:
        # Inicia el servidor como un proceso separado, sin ventana de consola
        server_process = subprocess.Popen(
            [server_path],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
            stdout=subprocess.PIPE, # Redirige stdout para evitar consola
            stderr=subprocess.PIPE  # Redirige stderr para evitar consola
        )
        print(f"Server started with PID: {server_process.pid}")
        # Dale un momento al servidor para que se inicie
        time.sleep(3) 
    except Exception as e:
        print(f"Failed to start server: {e}")
        server_process = None

def stop_server():
    global server_process
    if server_process and server_process.poll() is None:
        print(f"Stopping server with PID: {server_process.pid}")
        try:
            server_process.terminate()
            server_process.wait(timeout=5) # Espera a que termine
            print("Server stopped.")
        except subprocess.TimeoutExpired:
            print("Server did not terminate gracefully, killing it.")
            server_process.kill()
            server_process.wait()
        except Exception as e:
            print(f"Error stopping server: {e}")
        finally:
            server_process = None
    else:
        print("Server is not running.")

def open_browser(icon, item):
    print(f"Opening browser to {SERVER_URL}/{INDEX_HTML_NAME}")
    webbrowser.open(f"{SERVER_URL}/{INDEX_HTML_NAME}")

def restart_server(icon, item):
    print("Restarting server...")
    stop_server()
    start_server()
    open_browser(icon, item)

def exit_app(icon, item):
    print("Exiting application...")
    stop_server()
    icon.stop()
    sys.exit(0)

def setup_tray_icon():
    global tray_icon
    
    icon_path = os.path.join(BASE_PATH, APP_ICON_NAME)
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}. Using default.")
        image = Image.new('RGB', (64, 64), color = 'red') # Imagen de respaldo
    else:
        image = Image.open(icon_path)

    menu = (
        MenuItem(f"Abrir {APP_TITLE}", open_browser),
        MenuItem("Reiniciar Servidor", restart_server),
        MenuItem("Salir", exit_app)
    )

    tray_icon = Icon(APP_TITLE, image, APP_TITLE, menu)
    tray_icon.run()

if __name__ == "__main__":
    server_thread = Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(5) 
    
    webbrowser.open(f"{SERVER_URL}/{INDEX_HTML_NAME}")

    setup_tray_icon()