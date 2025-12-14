import logging
import openpyxl
from datetime import datetime, timedelta
import os
import time
from typing import List
import re
import pandas as pd
from utils.utils import validate_frescures, frescure_to_date, validate_sku

logger = logging.getLogger(__name__)

class Frescurer:
    def __init__(self, shelf_time_path: str, template_path: str, output_path: str, query: List[List[str]], project_root: str):
        t0 = time.perf_counter()
        self.project_root = project_root
        self.shelf_table = self.load_data(shelf_time_path)
        self.template_path = template_path
        self.output_path = output_path
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|1[0-9]|2[0-9]|3[0-1])[0-9]$')
        all_frescures = self.validate_query(query)
        self.attend_query(self.shelf_table, all_frescures, self.template_path)
        logger.info(f"Proceso completado en: {time.perf_counter() - t0:.6f}")

    def load_data(self, shelf_time_table: str) -> pd.DataFrame:
        try:
            DF_DIAS = pd.read_csv(shelf_time_table, encoding='utf-8') #type: ignore
            return DF_DIAS
        except FileNotFoundError as e:
            logger.error(f"Error no se encontró archivo con días de cnosumo preferente: '{e}'", exc_info=True)
            return pd.DataFrame({'CODIGO': [] ,'DESCRIPCION': [], 'SHELF_LIFE': []})

    def validate_query(self, all_frescuras: List[List[str]]) -> List[List[str]]:
        complete_frescures: List[List[str]] = []
        for frescuras in all_frescuras:
            if not validate_frescures(self.frescures_pattern, frescuras[1]) or not validate_sku(frescuras[0]):
                # logger.warning(f"Query no váida '{frescuras}'")
                continue
                        
            fecha = frescure_to_date(frescuras[1])
            complete_frescures.append([frescuras[0], frescuras[1], fecha])

        # logger.info(f"Valid: {complete_frescures}")
        return complete_frescures
    
    def attend_query(self, shelf_table: pd.DataFrame, all_frescures: List[List[str]], template_path: str):
        complete_data: List[List[str]] = []
        for frescure in all_frescures:
            sku = frescure[0].strip()
            codigo_frescura = frescure[1]
            frescura_final = frescure[2]
            
            fecha_base = datetime.strptime(frescure[2], "%d/%m/%Y").date()
            
            df_match = shelf_table.loc[shelf_table['CODIGO'].astype(str) == sku, 'SHELF_LIFE']

            if df_match.empty:
                logger.warning(f"SKU {sku} no encontrado en tabla de shelf life.")
                continue

            shelf_life_days = int(df_match.iloc[0])
            fecha_consumo_preferente = fecha_base + timedelta(days=shelf_life_days)
            fecha_final_consumo = fecha_consumo_preferente.strftime("%d/%m/%Y")

            # Mostrar solo la parte de fecha sin la hora
            complete_data.append([frescure[0], codigo_frescura, frescura_final, fecha_final_consumo])

        # La plantilla debe ser la hoja que tiene el formato A4
        logger.info(f"Final Query: {complete_data}")
        self.create_templates(complete_data, template_path)

    def create_templates(self, complete_data: List[List[str]], template_path: str):
        template = openpyxl.load_workbook(template_path)
        
        # Obtener la hoja original como referencia
        hoja_original = template.active
        if hoja_original is None:
            return
        
        nombre_hoja_original = hoja_original.title
        
        for idx, data in enumerate(complete_data):
            sku = str(data[0])
            frescura = str(data[2])
            caducidad = str(data[3])
            
            if idx == 0:
                # Usar la hoja original para el primer registro
                hoja_destino = hoja_original
            else:
                # Copiar la hoja original para los demás registros
                hoja_destino = template.copy_worksheet(hoja_original)
                hoja_destino.title = f"CP_{sku}_{idx}"
            
            # Inyectar datos en las celdas
            hoja_destino['D8'] = frescura
            hoja_destino['D15'] = sku
            hoja_destino['D24'] = caducidad
        
        # Guardar todo en un solo archivo
        os.makedirs(self.output_path, exist_ok=True)
        nombre_archivo = f"{self.output_path}/hojas_de_frescura.xlsx"
        template.save(nombre_archivo)
        logger.info(f"Documento generado: {nombre_archivo}")
