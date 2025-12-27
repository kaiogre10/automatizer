import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional

class TopBar(tk.Frame):
    """
    Componente de barra superior.
    Contiene: selector de archivo de entrada y carpeta de salida.
    
    Callbacks:
        - on_file_selected: Se llama cuando el usuario selecciona un archivo CSV
        - on_output_changed: Se llama cuando el usuario cambia la carpeta de salida
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        initial_output_path: str = "",
        on_file_selected: Optional[Callable[[str], None]] = None,
        on_output_changed: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent, padx=10, pady=10)
        
        # Callbacks (los pasa MainWindow)
        self._on_file_selected = on_file_selected
        self._on_output_changed = on_output_changed
        
        # Variables internas
        self._input_path_var = tk.StringVar(value="")
        self._output_path_var = tk.StringVar(value=initial_output_path)
        
        # Construir UI
        self._build_ui()
    
    def _build_ui(self):
        # --- Sección: Cargar archivo ---
        tk.Label(self, text="Cargar archivo:", font=('Arial', 9)).pack(side="left")
        
        tk.Entry(
            self,
            textvariable=self._input_path_var,
            width=15,
            state="readonly"
        ).pack(side="left", padx=1)
        
        tk.Button(
            self,
            text="📂",
            command=self._handle_select_file
        ).pack(side="left", padx=1)
        
        # --- Espaciador flexible ---
        tk.Label(self, text="  ").pack(side="left", expand=True)
        
        # --- Sección: Carpeta de salida ---
        tk.Label(self, text="Carpeta de salida:", font=('Arial', 9)).pack(side="left")
        
        tk.Entry(
            self,
            textvariable=self._output_path_var,
            width=15,
            state="readonly"
        ).pack(side="left", padx=5)
        
        tk.Button(
            self,
            text="📂",
            command=self._handle_select_output
        ).pack(side="left", padx=5)
    
    # ==================== Handlers internos ====================
    
    def _handle_select_file(self):
        """Abre diálogo para seleccionar archivo CSV."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de frescuras",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self._input_path_var.set(file_path)
            # Notificar a MainWindow via callback
            if self._on_file_selected:
                self._on_file_selected(file_path)
    
    def _handle_select_output(self):
        """Abre diálogo para seleccionar carpeta de salida."""
        folder = filedialog.askdirectory()
        if folder:
            self._output_path_var.set(folder)
            # Notificar a MainWindow via callback
            if self._on_output_changed:
                self._on_output_changed(folder)
    
    # ==================== Métodos públicos ====================
    
    def get_input_path(self) -> str:
        """Retorna la ruta del archivo de entrada seleccionado."""
        return self._input_path_var.get()
    
    def get_output_path(self) -> str:
        """Retorna la ruta de la carpeta de salida."""
        return self._output_path_var.get()
    
    def set_output_path(self, path: str):
        """Establece la ruta de salida programáticamente."""
        self._output_path_var.set(path)