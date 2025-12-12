import os
import logging
from logging.handlers import RotatingFileHandler
from src.frescures import Automatizer
from services.cache_service import  cleanup_project_cache

def configure_logging():
    level_name = os.environ.get("DEBUG", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    
    fmt = logging.Formatter("%(filename)s:%(lineno)d %(name)s: %(message)s")
    root = logging.getLogger()

    if not root.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(level)
        root.addHandler(sh)

        log_dir = os.path.join(os.path.dirname(__file__), "logs.txt")
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
    cleanup_project_cache(PROJECT_ROOT)
    try:
        automatizer = Automatizer(SHELF_TIMES, PROJECT_ROOT)
        cleanup_project_cache(PROJECT_ROOT)
        logger.info("Proceso terminado correctamente.")
    except Exception as e:
        logger.error("Error en el proceso de generación del modelo: {e}", exc_info=True)