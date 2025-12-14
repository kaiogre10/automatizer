import tkinter as tk
import sys
from tkinter import messagebox, ttk, filedialog
import logging
import os
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.frescures import Frescurer
from src.barcoder import Barcoder
from services.cache_service import clear_output_folders
from utils.utils import validate_frescures, validate_sku, frescure_to_date

logger = logging.getLogger(__name__)

class AppGeneradorCP:
    def __init__(self, master):
        self.master = master
        
        # --- Configuración de Rutas para PyInstaller ---
        def resource_path(relative_path):
            """ Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller """
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        self.project_root = resource_path(".")
        self.shelf_times_path = resource_path(os.path.join("data", "frescuras.csv"))
        self.template_path = resource_path(os.path.join("data", "plantilla.xlsx"))
        
        # Rutas de salida (fuera del exe)
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.output_path = os.path.join(application_path, "output")
        self.temp_path = os.path.join(application_path, "temp_img")
        
        self.default_output = self.output_path
        self.output_path_var = tk.StringVar(value=self.default_output)

        # --- Datos y Variables ---
        self.shelf_data = self._load_shelf_data()
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|1[0-9]|2[0-9]|3[0-1])[0-9]$')
        self.rows_data: List[Dict[str, Any]] = []
        self.mode_var = tk.StringVar(value="frescuras")

        # ==========================================================
        # SECCIÓN 1: Configuración Superior
        # ==========================================================
        top_frame = tk.Frame(master, padx=10, pady=10)
        top_frame.grid(row=0, column=0, sticky="ew")
        
        tk.Label(top_frame, text="Carpeta Salida:", font=('Arial', 9, 'bold')).pack(side="left")
        tk.Entry(top_frame, textvariable=self.output_path_var, width=35, state="readonly").pack(side="left", padx=5)
        tk.Button(top_frame, text="📂", command=self._select_output_folder).pack(side="left")

        mode_frame = tk.LabelFrame(master, text="Tipo de Documento", padx=10, pady=5)
        mode_frame.grid(row=1, column=0, padx=10, sticky="ew")
        
        tk.Radiobutton(mode_frame, text="Hojas de Consumo ", variable=self.mode_var, value="frescuras", command=self._on_mode_change).pack(side="left", padx=20)
        tk.Radiobutton(mode_frame, text="Códigos de Barra", variable=self.mode_var, value="barcodes", command=self._on_mode_change).pack(side="left", padx=20)

        # ==========================================================
        # SECCIÓN 2: Encabezados
        # ==========================================================
        self.header_frame = tk.Frame(master, bg="#ddd", pady=5)
        self.header_frame.grid(row=2, column=0, padx=10, sticky="ew")
        self.header_frame.columnconfigure(3, weight=1)

        self.W_COL1 = 12
        self.W_COL2 = 12
        self.W_COL3 = 7
        
        tk.Label(self.header_frame, text="SKU", width=self.W_COL1, bg="#ddd", font=('Arial', 9, 'bold')).grid(row=0, column=0)
        tk.Label(self.header_frame, text="Frescura", width=self.W_COL2, bg="#ddd", font=('Arial', 9, 'bold')).grid(row=0, column=1)
        tk.Label(self.header_frame, text="Copias", width=self.W_COL3, bg="#ddd", font=('Arial', 9, 'bold')).grid(row=0, column=2)
        tk.Label(self.header_frame, text="Información", bg="#ddd", font=('Arial', 9, 'bold'), anchor="w").grid(row=0, column=3, sticky="w", padx=10)

        # ==========================================================
        # SECCIÓN 3: Área de Entrada con Scroll (FIXED)
        # ==========================================================

        self.canvas_frame = tk.Frame(master, borderwidth=1, relief="sunken")
        self.canvas_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        self.canvas = tk.Canvas(self.canvas_frame)
        self.scrollbar_y = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)
        
        self.scrollbar_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Frame interno donde van las filas
        self.input_frame = tk.Frame(self.canvas)
        
        # TRUCO DEL SCROLLBAR: Crear ventana en el canvas y vincular el tamaño
        self.canvas_window = self.canvas.create_window((0, 0), window=self.input_frame, anchor="nw")

        # 1. Cuando el input_frame cambie de tamaño (filas nuevas), actualiza la region de scroll
        self.input_frame.bind("<Configure>", self._on_frame_configure)
        # 2. Cuando el canvas cambie de tamaño (resize ventana), ajusta el ancho del input_frame
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bindings para rueda del ratón
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ==========================================================
        # SECCIÓN 4: Botones
        # ==========================================================
        self.control_frame = tk.Frame(master, pady=10)
        self.control_frame.grid(row=4, column=0, sticky="ew", padx=10)

        tk.Button(self.control_frame, text="Añadir Fila", command=self.add_new_row, bg="#e3f2fd").pack(side="left", padx=5)
        tk.Button(self.control_frame, text="Limpiar", command=self._clear_all_rows).pack(side="left", padx=5)
        tk.Button(self.control_frame, text="GENERAR", command=self.execute_generation, bg='#2e7d32', fg='white', font=('Arial', 10, 'bold'), height=2).pack(side="right", padx=10)

        self.add_new_row()

    # --- Métodos de Scrollbar ---
    def _on_frame_configure(self, event):
        """Actualiza la región de scroll cuando el contenido interno cambia."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Ajusta el ancho del frame interno al ancho del canvas."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Scroll con rueda del ratón (solo si hace falta)."""
        if self.canvas.bbox("all")[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # --- Lógica de Negocio ---
    def _load_shelf_data(self) -> pd.DataFrame:
        try:
            if os.path.exists(self.shelf_times_path):
                df = pd.read_csv(self.shelf_times_path)
                df['CODIGO'] = df['CODIGO'].astype(str).str.strip()
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error cargando CSV: {e}")
            return pd.DataFrame()

    def _select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.output_path_var.set(folder)

    def _on_mode_change(self):
        mode = self.mode_var.get()
        # Resetear headers (opcional) y limpiar
        self._clear_all_rows()

    def add_new_row(self):
        row_frame = tk.Frame(self.input_frame)
        row_frame.pack(fill="x", pady=2)
        
        entry_sku = tk.Entry(row_frame, width=self.W_COL1 + 2)
        entry_sku.grid(row=0, column=0, padx=2)
        
        entry_frescura = tk.Entry(row_frame, width=self.W_COL2 + 2)
        entry_frescura.grid(row=0, column=1, padx=2)
        
        entry_cant = tk.Entry(row_frame, width=self.W_COL3 + 2, justify="center")
        entry_cant.insert(0, "1")
        entry_cant.grid(row=0, column=2, padx=2)
        
        lbl_status = tk.Label(row_frame, text="Ingrese datos", fg="black", anchor="w")
        lbl_status.grid(row=0, column=3, padx=10, sticky="ew")
        
        # Configurar columnas del row_frame para que el status ocupe el resto
        row_frame.columnconfigure(3, weight=1)

        row_data = {'frame': row_frame, 'sku': entry_sku, 'frescura': entry_frescura, 'cantidad': entry_cant, 'status': lbl_status}
        
        # Bindings para cálculo en tiempo real
        entry_sku.bind("<KeyRelease>", lambda e: self._calculate_preview(row_data))
        entry_frescura.bind("<KeyRelease>", lambda e: self._calculate_preview(row_data))
        
        if self.mode_var.get() == "barcodes":
            entry_frescura.config(state="disabled", bg="#f0f0f0")
        
        self.rows_data.append(row_data)

    def _calculate_preview(self, row):
        """ Lógica para mostrar descripción o cálculo completo """
        mode = self.mode_var.get()
        sku_val = row['sku'].get().strip()
        frescura_val: str = row['frescura'].get().strip().upper()
        status_lbl = row['status']
        
        # Caso base: Vacío
        if not sku_val:
            status_lbl.config(text="Ingresse datos...", fg="gray")
            return
        
        if mode == "barcodes":
            status_lbl.config(text="Ingrese texto para corregir código de barras", fg="gray")
            return

        # 1. Validar SKU numéricamente
        if not validate_sku(sku_val):
            status_lbl.config(text="SKU inválido", fg="red")
            return

        # 2. Buscar en Base de Datos
        match = self.shelf_data.loc[self.shelf_data['CODIGO'] == sku_val]
        
        if match.empty:
            status_lbl.config(text="SKU inexistente", fg="#d32f2f") # Rojo oscuro
            return

        # Obtener Descripción
        descripcion = match.iloc[0]['DESCRIPCION']

        # CASO A: Solo SKU ingresado -> Mostrar solo Descripción
        if not frescura_val:
            status_lbl.config(text=f"{descripcion}", fg="#1976D2") # Azul
            return

        # CASO B: SKU + Frescura -> Validar y Calcular Fechas
        if not validate_frescures(self.frescures_pattern, frescura_val):
            status_lbl.config(text=f"Frescura incorrecta", fg="red")
            return

        fecha_elab_str = frescure_to_date(frescura_val)
        if not fecha_elab_str:
            status_lbl.config(text=f"{descripcion} | Fecha inválida", fg="red")
            return

        try:
            shelf_days = int(match.iloc[0]['SHELF_LIFE'])
            fecha_base = datetime.strptime(fecha_elab_str, "%d/%m/%Y")
            fecha_venc = fecha_base + timedelta(days=shelf_days)
            fecha_venc_str = fecha_venc.strftime("%d/%m/%Y")
            
            # Mensaje Completo
            msg = f"{descripcion} | Lote: {fecha_elab_str} -> Cons. Pref.: {fecha_venc_str}"
            status_lbl.config(text=msg, fg="#3BAB41") # Verde
            
        except Exception as e:
            status_lbl.config(text=f"Error cálculo: {e}", fg="red")

    def _clear_all_rows(self):
        for row in self.rows_data:
            row['frame'].destroy()
        self.rows_data.clear()
        self.add_new_row()

    def execute_generation(self):
        mode = self.mode_var.get()
        output_folder = self.output_path_var.get()
        query = []
        
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except OSError:
                messagebox.showerror("Error", "Ruta de salida inválida.")
                return

        for row in self.rows_data:
            v1 = row['sku'].get().strip()
            v2 = row['frescura'].get().strip()
            cant_str = row['copias'].get().strip()
            
            if not v1: continue 
            
            try:
                cantidad = int(cant_str)
                if cantidad < 1: cantidad = 1
            except: cantidad = 1

            if mode == "frescuras":
                if validate_sku(v1) and validate_frescures(self.frescures_pattern, v2.upper()):
                    # Multiplicar filas (lógica de copias)
                    for _ in range(cantidad):
                        query.append([v1, v2.upper()])
            else:
                query.append([v1, str(cantidad)])

        if not query:
            messagebox.showwarning("Vacío", "No hay datos válidos.")
            return

        try:
            if mode == "frescuras":
                Frescurer(self.shelf_times_path, self.template_path, output_folder, query, self.project_root)
                msg = "Hojas generadas."
            else:
                Barcoder(output_folder, self.temp_path, query, self.project_root)
                msg = "Códigos generados."
            messagebox.showinfo("Éxito", f"{msg}\nEn: {output_folder}")
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))

def main():
    root = tk.Tk()
    root.title("Generador de Etiquetas")
    
    # Centrar ventana
    w, h = 550, 480
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (ws/2) - (w/2), (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    root.resizable(True, True)
    
    # Configurar pesos para que el contenido se expanda
    root.rowconfigure(3, weight=1) 
    root.columnconfigure(0, weight=1)

    AppGeneradorCP(root)
    root.mainloop()

if __name__ == "__main__":
    main()