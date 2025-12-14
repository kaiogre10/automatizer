import os
import logging
from logging.handlers import RotatingFileHandler
from src.frescures import Frescurer
from src.barcoder import Barcoder
from services.cache_service import  clear_output_folders

def configure_logging():
    level_name = os.environ.get("DEBUG", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    
    fmt = logging.Formatter("%(filename)s:%(lineno)d: %(message)s")
    root = logging.getLogger()

    if not root.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(level)
        root.addHandler(sh)
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(os.path.join(log_dir, "app.txt"), maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(level)
        root.addHandler(fh)

    root.setLevel(level)

if __name__ == "__main__":
    configure_logging()
    logger = logging.getLogger(__name__)
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    SHELF_TIMES = os.path.join(PROJECT_ROOT, "data", "frescuras.csv")
    TEMPLATE = os.path.join(PROJECT_ROOT, "data", "plantilla.xlsx")
    OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output")
    TEMP_PATH = os.path.join(PROJECT_ROOT, "temp_img")
    query = [["3017868", "J305"], ["3010443", "L305"], ["3010443 ", "L315"], ["1234567", "Z135"], ["30173672", "J265"]]
    # query = [["119", "2"], ["117", "4"], ["50", "1"], ["80", "2"]]
    clear_output_folders([OUTPUT_PATH], TEMP_PATH)
    try:
        # Barcoder(OUTPUT_PATH, TEMP_PATH, query, PROJECT_ROOT)
        Frescurer(SHELF_TIMES, TEMPLATE, OUTPUT_PATH, query, PROJECT_ROOT)
        logger.info("Proceso terminado correctamente.")
    except Exception as e:
        logger.error("Error en el proceso de generación del modelo: {e}", exc_info=True)
