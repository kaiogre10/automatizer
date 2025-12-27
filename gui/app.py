import tkinter as tk
import sys
import os
from gui.main_window import MainWindow
from config.config_loader import conf  # <--- IMPORTAR

def get_application_path() -> str:
    """Obtiene la ruta de la aplicación (compatible con PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def main():
    root = tk.Tk()
    
    # Usar valores del YAML
    app_name = conf.get("app.name", "Generador de Etiquetas")
    root.title(app_name)
    
    # Configurar tamaño desde YAML
    w = conf.get("app.window.width", 650)
    h = conf.get("app.window.height", 480)
    
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (ws / 2) - (w / 2), (hs / 2) - (h / 2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    resizable = conf.get("app.window.resizable", True)
    root.resizable(resizable, resizable)
    
    root.rowconfigure(3, weight=1)
    root.columnconfigure(0, weight=1)
    
    app_path = get_application_path()
    # Usar nombre de carpeta por defecto del YAML
    folder_name = conf.get("paths.output.default_folder", "formato_etiquetas")
    default_output = os.path.join(app_path, folder_name)
    
    # Crear ventana principal
    MainWindow(root, initial_output_path=default_output)
    
    root.mainloop()