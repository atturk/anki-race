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
    QComboBox,
    QPushButton,
    QRadioButton,
    Qt,
    QUrl,
    QTimer,
    QColor
)
from .race import race_manager

addon_package = __name__.split('.')[0]

def get_asset_url(filename: str) -> str:
    """Checks if a custom asset exists in user_files/, else falls back to default in web/assets/."""
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
    server_url = get_url() if get_url else "http://127.0.0.1/"
    
    for ext in ["png", "jpg", "svg"]:
        user_path = os.path.join(addon_dir, "user_files", f"{filename}.{ext}")
        if os.path.exists(user_path):
            return f"{server_url}_addons/{addon_package}/user_files/{filename}.{ext}"
    return f"{server_url}_addons/{addon_package}/web/assets/{filename}.svg"

class RaceBarWebView(AnkiWebView):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        from .config import race_config
        self.setFixedHeight(race_config.get("road_height", 70) + 18)
        self.set_bridge_command(self._handle_cmd, self)
        
        # Enable transparent background to allow confetti overlays to draw above reviewer content
        self.setStyleSheet("background: transparent;")
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        
    def load_race_html(self) -> None:
        """Loads the HTML document of the race bar served by Anki's server, inlining CSS and JS to bypass Qt WebEngine blocks."""
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(addon_dir, "web", "index.html")
        
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            # Inline CSS
            css_path = os.path.join(addon_dir, "web", "css", "race.css")
            if os.path.exists(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    css_data = f.read()
                html_content = html_content.replace(
                    '<link rel="stylesheet" href="css/race.css">',
                    f"<style>{css_data}</style>"
                )
                
            # Inline JS
            js_path = os.path.join(addon_dir, "web", "js", "race.js")
            if os.path.exists(js_path):
                with open(js_path, "r", encoding="utf-8") as f:
                    js_data = f.read()
                html_content = html_content.replace(
                    '<script src="js/race.js"></script>',
                    f"<script>{js_data}</script>"
                )
                
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
        
        current_deck_id = mw.col.decks.selected() if mw and mw.col else 1
        deck_name = "Mazzo"
        if mw and mw.col:
            try:
                deck = mw.col.decks.get(current_deck_id)
                deck_name = deck.get("name", "Mazzo")
            except:
                pass
        
        from .config import race_config
        
        # Override file URLs if custom file is selected
        cpu_file_name = race_config.get("car_cpu_file", "")
        if cpu_file_name:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_path = os.path.join(addon_dir, "user_files", cpu_file_name)
            if os.path.exists(user_path):
                get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
                server_url = get_url() if get_url else "http://127.0.0.1/"
                cpu_car_url = f"{server_url}_addons/{addon_package}/user_files/{cpu_file_name}"
                
        user_file_name = race_config.get("car_user_file", "")
        if user_file_name:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_path = os.path.join(addon_dir, "user_files", user_file_name)
            if os.path.exists(user_path):
                get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
                server_url = get_url() if get_url else "http://127.0.0.1/"
                user_car_url = f"{server_url}_addons/{addon_package}/user_files/{user_file_name}"
        
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
            "road_texture_url": road_texture_url,
            "advantage": race_manager.advantage,
            
            # Configurations
            "road_scrolling": race_config.get("road_scrolling", True),
            "road_height": race_config.get("road_height", 70),
            "car_cpu_offset_y": race_config.get("car_cpu_offset_y", 6),
            "car_user_offset_y": race_config.get("car_user_offset_y", 36),
            "car_cpu_type": race_config.get("car_cpu_type", "emoji"),
            "car_cpu_emoji": race_config.get("car_cpu_emoji", "🚓"),
            "car_cpu_flip": race_config.get("car_cpu_flip", True),
            "car_user_type": race_config.get("car_user_type", "emoji"),
            "car_user_emoji": race_config.get("car_user_emoji", "🏎️"),
            "car_user_flip": race_config.get("car_user_flip", False)
        }

    def _handle_cmd(self, cmd: str) -> Any:
        """Handles bridge signals sent from JavaScript inside the race bar."""
        if cmd == "anki_race_get_initial_state":
            state = self._get_state_dict()
            self.eval(f"if (window.initializeRace) {{ window.initializeRace({json.dumps(state)}); }}")
        elif cmd.startswith("anki_race_finished:"):
            result = cmd.split(":")[1]
            if result == "victory":
                self.trigger_victory_directly()
            else:
                race_manager.race_in_progress = False
                race_manager.race_paused = False
                self.hide() # Close the bar immediately
                # Show defeat popup (use singleShot to prevent web engine deadlock)
                QTimer.singleShot(100, self.show_defeat_popup)
                
        elif cmd.startswith("anki_race_toggle_minimize:"):
            is_minimized = cmd.split(":")[1] == "true"
            if is_minimized:
                self.setFixedHeight(18) # Collapse to show only the minimize tab
            else:
                from .config import race_config
                self.setFixedHeight(race_config.get("road_height", 70) + 18)
        return None

    def trigger_victory_directly(self) -> None:
        """Triggers victory confetti and popup directly from Python to prevent timing conflicts."""
        if not race_manager.race_in_progress:
            return
        race_manager.race_in_progress = False
        race_manager.race_paused = False
        self.hide() # Close the top bar immediately so it stops shifting layout
        from .config import race_config
        self.setFixedHeight(race_config.get("road_height", 70) + 18) # Reset height to standard
        
        # Inject confetti into Anki's main WebView immediately (0ms delay)
        QTimer.singleShot(0, self.inject_confetti_into_main_webview)
        # Show native popup immediately (50ms delay to ensure the confetti JS executes first)
        QTimer.singleShot(50, self.show_victory_popup)

    def inject_confetti_into_main_webview(self) -> None:
        """Injects CSS/JS confetti directly into Anki's main webview to celebrate victory."""
        if not mw or not mw.web:
            return
            
        js_code = """
        (function() {
            // Remove any existing overlay
            const oldOverlay = document.getElementById("victory-confetti-overlay");
            if (oldOverlay) oldOverlay.remove();

            // Inject Confetti CSS styles
            const style = document.createElement('style');
            style.id = "victory-confetti-style";
            style.innerHTML = `
                .confetti-particle {
                    position: fixed;
                    width: 9px;
                    height: 9px;
                    opacity: 0.85;
                    pointer-events: none;
                    z-index: 99999;
                }
                #victory-confetti-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.4);
                    pointer-events: none;
                    z-index: 99998;
                    transition: opacity 0.5s ease;
                    opacity: 1;
                }
            `;
            document.head.appendChild(style);

            // Create background dark overlay
            const overlay = document.createElement('div');
            overlay.id = "victory-confetti-overlay";
            document.body.appendChild(overlay);

            // Confetti generation physics
            const colors = ['#f1c40f', '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#e67e22'];
            const container = document.body;
            
            function createConfetti(x, y, angle, spread) {
                for (let i = 0; i < 45; i++) {
                    const p = document.createElement('div');
                    p.className = 'confetti-particle';
                    
                    const isCircle = Math.random() > 0.5;
                    const w = 8 + Math.random() * 12;
                    const h = isCircle ? w : 6 + Math.random() * 10;
                    
                    p.style.width = w + 'px';
                    p.style.height = h + 'px';
                    p.style.borderRadius = isCircle ? '50%' : '2px';
                    p.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                    p.style.left = x + 'px';
                    p.style.top = y + 'px';
                    
                    const a = angle + (Math.random() - 0.5) * spread;
                    const speed = 12 + Math.random() * 22;
                    p.vx = Math.cos(a) * speed;
                    p.vy = Math.sin(a) * speed - 7;
                    p.gravity = 0.38;
                    p.rotation = Math.random() * 360;
                    p.rotSpeed = (Math.random() - 0.5) * 15;
                    
                    container.appendChild(p);
                    
                    let ticks = 0;
                    const interval = setInterval(() => {
                        p.vx *= 0.97;
                        p.vy += p.gravity;
                        p.style.left = (parseFloat(p.style.left) + p.vx) + 'px';
                        p.style.top = (parseFloat(p.style.top) + p.vy) + 'px';
                        p.rotation += p.rotSpeed;
                        p.style.transform = `rotate(${p.rotation}deg)`;
                        
                        ticks++;
                        if (ticks > 120 || parseFloat(p.style.top) > window.innerHeight) {
                            clearInterval(interval);
                            p.remove();
                        }
                    }, 16);
                }
            }
            
            // Shoot from left and right corners
            createConfetti(0, window.innerHeight, -Math.PI / 4, Math.PI / 6);
            createConfetti(window.innerWidth, window.innerHeight, -3 * Math.PI / 4, Math.PI / 6);
            
            // Second burst
            setTimeout(() => {
                createConfetti(0, window.innerHeight, -Math.PI / 4, Math.PI / 6);
                createConfetti(window.innerWidth, window.innerHeight, -3 * Math.PI / 4, Math.PI / 6);
            }, 550);

            // Fade out and remove overlay
            setTimeout(() => {
                overlay.style.opacity = '0';
                setTimeout(() => {
                    overlay.remove();
                    const st = document.getElementById("victory-confetti-style");
                    if (st) st.remove();
                }, 500);
            }, 2200);
        })();
        """
        mw.web.eval(js_code)

    def show_victory_popup(self) -> None:
        """Displays the native Qt Victory dialog popup and resets widget layouts."""
        from aqt.utils import showInfo
        title = "Anki Race"
        if race_manager.mode == "fuga":
            showInfo("🏆 Vittoria!\n\nSei sfuggito all'inseguitore completando tutto il mazzo!", title=title)
        else:
            showInfo("🏆 Vittoria!\n\nHai battuto la CPU tagliando il traguardo per primo!", title=title)
        self.hide()
        from .config import race_config
        self.setFixedHeight(race_config.get("road_height", 70) + 18) # Reset height to standard

    def show_defeat_popup(self) -> None:
        """Displays the native Qt Defeat dialog popup."""
        from aqt.utils import showInfo
        title = "Anki Race"
        if race_manager.mode == "fuga":
            showInfo("💥 Game Over!\n\nL'inseguitore ti ha raggiunto! Fai più in fretta la prossima volta!", title=title)
        else:
            showInfo("💥 Game Over!\n\nLa CPU ha tagliato il traguardo prima di te. Riprova!", title=title)


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
        
        # Divider/Border
        line = QLabel()
        line.setStyleSheet("border-bottom: 1px solid #ccc; max-height: 1px;")
        layout.addWidget(line)
        
        # Mode Selection Header
        mode_header = QLabel("<b>Seleziona Modalità di Gioco:</b>")
        mode_header.setStyleSheet("font-size: 12px;")
        layout.addWidget(mode_header)
        
        # Mode Radio Buttons
        # Mode Radio Buttons
        from .config import race_config
        default_mode = race_config.get("default_mode", "normale")
        
        self.btn_normal = QRadioButton("Modalità Normale (Gara Standard)")
        self.btn_normal.setToolTip("La CPU avanza a velocità costante. Finisci il mazzo prima di essere battuto.")
        layout.addWidget(self.btn_normal)
        
        self.btn_escape = QRadioButton("Modalità Fuga (Inseguimento)")
        self.btn_escape.setToolTip("La CPU ti insegue. Fuggila completando tutto il mazzo prima di essere raggiunto!")
        layout.addWidget(self.btn_escape)
        
        if default_mode == "fuga":
            self.btn_escape.setChecked(True)
        else:
            self.btn_normal.setChecked(True)
            
        # Connect mode change to toggle advantage setting
        self.btn_escape.toggled.connect(self.on_mode_toggled)
        
        # Advantage Selection
        self.advantage_layout = QHBoxLayout()
        self.advantage_label = QLabel("<b>Vantaggio Iniziale:</b>")
        self.advantage_label.setStyleSheet("font-size: 12px; color: #555;")
        self.advantage_combo = QComboBox()
        self.advantage_combo.addItems(["10%", "20%", "30%", "40%", "50%"])
        
        default_adv = int(race_config.get("default_advantage", 30.0))
        self.advantage_combo.setCurrentText(f"{default_adv}%")
        self.advantage_combo.setEnabled(default_mode == "fuga") # Active only in Escape mode
        if default_mode == "fuga":
            self.advantage_label.setStyleSheet("font-size: 12px; color: #000;")
            
        self.advantage_layout.addWidget(self.advantage_label)
        self.advantage_layout.addWidget(self.advantage_combo)
        layout.addLayout(self.advantage_layout)
        
        # Time Selection Header
        time_header = QLabel("<b>Durata Gara (Tempo limite CPU):</b>")
        time_header.setStyleSheet("font-size: 12px; margin-top: 5px;")
        layout.addWidget(time_header)
        
        # Time SpinBox
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(1.0, 120.0)
        self.time_spin.setSingleStep(0.5)
        self.time_spin.setValue(race_config.get("default_time", 5.0))
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

    def on_mode_toggled(self, checked: bool) -> None:
        """Enables advantage setting if Escape mode is selected, else disables it."""
        self.advantage_combo.setEnabled(checked)
        color = "#000" if checked else "#555"
        self.advantage_label.setStyleSheet(f"font-size: 12px; color: {color};")

    def get_settings(self) -> Dict[str, Any]:
        """Returns the settings selected by the user."""
        mode = "normale" if self.btn_normal.isChecked() else "fuga"
        chosen_time = float(self.time_spin.value())
        
        # Convert e.g., "30%" to 30.0
        advantage_str = self.advantage_combo.currentText().replace("%", "")
        advantage = float(advantage_str) if mode == "fuga" else 0.0
        
        return {
            "mode": mode,
            "chosen_time": chosen_time,
            "advantage": advantage
        }
