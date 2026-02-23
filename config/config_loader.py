import yaml
import sys
import os
from typing import Any, Dict

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _get_base_path(self):
        import sys
        import os
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load_config(self):
        base_path = self._get_base_path()
        # Busca en config/settings.yaml
        config_path = os.path.join(base_path, "config", "settings.yaml")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"ADVERTENCIA: No se encontró el archivo de configuración en {config_path}")
            self._config = {}
        except Exception as e:
            print(f"ERROR: Fallo al leer configuración: {e}")
            self._config = {}

    def get(self, path: str, default=None):
        """
        Obtiene un valor usando notación de punto.
        Ejemplo: config.get('ui.colors.status_ok')
        """
        keys = path.split('.')
        value = self._config
        
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return default
            return value if value is not None else default
        except:
            return default

# Instancia global lista para importar
conf = Config()