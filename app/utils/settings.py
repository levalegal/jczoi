import json
import os
from typing import Optional, Dict, Any

class Settings:
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save_settings()
    
    def get_window_geometry(self) -> Optional[Dict[str, int]]:
        return self.settings.get('window_geometry')
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int):
        self.set('window_geometry', {'x': x, 'y': y, 'width': width, 'height': height})
    
    def get_remember_username(self) -> bool:
        return self.settings.get('remember_username', False)
    
    def set_remember_username(self, value: bool):
        self.set('remember_username', value)
    
    def get_last_username(self) -> Optional[str]:
        return self.settings.get('last_username')

