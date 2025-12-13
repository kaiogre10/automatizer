import logging
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np
import re
import pandas as pd
from utils.utils import validate_frescures, frescure_to_date

logger = logging.getLogger(__name__)

class Automatizer:
    def __init__(self, shelf_time_path: str, project_root: str):
        self.project_root = project_root
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|1[0-9]|2[0-9]|3[0-1])[0-9]$')
        self.shelf_table = self.load_data(shelf_time_path)
        self.get_dates(self.shelf_table)

    def load_data(self, shelf_time_table: str) -> pd.DataFrame:        
        try:
            DF_DIAS = pd.read_csv(shelf_time_table, encoding='utf-8')
            # logger.info(f"FRESCURAS: {DF_DIAS}")
            return DF_DIAS
        except FileNotFoundError as e:
            logger.error(f"Error no se encontró archivo con días de cnosumo preferente: '{e}'", exc_info=True)
            DF_DIAS = pd.DataFrame({'CODIGO': [] ,'DESCRIPCION': [], 'SHELF_LIFE': []})
            return DF_DIAS    

    def validate_query(self, all_frescuras: List[List[str]]) ->  List[List[str]]:
         
        complete_frescures: List[List[str]] = []
        for _ in all_frescuras:
            for frescuras in all_frescuras:
               # logger.info(f"{frescuras}")
                #logger.info(f"{code}")
                valid_frescures: List[str] = []
                if not validate_frescures(self.frescures_pattern, frescuras[0]):
                   # logger.info(f"Frescura no valida: {frescuras}")
                    continue
                         
              #  valid_frescures.append(frescuras)
                fecha = frescure_to_date(frescuras[0])
              #  logger.info(f"Date: {fecha}")
                complete_frescures.append([frescuras[1], frescuras[0], fecha])
              #  complete_frescures.append(valid_frescures)

            logger.info(f"Valid: {complete_frescures}")
            return complete_frescures
       # except Exception as e:
          #  logger.info(f"Error: {e}", exc_info=True)
    
    def get_dates(self, shelf_table: pd.DataFrame):
        query = [["J345", "3007868"], ["L315", "3010443"], ["F135", "1234567"], ["J265", "0987654"]]
        all_frescures = self.validate_query(query)
        logger.info(f"Filtradas: {all_frescures}")
        for frescure in all_frescures:
            sku = frescure[0]
            codigo_frescura = frescure[1]
            fecha_base =  datetime.strptime(frescure[2], "%d/%m/%Y")
            logger.info(f"{type(fecha_base)}")

            # Buscar shelf life por SKU (columna CODIGO en CSV)
            # Normalizar tipos: CODIGO suele ser numérico, convertir sku a int si es posible
            try:
                sku_int = int(sku)
            except ValueError:
                sku_int = None

            if sku_int is not None:
                df_match = shelf_table.loc[shelf_table['CODIGO'] == sku_int, 'SHELF_LIFE']
            else:
                # Si CODIGO en el CSV es string, intentar comparación como string
                df_match = shelf_table.loc[shelf_table['CODIGO'].astype(str) == sku, 'SHELF_LIFE']

            if df_match.empty:
                logger.warning(f"SKU {sku} no encontrado en tabla de shelf life.")
                continue

            shelf_life_days = int(df_match.iloc[0])
            fecha_consumo_preferente = fecha_base + timedelta(days=shelf_life_days)
            logger.info(f"Código {codigo_frescura} → fecha base {fecha_base} + {shelf_life_days} días = {fecha_consumo_preferente}")
            