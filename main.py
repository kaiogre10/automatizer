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
from config.config_loader import conf

logger = logging.getLogger(__name__)

if not getattr(sys, 'frozen', False):
    from cleanning_service import run_full_cleanup
    run_full_cleanup(os.path.dirname(os.path.abspath(__file__)))

class AppGeneradorCP:
    def __init__(self, master):
        self.master = master
        self.shelf_data = None
        self.shelf_times_path = None
        
        def resource_path(relative_path):
            """ Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller """
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        self.project_root = resource_path(".")
        self.template_path = resource_path(os.path.join(conf.get("paths.data.template_xlsx", "data/plantilla.xlsx")))
        
        # Rutas de salida (fuera del exe)
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.output_path = os.path.join(application_path, conf.get("paths.output.default_folder", "formato_etiquetas"))
        self.temp_path = os.path.join(application_path, conf.get("paths.output.temp_images", "temp_img"))

        self.output_path_var = tk.StringVar(value=self.output_path)
        self.input_path_var = tk.StringVar(value="")

        # --- Datos y Variables ---
        frescura_pattern = conf.get("validation.frescura.pattern", [])
        self.frescures_pattern = re.compile(frescura_pattern)
        self.rows_data: List[Dict[str, Any]] = []
        self.mode_var = tk.StringVar(value="frescuras")
        self.deletion_mode = False

        # ==========================================================
        # ESTILOS CENTRALIZADOS
        # ==========================================================
        self.colors = {
            'header_bg': conf.get("ui.colors.header_bg", "#ddd"),
            'status_ok': conf.get("ui.colors.status_ok", "#3BAB41"),
            'status_warn': conf.get("ui.colors.status_warn", "#d32f2f"),
            'status_info': conf.get("ui.colors.status_info", "#1976D2"),
            'button_add': conf.get("ui.colors.button_add", "#e3f2fd"),
            'button_generate_bg': conf.get("ui.colors.button_generate_bg", "#2e7d32"),
            'button_generate_fg': conf.get("ui.colors.button_generate_fg", "white"),
            'entry_normal_bg': "white",
            'entry_disabled_bg': "#f0f0f0",
            'entry_normal_fg': "black",
            'entry_disabled_fg': "gray",
            'status_default_fg': "gray",
            'status_blocked_fg': "red",
        }
        self.fonts = {
            'default': tuple(conf.get("ui.fonts.default", ["Arial", 9])),
            'header': tuple(conf.get("ui.fonts.header", ["Arial", 9, "bold"])),
            'button': tuple(conf.get("ui.fonts.button", ["Arial", 9, "bold"])),
            'status': tuple(conf.get("ui.fonts.status", ["Arial", 9])),
            'status_blocked': tuple(conf.get("ui.fonts.status_blocked", ["Arial", 9, "bold"])),
        }
        
        # Textos por defecto
        self.texts = {
            'status_default': "Ingrese datos",
            'status_blocked': "CARGUE ARCHIVO CSV",
            'status_barcodes': "Listo para generar",
        }

        # ==========================================================
        # SECCIÓN 1: Configuración Superior
        # ==========================================================
        top_frame = tk.Frame(master, background="", padx=10, pady=10)
        top_frame.grid(row=0, column=0, sticky="ew")

        tk.Label(top_frame, text="Cargar archivo:", font=self.fonts['default']).pack(side="left")
        tk.Entry(top_frame, textvariable=self.input_path_var, width=15, state="readonly").pack(side="left", padx=1)
        tk.Button(top_frame, text="📂", command=self._select_input_file).pack(side="left", padx=1)

        tk.Label(top_frame, text="  ").pack(side="left", expand=True)

        tk.Label(top_frame, text="Carpeta de salida:", font=self.fonts['default']).pack(side="left")
        tk.Entry(top_frame, textvariable=self.output_path_var, width=15, state="readonly").pack(side="left", padx=5)
        tk.Button(top_frame, text="📂", command=self._select_output_folder).pack(side="left", padx=5)

        mode_frame = tk.LabelFrame(master, text="Tipo de documento:", padx=10, pady=5)
        mode_frame.grid(row=1, column=0, padx=10, sticky="ew")
        
        tk.Radiobutton(mode_frame, text="Hojas de Consumo Preferente", variable=self.mode_var, value="frescuras", command=self._on_mode_change).pack(side="left", padx=20)
        tk.Radiobutton(mode_frame, text="Código de Barras", variable=self.mode_var, value="barcodes", command=self._on_mode_change).pack(side="left", padx=20)
        
        # ==========================================================
        # SECCIÓN 2: Encabezados
        # ==========================================================
        self.header_frame = tk.Frame(master, bg=self.colors['header_bg'], pady=5)
        self.header_frame.grid(row=2, column=0, padx=10, sticky="ew")
        self.header_frame.columnconfigure(7, weight=1)

        self.col_idx = conf.get("ui.columns.index_width", 5)
        self.W_COL1 = conf.get("ui.columns.sku_width", 10)
        self.W_COL2 = conf.get("ui.columns.frescura_width", 10)
        self.W_COL3 = conf.get("ui.columns.copias_width", 12)
        
        self.header_select = tk.Label(self.header_frame, text="Sel.", width=4, bg=self.colors['header_bg'], font=self.fonts['header'])
        self.header_select.grid(row=0, column=0, padx=(0, 2))
        self.header_select.grid_remove()

        self.header_index = tk.Label(self.header_frame, text="Num", width=3, bg=self.colors['header_bg'], font=self.fonts['header'])
        self.header_index.grid(row=0, column=1, padx=2)

        self.header_sku = tk.Label(self.header_frame, text="SKU", width=self.W_COL1 + 2, bg=self.colors['header_bg'], font=self.fonts['header'])
        self.header_sku.grid(row=0, column=2, padx=2)

        self.header_frescura = tk.Label(self.header_frame, text="Frescura", width=self.W_COL2 + 2, bg=self.colors['header_bg'], font=self.fonts['header'])
        self.header_frescura.grid(row=0, column=3, padx=2)

        self.header_copias = tk.Label(self.header_frame, text="Copias", width=self.W_COL3 + 2, bg=self.colors['header_bg'], font=self.fonts['header'])
        self.header_copias.grid(row=0, column=4, padx=(2, 0))

        # Espacio para los botones +/- (columnas 5 y 6)
        tk.Label(self.header_frame, text="", width=2, bg=self.colors['header_bg']).grid(row=0, column=5, padx=1)
        tk.Label(self.header_frame, text="", width=2, bg=self.colors['header_bg']).grid(row=0, column=6, padx=(1, 4))

        tk.Label(self.header_frame, text="Info", bg=self.colors['header_bg'], font=self.fonts['header'], anchor="w").grid(row=0, column=7, sticky="w", padx=10)

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

        self.input_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.input_frame, anchor="nw")

        self.input_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ==========================================================
        # SECCIÓN 4: Botones
        # ==========================================================
        self.control_frame = tk.Frame(master, pady=10)
        self.control_frame.grid(row=4, column=0, sticky="ew", padx=10)

        self.btn_add = tk.Button(self.control_frame, text="Añadir Fila", command=self.add_new_row, bg=self.colors['button_add'])
        self.btn_add.pack(side="left", padx=5)
        self.btn_delete = tk.Button(self.control_frame, text="Eliminar Fila", command=self._toggle_deletion_mode)
        self.btn_delete.pack(side="left", padx=5)
        self.btn_cancel_delete = tk.Button(self.control_frame, text="Cancelar", command=self._cancel_deletion_mode)
        self.btn_cancel_delete.pack(side="left", padx=5)
        self.btn_cancel_delete.pack_forget()  # Oculto por defecto
        self.btn_clear = tk.Button(self.control_frame, text="Limpiar", command=self._clear_all_rows)
        self.btn_clear.pack(side="left", padx=5)
        self.btn_generate = tk.Button(self.control_frame, text="GENERAR", command=self.execute_generation, bg=self.colors['button_generate_bg'], fg=self.colors['button_generate_fg'], font=self.fonts['button'], height=2)
        self.btn_generate.pack(side="right", padx=10)

        self.add_new_row()

    # ==========================================================
    # MÉTODOS DE ESTILO CENTRALIZADOS
    # ==========================================================
    def _apply_row_style(self, row_data: Dict[str, Any], state: str):
        """
        Aplica estilos consistentes a una fila según su estado.
        state: 'normal', 'blocked', 'barcodes'
        """
        entry_sku = row_data['sku']
        entry_frescura = row_data['frescura']
        entry_copias = row_data['copias']
        lbl_status = row_data['status']

        if state == 'blocked':
            # Estado bloqueado: sin CSV cargado en modo frescuras
            entry_sku.config(
                state="readonly",
                fg=self.colors['entry_disabled_fg'],
                bg=self.colors['entry_disabled_bg'],
                relief="sunken"
            )
            entry_frescura.config(
                state="readonly",
                fg=self.colors['entry_disabled_fg'],
                bg=self.colors['entry_disabled_bg'],
                relief="sunken"
            )
            entry_frescura.grid(row=0, column=3, padx=2)
            entry_copias.config(
                state="readonly",
                fg=self.colors['entry_disabled_fg'],
                bg=self.colors['entry_disabled_bg'],
                relief="sunken"
            )
            lbl_status.config(
                text=self.texts['status_blocked'],
                fg=self.colors['status_blocked_fg'],
                font=self.fonts['status_blocked']
            )

        elif state == 'barcodes':
            # Estado barcodes: ocultar frescura
            entry_sku.config(
                state="normal",
                fg=self.colors['entry_normal_fg'],
                bg=self.colors['entry_normal_bg'],
                relief="sunken"
            )
            entry_frescura.config(
                state="disabled",
                width=1,
                bg=self.colors['entry_disabled_bg'],
                relief="flat"
            )
            entry_frescura.grid_remove()
            entry_copias.config(
                state="normal",
                fg=self.colors['entry_normal_fg'],
                bg=self.colors['entry_normal_bg'],
                relief="sunken"
            )
            lbl_status.config(
                text=self.texts['status_barcodes'],
                fg=self.colors['status_default_fg'],
                font=self.fonts['status']
            )

        else:  # 'normal'
            # Estado normal: CSV cargado, modo frescuras
            entry_sku.config(
                state="normal",
                fg=self.colors['entry_normal_fg'],
                bg=self.colors['entry_normal_bg'],
                relief="sunken"
            )
            entry_frescura.config(
                state="normal",
                width=self.W_COL2 + 2,
                fg=self.colors['entry_normal_fg'],
                bg=self.colors['entry_normal_bg'],
                relief="sunken"
            )
            entry_frescura.grid(row=0, column=3, padx=2)
            entry_copias.config(
                state="normal",
                fg=self.colors['entry_normal_fg'],
                bg=self.colors['entry_normal_bg'],
                relief="sunken"
            )
            lbl_status.config(
                text=self.texts['status_default'],
                fg=self.colors['status_default_fg'],
                font=self.fonts['status']
            )

    def _get_current_row_state(self) -> str:
        """Determina el estado actual que deben tener las filas."""
        mode = self.mode_var.get()
        if mode == "barcodes":
            return 'barcodes'
        elif not self.input_path_var.get():
            return 'blocked'
        else:
            return 'normal'

    def _apply_style_to_all_rows(self):
        """Aplica el estilo actual a todas las filas existentes."""
        state = self._get_current_row_state()
        for row_data in self.rows_data:
            self._apply_row_style(row_data, state)

    # ==========================================================
    # EVENTOS Y CONFIGURACIÓN
    # ==========================================================
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

    # ==========================================================
    # LÓGICA DE NEGOCIO
    # ==========================================================
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
        if folder:
            self.output_path_var.set(folder)

    def _on_mode_change(self):
        # 1. Limpiar todas las filas existentes primero
        # Usamos una versión interna que no dependa del modo actual
        for row in self.rows_data:
            row['frame'].destroy()
        self.rows_data.clear()
        
        # 2. Configurar el nuevo modo
        mode = self.mode_var.get()
        if mode == "barcodes":
            self.header_sku.config(text="Texto")
            self.header_frescura.grid_remove()
            # En barcodes, siempre agregamos una fila nueva vacía lista para usar
            self.add_new_row()
        else:
            self.header_sku.config(text="SKU")
            self.header_frescura.grid()
            # En frescuras, solo agregamos fila si hay archivo cargado
            if self.input_path_var.get():
                self.add_new_row()
        
        # 3. Aplicar estilos (aunque estará vacío o con una nueva fila)
        self._apply_style_to_all_rows()
    
    def add_new_row(self):
        # Bloquear si estamos en modo eliminación
        if self.deletion_mode:
            messagebox.showwarning("Finalice o cancele la eliminación de filas primero.")
            return
        
        # Bloquear si estamos en modo frescuras y no hay archivo cargado
        # (solo si ya hay filas, para no bloquear la primera fila inicial)
        if self.mode_var.get() == "frescuras" and not self.input_path_var.get():
            if self.rows_data:  # Solo mostrar mensaje si ya hay filas
                messagebox.showwarning("Archivo requerido", "Debe cargar un archivo CSV antes de agregar filas en modo Frescuras.")
            return
        
        row_frame = tk.Frame(self.input_frame)
        row_frame.pack(fill="x", pady=2)

        select_var = tk.BooleanVar(value=False)
        chk_select = tk.Checkbutton(row_frame, variable=select_var)
        chk_select.grid(row=0, column=0, padx=(0, 2))
        chk_select.grid_remove()

        row_index = len(self.rows_data) + 1
        lbl_index = tk.Label(row_frame, text=str(row_index), width=3, anchor="center", font=self.fonts['default'])
        lbl_index.grid(row=0, column=1, padx=2)
        
        entry_sku = tk.Entry(row_frame, width=self.W_COL1 + 2, justify="center", font=self.fonts['default'])
        entry_sku.grid(row=0, column=2, padx=2)
        
        entry_frescura = tk.Entry(row_frame, width=self.W_COL2 + 2, justify="center", font=self.fonts['default'])
        entry_frescura.grid(row=0, column=3, padx=2)
        
        entry_cant = tk.Entry(row_frame, width=self.W_COL3 + 2, justify="center", font=self.fonts['default'])
        entry_cant.insert(0, "1")
        entry_cant.grid(row=0, column=4, padx=(2, 0))

        # Validadores
        vc_sku = self.master.register(self._vc_sku)
        vc_fres = self.master.register(self._vc_frescura)
        vc_cop = self.master.register(self._vc_copias)
        entry_sku.config(validate='key', validatecommand=(vc_sku, '%P'))
        entry_frescura.config(validate='key', validatecommand=(vc_fres, '%P'))
        entry_cant.config(validate='key', validatecommand=(vc_cop, '%P'))

        btn_menos = tk.Button(
            row_frame,
            text="-",
            width=2,
            font=self.fonts['default'],
            command=lambda e=entry_cant: self._ajustar_copias(e, -1)
        )
        btn_menos.grid(row=0, column=5, padx=1)

        btn_mas = tk.Button(
            row_frame,
            text="+",
            width=2,
            font=self.fonts['default'],
            command=lambda e=entry_cant: self._ajustar_copias(e, +1)
        )
        btn_mas.grid(row=0, column=6, padx=(1, 4))
        
        lbl_status = tk.Label(row_frame, text="", anchor="w", justify="left", font=self.fonts['status'])
        lbl_status.grid(row=0, column=7, padx=10, sticky="ew")
        
        row_frame.columnconfigure(7, weight=1)

        row_data: Dict[str, Any] = {
            'frame': row_frame,
            'select_var': select_var,
            'select_chk': chk_select,
            'index_lbl': lbl_index,
            'sku': entry_sku,
            'frescura': entry_frescura,
            'copias': entry_cant,
            'status': lbl_status
        }
        
        # Bindings para cálculo en tiempo real
        entry_sku.bind("<KeyRelease>", lambda e, r=row_data: self._calculate_preview(r))
        entry_frescura.bind(
            "<KeyRelease>",
            lambda e, r=row_data: (self._force_upper(e.widget), self._calculate_preview(r))
        )
        
        self.rows_data.append(row_data)
        
        # Aplicar estilo según el estado actual
        state = self._get_current_row_state()
        self._apply_row_style(row_data, state)

    def _force_upper(self, widget: tk.Entry):
        current = widget.get()
        upper = current.upper()
        if current != upper:
            pos = widget.index(tk.INSERT)
            widget.delete(0, tk.END)
            widget.insert(0, upper)
            widget.icursor(pos)

    def _force_lower(self, widget: tk.Entry):
        current = widget.get()
        lower = current.lower()
        if current != lower:
            pos = widget.index(tk.INSERT)
            widget.delete(0, tk.END)
            widget.insert(0, lower)
            widget.icursor(pos)

    def _vc_sku(self, P: str) -> bool:
        if P == "":
            return True
        max_len = conf.get("validation.sku.max_length", 7)
        return P.isdigit() and len(P) <= max_len

    def _vc_frescura(self, P: str) -> bool:
        if P == "":
            return True
        max_len = conf.get("validation.frescura.max_length", 4)
        return len(P) <= max_len

    def _vc_copias(self, P: str) -> bool:
        if P == "":
            return True
        return P.isdigit() and len(P) <= 2

    def _calculate_preview(self, row):
        """Lógica para mostrar descripción o cálculo completo."""
        mode = self.mode_var.get()
        sku_val: str = row['sku'].get().strip()
        frescura_val: str = row['frescura'].get().strip().upper()
        status_lbl = row['status']
         
        # Si estamos en modo frescuras y no hay CSV cargado válido
        if mode == "frescuras" and (self.shelf_data is None or self.shelf_data.empty):
            status_lbl.config(
                text=self.texts['status_blocked'],
                fg=self.colors['status_blocked_fg'],
                font=self.fonts['status_blocked']
            )
            return
        
        if not sku_val:
            status_lbl.config(
                text=self.texts['status_default'],
                fg=self.colors['status_default_fg'],
                font=self.fonts['status']
            )
            return
        
        if mode == "barcodes":
            status_lbl.config(
                text=self.texts['status_barcodes'],
                fg=self.colors['status_ok'],
                font=self.fonts['status']
            )
            return

        # 1. Validar SKU numéricamente
        if not validate_sku(sku_val):
            status_lbl.config(
                text="SKU inválido",
                fg=self.colors['status_warn'],
                font=self.fonts['status']
            )
            return

        # 2. Buscar en Base de Datos
        match = self.shelf_data.loc[self.shelf_data['CODIGO'] == sku_val]
        
        if match.empty:
            status_lbl.config(
                text="SKU inexistente",
                fg=self.colors['status_warn'],
                font=self.fonts['status']
            )
            return

        # Obtener Descripción
        descripcion = match.iloc[0]['DESCRIPCION']

        # CASO A: Solo SKU ingresado -> Mostrar solo Descripción
        if not frescura_val:
            status_lbl.config(
                text=f"{descripcion}",
                fg=self.colors['status_info'],
                font=self.fonts['status']
            )
            return

        # CASO B: SKU + Frescura -> Validar y Calcular Fechas
        if not validate_frescures(self.frescures_pattern, frescura_val):
            status_lbl.config(
                text="Frescura incorrecta",
                fg=self.colors['status_warn'],
                font=self.fonts['status']
            )
            return

        fecha_elab_str = frescure_to_date(frescura_val)
        if not fecha_elab_str:
            status_lbl.config(
                text=f"{descripcion} | Fecha inválida",
                fg=self.colors['status_warn'],
                font=self.fonts['status']
            )
            return

        try:
            shelf_days = int(match.iloc[0]['SHELF_LIFE'])
            fecha_base = datetime.strptime(fecha_elab_str, "%d/%m/%Y")
            fecha_venc = fecha_base + timedelta(days=shelf_days)
            fecha_venc_str = fecha_venc.strftime("%d/%m/%Y")
            
            # Mensaje Completo
            msg = f"{descripcion} | Lote: {fecha_elab_str} => Cons. Pref: '{fecha_venc_str}'"
            status_lbl.config(
                text=msg,
                fg=self.colors['status_ok'],
                font=self.fonts['status']
            )
            
        except Exception as e:
            status_lbl.config(
                text=f"Error cálculo: {e}",
                fg=self.colors['status_warn'],
                font=self.fonts['status']
            )

    def _ajustar_copias(self, entry: tk.Entry, delta: int):
        """Suma o resta copias, manteniendo el valor en el rango 1–99."""
        try:
            val = int(entry.get())
        except ValueError:
            val = 1

        val += delta

        if val < 1:
            val = 1
        if val > 99:
            val = 99

        entry.delete(0, tk.END)
        entry.insert(0, str(val))
    
    def _select_input_file(self):
        """Permite elegir el CSV y lo carga solo cuando el usuario lo selecciona."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de frescuras",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        self.input_path_var.set(file_path)
        self.shelf_times_path = file_path

        self.shelf_data = self._load_shelf_data()
        if self.shelf_data.empty:
            messagebox.showwarning("Advertencia", "No se pudieron cargar datos del archivo seleccionado.")
        else:
            # Aplicar estilos a TODAS las filas consistentemente
            self._apply_style_to_all_rows()
            messagebox.showinfo("Información", "Archivo cargado correctamente.")

    def _clear_all_rows(self):
        # Bloquear si estamos en modo eliminación
        if self.deletion_mode:
            messagebox.showwarning("Operación bloqueada", "Finalice o cancele la eliminación de filas primero.")
            return
        
        for row in self.rows_data:
            row['frame'].destroy()
        self.rows_data.clear()
        
        # Solo agregar fila si hay archivo cargado en modo frescuras, o si es modo barcodes
        if self.mode_var.get() == "barcodes" or self.input_path_var.get():
            self.add_new_row()

    def _toggle_deletion_mode(self):
        """Alterna entre modo normal y modo de eliminación."""
        if not self.rows_data:
            messagebox.showinfo("Sin filas", "No hay filas para eliminar.")
            return

        if not self.deletion_mode:
            self.deletion_mode = True
            self.btn_delete.config(text="Confirmar Eliminación", bg="#d32f2f", fg="white")
            self.btn_cancel_delete.pack(side="left", padx=5, after=self.btn_delete)
            # Deshabilitar otros botones
            self.btn_add.config(state="disabled")
            self.btn_clear.config(state="disabled")
            self.btn_generate.config(state="disabled")
            self._show_checkboxes()
        else:
            selected_indices = [i for i, row in enumerate(self.rows_data) if row['select_var'].get()]

            if not selected_indices:
                messagebox.showinfo("Seleccione filas", "Marca al menos una fila para eliminar.")
                return

            for index in reversed(selected_indices):
                row = self.rows_data.pop(index)
                row['frame'].destroy()

            if not self.rows_data:
                # Temporalmente desactivar deletion_mode para permitir add_new_row
                self.deletion_mode = False
                self.add_new_row()
            else:
                self._renumber_rows()

            self._exit_deletion_mode()
    
    def _cancel_deletion_mode(self):
        """Cancela el modo de eliminación sin eliminar filas."""
        self._hide_checkboxes()
        self._exit_deletion_mode()
    
    def _exit_deletion_mode(self):
        """Restaura la UI al salir del modo eliminación."""
        self.deletion_mode = False
        self.btn_delete.config(text="Eliminar Fila", bg="SystemButtonFace", fg="black")
        self.btn_cancel_delete.pack_forget()
        # Rehabilitar otros botones
        self.btn_add.config(state="normal")
        self.btn_clear.config(state="normal")
        self.btn_generate.config(state="normal")
        self._hide_checkboxes()

    def _show_checkboxes(self):
        """Muestra todos los checkboxes de selección."""
        self.header_select.grid()
        for row in self.rows_data:
            row['select_chk'].grid()

    def _hide_checkboxes(self):
        """Oculta todos los checkboxes de selección."""
        self.header_select.grid_remove()
        for row in self.rows_data:
            row['select_chk'].grid_remove()
            row['select_var'].set(False)

    def _renumber_rows(self):
        for i, row in enumerate(self.rows_data, start=1):
            row['index_lbl'].config(text=str(i))
            row['select_var'].set(False)

    def execute_generation(self):
        # Bloquear si estamos en modo eliminación
        if self.deletion_mode:
            messagebox.showwarning("Operación bloqueada", "Finalice o cancele la eliminación de filas primero.")
            return
        
        mode = self.mode_var.get()
        if not mode:
            return
        
        # --- VALIDACIÓN PREVIA ---
        filas_invalidas = []
        for idx, row in enumerate(self.rows_data, start=1):
            v1 = row['sku'].get().strip()
            v2 = row['frescura'].get().strip()
            cant_str = row['copias'].get().strip()
            status_text = row['status'].cget('text')
            status_fg = row['status'].cget('fg')
            
            if mode == "frescuras":
                if not v1 or not v2:
                    filas_invalidas.append(f"Fila {idx}: Datos incompletos")
                    continue
                if status_fg == self.colors['status_warn'] or "inválido" in status_text.lower() or "inexistente" in status_text.lower():
                    filas_invalidas.append(f"Fila {idx}: {status_text}")
            else:
                if not v1:
                    filas_invalidas.append(f"Fila {idx}: Texto vacío")
                    continue
            
            try:
                cantidad = int(cant_str)
                if cantidad < 1 or cantidad > 99:
                    filas_invalidas.append(f"Fila {idx}: Cantidad fuera de rango (1-99)")
            except ValueError:
                filas_invalidas.append(f"Fila {idx}: Cantidad inválida")
        
        if filas_invalidas:
            msg_error = "Corrija los siguientes errores antes de generar:\n\n" + "\n".join(filas_invalidas)
            messagebox.showerror("Validación fallida", msg_error)
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
            
            if not v1:
                continue
            
            try:
                cantidad = int(cant_str)
                if cantidad < 1:
                    cantidad = 1
            except:
                cantidad = 1

            if mode == "frescuras":
                if validate_sku(v1) and validate_frescures(self.frescures_pattern, v2.upper()):
                    for _ in range(cantidad):
                        query.append([v1, v2.upper()])
            else:
                query.append([v1, str(cantidad)])

        if not query:
            messagebox.showwarning("Vacío", "No hay datos válidos.")
            return

        try:
            if mode == "frescuras":
                Frescurer(self.shelf_times_path, self.template_path, output_folder, query, self.project_root, self.frescures_pattern)
                msg = "Hojas de consumo preferente generadas."
            else:
                Barcoder(output_folder, self.temp_path, query, self.project_root)
                msg = "Códigos generados."
            messagebox.showinfo("Éxito", f"{msg}\nEn: {output_folder}")
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))

def main():
    root = tk.Tk()
    root.title(conf.get("app.name", "Generador de Etiquetas"))
    
    w = conf.get("app.window.width", 650)
    h = conf.get("app.window.height", 480)
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (ws/2) - (w/2), (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    resizable = conf.get("app.window.resizable", True)
    root.resizable(resizable, resizable)
    
    root.rowconfigure(3, weight=1) 
    root.columnconfigure(0, weight=1)

    AppGeneradorCP(root)
    root.mainloop()


if __name__ == "__main__":
    main()