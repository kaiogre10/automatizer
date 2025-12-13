import tkinter as tk
import logging
import os
import re
from typing import List, Dict, Any
from tkinter import messagebox, ttk
from src.frescures import Frescurer
from src.barcoder import Barcoder
from services.cache_service import clear_output_folders
from utils.utils import validate_frescures, validate_sku

logger = logging.getLogger(__name__)

class AppGeneradorCP:
    def __init__(self, master):
        self.master = master
        master.title("Generador de Etiquetas")
        master.geometry("550x480")
        master.resizable(False, False)

        # Permitir que la fila 2 y la columna 0 crezcan (scroll area)
        master.rowconfigure(2, weight=1)
        master.columnconfigure(0, weight=1)

        # Rutas del proyecto
        # CORRECCIÓN: Al estar main.py en la raíz, no necesitamos subir un nivel ("..")
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.shelf_times_path = os.path.join(self.project_root, "data", "frescuras.csv")
        self.template_path = os.path.join(self.project_root, "data", "plantilla.xlsx")
        self.output_path = os.path.join(self.project_root, "output")
        self.temp_path = os.path.join(self.project_root, "temp_img")
        
        # Patrón para validación visual solamente
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|1[0-9]|2[0-9]|3[0-1])[0-9]$')
        
        self.rows_data: List[Dict[str, Any]] = []
        self.mode_var = tk.StringVar(value="frescuras")
        
        # === Selector de Modo ===
        self.mode_frame = tk.LabelFrame(master, text="Modo de Operación", padx=15, pady=15)
        self.mode_frame.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

        self.mode_frame.columnconfigure(0, weight=1)
        self.mode_frame.columnconfigure(1, weight=1)

        tk.Radiobutton(
            self.mode_frame,
            text="Hojas de Consumo",
            variable=self.mode_var,
            value="frescuras",
            command=self._on_mode_change
        ).grid(row=0, column=0, padx=20, sticky="w")

        tk.Radiobutton(
            self.mode_frame,
            text="Códigos de Barras",
            variable=self.mode_var,
            value="barcodes",
            command=self._on_mode_change
        ).grid(row=0, column=1, padx=20, sticky="w")

        # === Encabezados ===
        self.header_frame = tk.Frame(master)
        self.header_frame.grid(row=1, column=0, pady=(0, 5), padx=10, sticky="ew")

        self.header_frame.columnconfigure(0, weight=1)
        self.header_frame.columnconfigure(1, weight=1)

        self.lbl_col1 = tk.Label(self.header_frame, text="SKU Producto", width=20, font=('Arial', 9, 'bold'), anchor="w")
        self.lbl_col2 = tk.Label(self.header_frame, text="Frescura", width=20, font=('Arial', 9, 'bold'), anchor="w")

        self.lbl_col1.grid(row=0, column=0, padx=5, sticky="w")
        self.lbl_col2.grid(row=0, column=1, padx=5, sticky="w")

        # === Área de Entrada (Scroll) ===
        self.canvas_frame = tk.Frame(master, borderwidth=1, relief="sunken")
        self.canvas_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.canvas = tk.Canvas(self.canvas_frame, height=220)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.input_frame = tk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

        self.canvas.create_window((0, 0), window=self.input_frame, anchor="nw")
        self.input_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # === Botones ===
        self.control_frame = tk.Frame(master)
        self.control_frame.grid(row=3, column=0, pady=10, padx=10, sticky="e")

        tk.Button(self.control_frame, text="+ Fila", command=self.add_new_row, width=10)\
            .grid(row=0, column=0, padx=5)
        tk.Button(self.control_frame, text="Limpiar", command=self._clear_all_rows, width=10)\
            .grid(row=0, column=1, padx=5)
        tk.Button(
            self.control_frame,
            text="GENERAR",
            command=self.execute_generation,
            bg='#4CAF50',
            fg='white',
            width=15,
            font=('Arial', 10, 'bold')
        ).grid(row=0, column=2, padx=15)

        self.add_new_row()

    def _on_mode_change(self):
        """Actualiza las etiquetas según el modo."""
        if self.mode_var.get() == "frescuras":
            self.lbl_col1.config(text="SKU (7 dígitos)")
            self.lbl_col2.config(text="Frescura (A000)")
        else:
            self.lbl_col1.config(text="Código")
            self.lbl_col2.config(text="Cantidad")
        
        # Re-validar visualmente las filas existentes
        for row in self.rows_data:
            self._validate_row_visual(row)

    def add_new_row(self):
        """Añade una fila vacía."""
        row_frame = tk.Frame(self.input_frame)
        row_frame.pack(pady=2, fill="x")

        row = {
            'frame': row_frame,
            'col1_entry': tk.Entry(row_frame, width=20),
            'col2_entry': tk.Entry(row_frame, width=20)
        }

        row['col1_entry'].grid(row=0, column=0, padx=5, sticky="w")
        row['col2_entry'].grid(row=0, column=1, padx=5, sticky="w")

        # Validación visual al perder el foco
        row['col1_entry'].bind("<FocusOut>", lambda e: self._validate_row_visual(row))
        row['col2_entry'].bind("<FocusOut>", lambda e: self._validate_row_visual(row))

        self.rows_data.append(row)

    def _validate_row_visual(self, row):
        """
        Validación puramente visual (formato). 
        No consulta bases de datos ni calcula fechas.
        """
        mode = self.mode_var.get()
        val1 = row['col1_entry'].get().strip()
        val2 = row['col2_entry'].get().strip()
        
        # Resetear colores
        row['col1_entry'].config(bg='white')
        row['col2_entry'].config(bg='white')
        
        if not val1 and not val2: return

        if mode == "frescuras":
            # Validar formato SKU
            if val1 and not validate_sku(val1):
                row['col1_entry'].config(bg='#FFCDD2') # Rojo claro
            
            # Validar formato Frescura
            if val2 and not validate_frescures(self.frescures_pattern, val2.upper()):
                row['col2_entry'].config(bg='#FFCDD2')
        else:
            # Modo Barcodes
            # Cantidad debe ser número positivo
            if val2 and (not val2.isdigit() or int(val2) <= 0):
                row['col2_entry'].config(bg='#FFCDD2')

    def _clear_all_rows(self):
        for row in self.rows_data:
            row['frame'].destroy()
        self.rows_data.clear()
        self.add_new_row()

    def execute_generation(self):
        """Recopila datos y llama al backend correspondiente."""
        mode = self.mode_var.get()
        query = []
        
        # Recopilar datos válidos
        for row in self.rows_data:
            v1 = row['col1_entry'].get().strip()
            v2 = row['col2_entry'].get().strip()
            
            if not v1 or not v2: continue
            
            if mode == "frescuras":
                # Solo enviamos si cumple formato básico
                if validate_sku(v1) and validate_frescures(self.frescures_pattern, v2.upper()):
                    query.append([v1, v2.upper()])
            else:
                # Barcodes: Texto y Cantidad
                if v2.isdigit() and int(v2) > 0:
                    query.append([v1, v2])

        if not query:
            messagebox.showwarning("Atención", "No hay datos válidos para procesar.")
            return

        try:
            # Limpiar carpetas previas
            clear_output_folders([self.output_path], self.temp_path)
            
            if mode == "frescuras":
                # Delegar a Frescurer
                Frescurer(self.shelf_times_path, self.template_path, self.output_path, query, self.project_root)
                msg = "Hojas de consumo generadas correctamente."
            else:
                # Delegar a Barcoder
                Barcoder(self.output_path, self.temp_path, query, self.project_root)
                msg = "Códigos de barras generados correctamente."
                
            messagebox.showinfo("Proceso Terminado", f"{msg}\n\nRevise la carpeta 'output'.")
            
        except Exception as e:
            logger.error(f"Error en el proceso: {e}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante la generación:\n{e}")

def main():
    root = tk.Tk()
    AppGeneradorCP(root)
    root.mainloop()

if __name__ == "__main__":
    main()
