import tkinter as tk
from tkinter import messagebox
from typing import Optional
import pandas as pd
from gui.components.top_bar import TopBar

class MainWindow:
    """
    Ventana principal - Orquesta todos los componentes.
    """
    
    def __init__(self, master: tk.Tk, initial_output_path: str):
        self.master = master
        
        # Estado global
        self.shelf_data: Optional[pd.DataFrame] = None
        
        # ==================== Crear componentes ====================
        
        # TopBar: Pasamos callbacks para recibir notificaciones
        self.top_bar = TopBar(
            parent=master,
            initial_output_path=initial_output_path,
            on_file_selected=self._handle_file_selected,
            on_output_changed=self._handle_output_changed
        )
        self.top_bar.grid(row=0, column=0, sticky="ew")
        
        # TODO: Agregar más componentes aquí
        # self.mode_selector = ModeSelector(...)
        # self.data_grid = DataGrid(...)
        # self.control_panel = ControlPanel(...)
    
    # ==================== Handlers (reciben eventos de componentes) ====================
    
    def _handle_file_selected(self, file_path: str):
        """
        Callback: El usuario seleccionó un archivo CSV.
        Carga los datos y actualiza los componentes necesarios.
        """
        try:
            df = pd.read_csv(file_path)
            df['CODIGO'] = df['CODIGO'].astype(str).str.strip()
            self.shelf_data = df
            
            messagebox.showinfo("Información", "Archivo cargado correctamente.")
            
            # TODO: Habilitar filas en DataGrid
            # self.data_grid.enable_all_rows()
            
        except Exception as e:
            messagebox.showwarning("Advertencia", f"Error al cargar: {e}")
            self.shelf_data = None
    
    def _handle_output_changed(self, folder_path: str):
        """
        Callback: El usuario cambió la carpeta de salida.
        """
        # Por ahora solo guardamos la referencia
        # La carpeta se obtiene con self.top_bar.get_output_path() al generar
        pass