import os
import PIL
import logging
import numpy as np
from typing import List, Tuple
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image
from cleanning_service import cleanup_project_cache

logger = logging.getLogger(__name__)

class Barcoder:
    def __init__(self, output_path: str, temp_path: str, query: List[List[str]], project_root: str):
        self.project_root = project_root
        self.output_path = output_path
        self.temp_path = temp_path
        os.makedirs(self.temp_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)
        self.generate_barcodes(query)

    def generate_barcodes(self, query: List[List[str]]):
        """
        Genera un único archivo PDF con N copias de M códigos de barras.
        """
        try:
            # 1. Inicializar el lienzo del PDF
            pdf_path = f"{self.output_path}/Codigos_Barras.pdf"
            c = canvas.Canvas(pdf_path)
            
            page_width, page_height = A4
        
            # Márgenes y espacio
            margin_x = 15 * mm
            margin_y = 25 * mm
            code_width = page_width - 0.5 * margin_x
            code_height = 50 * mm
            gap = 15 * mm

            # Calcular posiciones verticales (una sola columna)
            positions: List[Tuple[float, float]] = []
            y_pos = page_height - margin_y
            while y_pos - code_height >= margin_y:
                positions.append((margin_x, y_pos - code_height))
                y_pos -= (code_height + gap)
                
            items_per_page = len(positions)

            current_pos_index = 0
            temp_files: List[np.ndarray] | List[str] = [] # Para almacenar nombres de archivos temporales

            # 2. Iterar sobre todos los lotes de códigos (M entradas)
            for lote in query:
                texto_codigo = lote[0]
                cantidad_copias = int(lote[1])
                
                # 3. Ciclo de Replicación (N copias por cada texto_codigo)
                for i in range(1, cantidad_copias + 1):
                    # Guardar en un PNG temporal (sin extensión, save() la añade)
                    temp_img_base = os.path.join(self.temp_path, f"temp_barcode_{texto_codigo}_{i}")
                    opciones_renderizado = {'font_path': 'arial.ttf'}
                    codigo = Code128(texto_codigo, writer=ImageWriter())
                    temp_img_path = codigo.save(temp_img_base, options=opciones_renderizado)
                    temp_files.append(temp_img_path)
                    
                    x, y = positions[current_pos_index]
                    
                    # Dibujar imagen ajustada al ancho disponible
                    c.drawImage(temp_img_path, x, y, width=code_width, height=code_height, mask='auto')
                    
                    current_pos_index += 1
                    
                    # Si se llenó la página
                    if current_pos_index >= items_per_page: 
                        c.showPage() # Iniciar una nueva página
                        current_pos_index = 0 # Reiniciar el índice de posición en la nueva página

            # Asegurarse de que el PDF termine con una página completa si la última no lo estaba
            if current_pos_index > 0 and current_pos_index < items_per_page:
                c.showPage()

            # 4. Finalizar y Guardar el PDF
            cleanup_project_cache(self.project_root)
            c.save()
            logger.info(f"ÉXITO: Archivo de códigos de barras consolidado generado como '{pdf_path}'")
        except Exception as e:
            logger.error(f"Error generando codigos de barras: {e}", exc_info=True)
            cleanup_project_cache(self.project_root)
            return e