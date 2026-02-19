# service/cache_manager.py
import shutil
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

EXCLUDED_DIRS = {".venv", "venv"}

PYINSTALLER_DIRS = {"build", "dist"}

def cleanup_pyinstaller_temp() -> None:
    r"""Elimina carpetas temporales _MEIxxxxx de PyInstaller en %LOCALAPPDATA%\Temp."""
    import tempfile
    import glob
    logger.debug("Borrando cachés temporales de PyInstaller (_MEI*)")

    temp_base = os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
    pattern = os.path.join(temp_base, "Temp", "_MEI*")

    for meidir in glob.glob(pattern):
        if os.path.isdir(meidir):
            try:
                shutil.rmtree(meidir, ignore_errors=True)
                logger.debug(f"Carpeta temporal eliminada: {meidir}")
            except Exception as e:
                logger.warning(f"No se pudo borrar {meidir}: {e}")

def clear_output_folders(output_paths: List[str]) -> None:
    """Vacia las carpetas de salida definidas en la config y cuenta los eliminados."""
    deleted_files = 0
    deleted_folder = 0

    logger.debug("Limpieza Inicial: Vaciando carpetas de salida")
    for folder_path in output_paths:
        if not os.path.isdir(folder_path):
            continue
        
        for item_name in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item_name)
            try:
                if os.path.isdir(item_path):
                    for root, dirs, files in os.walk(item_path): # type: ignore
                        deleted_folder += len(dirs)
                        deleted_files += len(files)
                        
                    shutil.rmtree(item_path)
                    deleted_folder += 1
                    
                else:
                    os.remove(item_path)
                    deleted_files += 1
                    
                logger.debug(f"Eliminado: {item_path}")
                
            except Exception as e:
                logger.error(f"Error al eliminar {item_path}: {e}", exc_info=True)
                
    total_eliminated = deleted_files + deleted_folder
    if total_eliminated > 0:
        logger.debug(f"Total eliminados: {total_eliminated} (archivos: {deleted_files}, carpetas: {deleted_folder})")

def cleanup_pyinstaller_artifacts(project_root: str) -> None:
    """Elimina carpetas build/, dist/ y archivos .spec generados por PyInstaller."""
    logger.debug("Limpieza PyInstaller: Eliminando artefactos de compilacion")

    for dir_name in PYINSTALLER_DIRS:
        dir_path = os.path.join(project_root, dir_name)
        if os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                logger.debug(f"Eliminada carpeta PyInstaller: {dir_path}")
            except Exception as e:
                logger.error(f"Error al eliminar {dir_path}: {e}", exc_info=True)

    for item in os.listdir(project_root):
        if item.endswith(".spec"):
            continue
            # spec_path = os.path.join(project_root, item)
            # try:
            #     os.remove(spec_path)
            #     logger.debug(f"Eliminado archivo .spec: {spec_path}")
            # except Exception as e:
            #     logger.error(f"Error al eliminar {spec_path}: {e}", exc_info=True)


def cleanup_project_cache(project_root: str) -> None:
    """Elimina la cache del proyecto (__pycache__ y .pyc/.pyo). Excluye .venv y venv."""
    logger.debug("Limpieza Final: Eliminando cache del proyecto")

    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for d in list(dirnames):
            if d == "__pycache__":
                cache_path = os.path.join(dirpath, d)
                try:
                    shutil.rmtree(cache_path)
                    dirnames.remove(d)
                    logger.debug(f"Eliminada carpeta cache: {cache_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar {cache_path}: {e}", exc_info=True)

        for filename in filenames:
            if filename.endswith(('.pyc', '.pyo')):
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    logger.debug(f"Eliminado archivo de cache: {file_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar {file_path}: {e}", exc_info=True)

def run_full_cleanup(project_root: str, output_paths: List[str] | None = None) -> None:
    """Ejecuta la limpieza completa: artefactos PyInstaller, cache Python y carpetas de salida."""
    logger.info("Iniciando limpieza completa del proyecto")
    cleanup_pyinstaller_artifacts(project_root)
    cleanup_pyinstaller_temp()
    cleanup_project_cache(project_root)
    if output_paths:
        clear_output_folders(output_paths)
    logger.info("Limpieza completa finalizada")

def run_pre_gui_cleanup(project_root: str) -> None:
    """Limpieza al inicio (antes de la GUI): solo artefactos pesados (build, dist, _MEI)."""
    logger.info("Limpiando antes de arrancar GUI")
    cleanup_pyinstaller_artifacts(project_root)
    cleanup_pyinstaller_temp()
    logger.info("Limpieza inicial terminada")

def run_post_gui_cleanup(project_root: str) -> None:
    """Limpieza al final (después de GUI): solo cache de Python generado en runtime."""
    logger.info("Limpiando al finalizar GUI")
    cleanup_project_cache(project_root)
    logger.info("Limpieza final terminada")


### USO
# from cleanning_service import run_pre_gui_cleanup, run_post_gui_cleanup
# 
# run_pre_gui_cleanup(r"C:\ruta\proyecto")   # antes de root.mainloop()
# run_post_gui_cleanup(r"C:\ruta\proyecto")  # después de root.mainloop()
# 
# run_full_cleanup(...)                     # antigua unión; aún disponible
