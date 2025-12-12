import logging
from datetime import datetime, timedelta
from typing import List
import numpy as np
import re
import pandas as pd
from utils.utils import validate_frescures, frescure_to_date

logger = logging.getLogger(__name__)

class Automatizer:
    def __init__(self, shelf_time_table: str, project_root: str):
        self.project_root = project_root
        self.shelf_time_table: str = shelf_time_table
        self.frescures_pattern = re.compile(r'^[A-L](0[1-9]|[12][0-9]|3[01])[0-9]$')
        self.load_data(self.shelf_time_table)
        self.validate_dates_test()

    def load_data(self, shelf_time_table: str) -> pd.DataFrame:        
        try:
            DF_DIAS = pd.read_csv(shelf_time_table, encoding='utf-8')
            # logger.info(f"FRESCURAS: {DF_DIAS}")
        except FileNotFoundError as e:
            logger.error(f"Error no se encontró archivo con días de cnosumo preferente: '{e}'", exc_info=True)

            DF_DIAS = pd.DataFrame({'CODIGO': [] ,'DESCRIPCION': [], 'SHELF_LIFE': []})    

    def validate_dates_test(self):
        frescuras_ejemplos = ["J345", "L315", "F135", "J265", "M085"]
        valid_frescures: List[str] = []
        for frescuras in frescuras_ejemplos:
            if not validate_frescures(self.frescures_pattern, frescuras):
                continue

            logger.info(f"VALIDAS: {frescuras}")
            valid_frescures.append(frescuras)
            fecha = frescure_to_date(frescuras)
            logger.info(f"FECHAS: {fecha}")
            # result.append(fecha)
        # return result
        