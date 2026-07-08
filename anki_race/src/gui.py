import os
import json
from typing import Dict, Any, Optional
from aqt import mw
from aqt.webview import AnkiWebView
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QRadioButton,
    Qt,
    QUrl
)
from .race import race_manager

addon_package = __name__.split('.')[0]

def get_asset_url(filename: str) -> str:
    """Checks if a custom asset exists in user_files/, else falls back to default in web/assets/."""
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ext in ["png", "jpg", "svg"]:
        user_path = os.path.join(addon_dir, "user_files", f"{filename}.{ext}")
        if os.path.exists(user_path):
            return f"/_addons/{addon_package}/user_files/{filename}.{ext}"
    return f"/_addons/{addon_package}/web/assets/{filename}.svg"

class RaceBarWebView(AnkiWebView):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(110) # Set height of the persistent race bar widget
        self.set_bridge_command(self._handle_cmd, self)
        
    def load_race_html(self) -> None:
        """Loads the HTML document of the race bar served by Anki's server."""
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(addon_dir, "web", "index.html")
        
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
            server_url = get_url() if get_url else "http://127.0.0.1/"
            base_url = f"{server_url}_addons/{addon_package}/web/"
            
            self.setHtml(html_content, QUrl(base_url))
        except Exception as e:
            print(f"[AnkiRace] Error loading HTML: {e}")
        
    def update_state(self) -> None:
        """Pushes the updated state variables to the JavaScript frontend."""
        if not race_manager.race_in_progress:
            return
        state = self._get_state_dict()
        self.eval(f"if (window.updateRaceState) {{ window.updateRaceState({json.dumps(state)}); }}")

    def _get_state_dict(self) -> Dict[str, Any]:
        """Collects the complete current state of the race manager."""
        user_car_url = get_asset_url("car_user")
        cpu_car_url = get_asset_url("car_cpu")
        road_texture_url = get_asset_url("road_texture")
        
        current_deck_id = mw.col.decks.selected()
        deck = mw.col.decks.get(current_deck_id)
        deck_name = deck.get("name", "Mazzo")
        
        return {
            "user_position": race_manager.user_position,
            "cpu_position": race_manager.cpu_position,
            "total_cards": race_manager.total_cards,
            "remaining_cards": race_manager.remaining_cards,
            "mode": race_manager.mode,
            "chosen_time": race_manager.chosen_time,
            "race_in_progress": race_manager.race_in_progress,
            "start_time": race_manager.start_time,
            "deck_name": deck_name,
            "user_car_url": user_car_url,
            "cpu_car_url": cpu_car_url,
            "road_texture_url": road_texture_url
        }

    def _handle_cmd(self, cmd: str) -> Any:
        """Handles bridge signals sent from JavaScript inside the race bar."""
        if cmd == "anki_race_get_initial_state":
            state = self._get_state_dict()
            self.eval(f"if (window.initializeRace) {{ window.initializeRace({json.dumps(state)}); }}")
        elif cmd == "anki_race_finished":
            race_manager.race_in_progress = False
        elif cmd == "anki_race_close_overlay":
            self.hide()
        return None


class RaceSetupDialog(QDialog):
    def __init__(self, parent: Any, deck_name: str, due_cards: int) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configura Anki Race")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(340)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        self.setLayout(layout)
        
        # Info Panel
        info_label = QLabel(
            f"<b>Mazzo selezionato:</b> {deck_name}<br>"
            f"<b>Carte da completare:</b> {due_cards}"
        )
        info_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(info_label)
        
        # Divider/Border (styled via stylesheet)
        line = QLabel()
        line.setStyleSheet("border-bottom: 1px solid #ccc; max-height: 1px;")
        layout.addWidget(line)
        
        # Mode Selection Header
        mode_header = QLabel("<b>Seleziona Modalità di Gioco:</b>")
        mode_header.setStyleSheet("font-size: 12px;")
        layout.addWidget(mode_header)
        
        # Mode Radio Buttons
        self.btn_normal = QRadioButton("Modalità Normale (Gara Standard)")
        self.btn_normal.setChecked(True)
        self.btn_normal.setToolTip("La CPU avanza a velocità costante. Finisci il mazzo prima di essere battuto.")
        layout.addWidget(self.btn_normal)
        
        self.btn_escape = QRadioButton("Modalità Fuga (Inseguimento)")
        self.btn_escape.setToolTip("La CPU ti insegue e accelera col tempo. Fuggila rispondendo correttamente!")
        layout.addWidget(self.btn_escape)
        
        # Time Selection Header
        time_header = QLabel("<b>Durata Gara (Tempo limite CPU):</b>")
        time_header.setStyleSheet("font-size: 12px; margin-top: 5px;")
        layout.addWidget(time_header)
        
        # Time SpinBox
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 120)
        self.time_spin.setValue(5)
        self.time_spin.setSuffix(" minuti")
        layout.addWidget(self.time_spin)
        
        # Spacer
        layout.addSpacing(10)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.start_btn = QPushButton("Gareggia!")
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self.accept)
        self.start_btn.setStyleSheet("font-weight: bold;")
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

    def get_settings(self) -> Dict[str, Any]:
        """Returns the settings selected by the user."""
        mode = "normale" if self.btn_normal.isChecked() else "fuga"
        chosen_time = float(self.time_spin.value())
        return {
            "mode": mode,
            "chosen_time": chosen_time
        }
