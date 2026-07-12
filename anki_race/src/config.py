import os
from typing import Any, Dict
from aqt import mw

addon_package = __name__.split('.')[0]

DEFAULT_CONFIG = {
    "car_cpu_emoji": "🚗",
    "car_cpu_file": "",
    "car_cpu_flip": True,
    "car_cpu_offset_y": 14,
    "car_cpu_size": 30,
    "car_cpu_type": "emoji",
    "car_user_emoji": "🚙",
    "car_user_file": "",
    "car_user_flip": True,
    "car_user_offset_y": 22,
    "car_user_size": 30,
    "car_user_type": "emoji",
    "deck_leave_action": "pause",
    "decor_emoji": "🌲   🏠   🌲",
    "decor_enabled": True,
    "decor_image_file": "road-texture.png",
    "decor_replicate": True,
    "decor_scrolling": True,
    "decor_size": 58,
    "decor_spacer": 0,
    "decor_speed": 6,
    "decor_type": "image",
    "decor_x": 50,
    "decor_y": 29,
    "default_advantage": 30.0,
    "default_mode": "normale",
    "default_time": 5.0,
    "nitro_cards": 5,
    "nitro_enabled": False,
    "road_height": 35,
    "road_image_file": "",
    "road_scrolling": False,
    "road_solid_color": "#ffffff",
    "road_style": "solid",
    "shortcut": "",
    "show_deck_list_flag": True,
    "show_defeat_popup": True,
    "show_overview_button": False,
    "show_victory_popup": True
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
