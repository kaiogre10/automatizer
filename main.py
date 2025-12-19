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
        self.template_path = resource_path(os.path.join("data", "plantilla.xlsx"))
        
        # Rutas de salida (fuera del exe)
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.output_path = os.path.join(application_path, "output")
        self.temp_path = os.path.join(application_path, "temp_img")

        self.output_path_var = tk.StringVar(value=self.output_path)
        self.input_path_var = tk.StringVar(value="")

        # --- Datos y Variables ---
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|1[0-9]|2[0-9]|3[0-1])[0-9]$')
        self.rows_data: List[Dict[str, Any]] = []
        self.mode_var = tk.StringVar(value="frescuras")

        # ==========================================================
        # SECCIÓN 1: Configuración Superior
        # ==========================================================

        top_frame = tk.Frame(master, background="",padx=10, pady=10)
        top_frame.grid(row=0, column=0, sticky="ew")

        tk.Label(top_frame, text="Cargar archivo:", font=('Arial', 9)).pack(side="left")
        tk.Entry(top_frame, textvariable=self.input_path_var, width=15, state="readonly").pack(side="left", padx=1)
        tk.Button(top_frame, text="📂", command=self._select_input_file).pack(side="left", padx=1)

        # Espaciador flexible en el medio
        tk.Label(top_frame, text="  ").pack(side="left", expand=True)

        tk.Label(top_frame, text="Carpeta de salida:", font=('Arial', 9)).pack(side="left")
        tk.Entry(top_frame, textvariable=self.output_path_var, width=15, state="readonly").pack(side="left", padx=5)
        tk.Button(top_frame, text="📂", command=self._select_output_folder).pack(side="left", padx=5)

        mode_frame = tk.LabelFrame(master, text="Tipo de documento:", padx=10, pady=5)
        mode_frame.grid(row=1, column=0, padx=10, sticky="ew")
        
        tk.Radiobutton(mode_frame, text="Hojas de Consumo Preferente", variable=self.mode_var, value="frescuras", command=self._on_mode_change).pack(side="left", padx=20)
        tk.Radiobutton(mode_frame, text="Código de Barras", variable=self.mode_var, value="barcodes", command=self._on_mode_change).pack(side="left", padx=20)
        
        # ==========================================================
        # SECCIÓN 2: Encabezados
        # ==========================================================

        self.header_frame = tk.Frame(master, bg="#ddd", pady=5)
        self.header_frame.grid(row=2, column=0, padx=10, sticky="ew")
        self.header_frame.columnconfigure(4, weight=1)

        self.col_idx = 5
        self.W_COL1 = 10
        self.W_COL2 = 10
        self.W_COL3 = 12
        
        # Columna índice
        self.header_index = tk.Label(self.header_frame, text="Num", width=self.col_idx, bg="#ddd", font=('Arial', 9, 'bold'))
        self.header_index.grid(row=0, column=0)

        # Guardamos referencias a los labels de encabezado
        self.header_sku = tk.Label(self.header_frame, text="SKU", width=self.W_COL1, bg="#ddd", font=('Arial', 9, 'bold'))
        self.header_sku.grid(row=0, column=1)

        self.header_frescura = tk.Label(self.header_frame, text="Frescura", width=self.W_COL2, bg="#ddd", font=('Arial', 9, 'bold'))
        self.header_frescura.grid(row=0, column=2)

        self.header_copias = tk.Label(self.header_frame, text="Copias", width=self.W_COL3, bg="#ddd", font=('Arial', 9, 'bold'))
        self.header_copias.grid(row=0, column=3)

        tk.Label(self.header_frame, text="Info", bg="#ddd", font=('Arial', 9, 'bold'), anchor="w").grid(row=0, column=4, sticky="w", padx=15.0)

        # ==========================================================
        # SECCIÓN 3: Área de Entrada con Scroll
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

        # tk.Button(self.control_frame, text="-", command=self.add_new_row, bg="#e3f2fd").pack(side="left", padx=5)
        # tk.Button(self.control_frame, text="+", command=self.add_new_row, bg="#e3f2fd").pack(side="left", padx=5)
        tk.Button(self.control_frame, text="Añadir Fila", command=self.add_new_row, bg="#e3f2fd").pack(side="left", padx=5)
        tk.Button(self.control_frame, text="Limpiar", command=self._clear_all_rows).pack(side="left", padx=5)
        tk.Button(self.control_frame, text="GENERAR", command=self.execute_generation, bg='#2e7d32', fg='white', font=('Arial', 10, 'bold'), height=2).pack(side="right", padx=10)

        self.add_new_row()

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
            if self.shelf_times_path and os.path.exists(self.shelf_times_path):
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
        # Actualizar encabezados
        if mode == "barcodes":
            self.header_sku.config(text="Texto")
            # Ocultar encabezado de frescura
            self.header_frescura.grid_remove()
        else:
            self.header_sku.config(text="SKU")
            # Mostrar encabezado de frescura
            self.header_frescura.grid()
        # Limpiar filas y crear una nueva con el modo actual
        self._clear_all_rows()
    
    def add_new_row(self):
        row_frame = tk.Frame(self.input_frame)
        row_frame.pack(fill="x", pady=2)

        # Índice de la fila (1‑based)
        row_index = len(self.rows_data) + 1
        self.lbl_index = tk.Label(row_frame, text=str(row_index), width=3, anchor="center")
        self.lbl_index.grid(row=0, column=0, padx=2)
        
        self.entry_sku = tk.Entry(row_frame, width=self.W_COL1 + 2, justify="center")
        self.entry_sku.grid(row=0, column=1, padx=2)
        
        self.entry_frescura = tk.Entry(row_frame, width=self.W_COL2 + 2, justify="center")
        self.entry_frescura.grid(row=0, column=2, padx=2)
        
        # Campo de copias
        self.entry_cant = tk.Entry(row_frame, width=self.W_COL3 + 2, justify="center")
        self.entry_cant.insert(0, 0)
        self.entry_cant.grid(row=0, column=3, padx=(2, 0))

        # Validadores: SKU max 7 chars, Frescura max 4 chars, Copias sólo numérico hasta 2 dígitos
        vc_sku = self.master.register(self._vc_sku)
        vc_fres = self.master.register(self._vc_frescura)
        vc_cop = self.master.register(self._vc_copias)
        self.entry_sku.config(validate='key', validatecommand=(vc_sku, '%P'))
        self.entry_frescura.config(validate='key', validatecommand=(vc_fres, '%P'))
        self.entry_cant.config(validate='key', validatecommand=(vc_cop, '%P'))

        # Botón "-" para restar una copia (mínimo 1)
        btn_menos = tk.Button(
            row_frame,
            text="-",
            width=2,
            command=lambda e=self.entry_cant: self._ajustar_copias(e, -1)
        )
        btn_menos.grid(row=0, column=4, padx=1)

        # Botón "+" para sumar una copia
        btn_mas = tk.Button(
            row_frame,
            text="+",
            width=2,
            command=lambda e=self.entry_cant: self._ajustar_copias(e, +1)
        )
        btn_mas.grid(row=0, column=5, padx=(1, 4))
        
        self.lbl_status = tk.Label(row_frame, text="Ingrese datos", fg="gray", anchor="w", justify="center")
        self.lbl_status.grid(row=0, column=6, padx=10, sticky="ew")
        
        # Configurar columnas del row_frame para que el status ocupe el resto
        row_frame.columnconfigure(6, weight=1)

        row_data: Dict[str, Any] = {
            'frame': row_frame,
            'index_lbl': self.lbl_index,
            'sku': self.entry_sku,
            'frescura': self.entry_frescura,
            'copias': self.entry_cant,
            'status': self.lbl_status
        }
        
        # Bindings para cálculo en tiempo real
        self.entry_sku.bind("<KeyRelease>", lambda e: self._calculate_preview(row_data))
        self.entry_frescura.bind(
            "<KeyRelease>",
            lambda e, r=row_data: (self._force_upper(e.widget), self._calculate_preview(r))
        )
        
        # Ajustar la columna Frescura según el modo
         
        if self.mode_var.get() == "frescuras" and not self.input_path_var.get():
            self.entry_frescura.config(state="readonly", fg="gray", bg=self.canvas_frame.cget("bg"))
            self.entry_sku.config(state="readonly", fg="gray", bg=self.canvas_frame.cget("bg"))
            self.entry_cant.config(state="readonly", fg="gray", bg=self.canvas_frame.cget("bg"))
            self.lbl_status.config(text="NO SE HAN CARGADO FRESCURAS", font="bold", fg="red")

        elif self.mode_var.get() == "barcodes":
            self.entry_frescura.config(state="disabled", width=1, bg=self.canvas_frame.cget("bg"), relief="flat")
            self.entry_frescura.grid_remove()
        else:
            self.entry_frescura.config(state="normal", width=self.W_COL2 + 2, bg="white", relief="sunken")
            self.entry_frescura.grid(row=0, column=2, padx=2)
        
        self.rows_data.append(row_data)

    def _force_upper(self, widget: tk.Entry):
        current = widget.get()
        upper = current.upper()
        if current != upper:
            pos = widget.index(tk.INSERT)
            widget.delete(0, tk.END)
            widget.insert(0, upper)
            widget.icursor(pos)

    def _vc_sku(self, P: str) -> bool:
        """Allow empty or up to 7 characters for SKU."""
        if P is None:
            return False
        return len(P) <= 7 and P.isdigit()

    def _vc_frescura(self, P: str) -> bool:
        """Allow empty or up to 4 characters for frescura."""
        if P is None:
            return False
        return len(P) <= 4

    def _vc_copias(self, P: str) -> bool:
        """Allow empty or numeric string with max 2 digits."""
        if P is None:
            return False
        if P == "":
            return True
        return P.isdigit() and len(P) <= 2

    def _calculate_preview(self, row):
        """ Lógica para mostrar descripción o cálculo completo """
        mode = self.mode_var.get()
        sku_val: str = row['sku'].get().strip()
        frescura_val: str = row['frescura'].get().strip().upper()
        status_lbl = row['status']
         
        # Si estamos en modo frescuras y no hay CSV cargado válido
        if mode == "frescuras" and (self.shelf_data is None or self.shelf_data.empty):
            
            status_lbl.config(text="Cargue primero un archivo CSV válido.", fg="black")
            return
        
        if not sku_val:
            status_lbl.config(text="Ingrese datos", fg="black")
            return
        
        if mode == "barcodes":
            status_lbl.config(text="Ingrese texto para código de barras", fg="black")
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

    def _ajustar_copias(self, entry: tk.Entry, delta: int):
        """Suma o resta copias, manteniendo el valor en el rango 1–50."""
        try:
            val = int(entry.get())
        except ValueError:
            val = 1

        val += delta

        # Limitar entre 1 y 50
        if val < 1:
            val = 1
        if val > 50:
            val = 50

        entry.delete(0, tk.END)
        entry.insert(0, str(val))
    
    def _select_input_file(self):
        """Permite elegir el CSV y lo carga solo cuando el usuario lo selecciona."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de frescuras",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return  # Usuario canceló

        # Actualizar ruta y cargar datos
        self.input_path_var.set(file_path)
        self.shelf_times_path = file_path  # Usar este CSV en el resto de la app

        self.shelf_data = self._load_shelf_data()
        if self.shelf_data.empty:
            messagebox.showwarning("Advertencia", "No se pudieron cargar datos del archivo seleccionado.")
        else:
            self.entry_frescura.config(state="normal")
            self.entry_sku.config(state="normal")
            self.entry_cant.config(state="normal")
            self.lbl_status.config(state="active", text="Ingrese datos", fg="black", anchor="w", justify="center")
            messagebox.showinfo("Información", "Archivo cargado correctamente.")

    def _clear_all_rows(self):
        for row in self.rows_data:
            row['frame'].destroy()
        self.rows_data.clear()
        self.add_new_row()

    def execute_generation(self):
        mode = self.mode_var.get()
        if not mode:
            return
        
        output_folder = self.output_path_var.get()
        query: List[List[str]] = []
        
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

            if mode == "frescuras" :
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
    w, h = 650, 480
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