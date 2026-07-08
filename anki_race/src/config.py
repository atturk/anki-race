import os
from typing import Any, Dict
from aqt import mw

addon_package = __name__.split('.')[0]

DEFAULT_CONFIG = {
    "road_scrolling": False,
    "show_overview_button": True,
    "default_mode": "normale",
    "default_time": 5.0,
    "default_advantage": 30.0,
    "road_height": 35,
    "car_cpu_offset_y": 2,
    "car_user_offset_y": 18,
    "car_cpu_type": "emoji",
    "car_cpu_emoji": "🚓",
    "car_cpu_flip": True,
    "car_cpu_file": "",
    "car_user_type": "emoji",
    "car_user_emoji": "🏎️",
    "car_user_flip": False,
    "car_user_file": "",
    "road_style": "image",
    "road_solid_color": "#1e272e",
    "road_image_file": ""
}

class AnkiRaceConfig:
    def __init__(self) -> None:
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        """Loads configuration from Anki's addon manager."""
        if not mw:
            return
        loaded = mw.addonManager.getConfig(addon_package)
        if isinstance(loaded, dict):
            # Merge with defaults to handle any missing keys
            self._config = DEFAULT_CONFIG.copy()
            self._config.update(loaded)

    def save(self) -> None:
        """Saves current configuration to Anki's addon manager."""
        if not mw:
            return
        mw.addonManager.writeConfig(addon_package, self._config)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()

    def update(self, updates: Dict[str, Any]) -> None:
        self._config.update(updates)
        self.save()

# Global configuration instance
race_config = AnkiRaceConfig()
