import os
import shutil
import json
from typing import Any, Dict
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
from .config import race_config

addon_package = __name__.split('.')[0]

def is_emoji(char: str) -> bool:
    if not char:
        return False
    cp = ord(char)
    # Emojis are generally characters in these unicode blocks:
    if (0x1F300 <= cp <= 0x1F5FF or
        0x1F600 <= cp <= 0x1F64F or
        0x1F680 <= cp <= 0x1F6FF or
        0x1F900 <= cp <= 0x1F9FF or
        0x1FA70 <= cp <= 0x1FAFF or
        0x2600 <= cp <= 0x27BF or
        0x1F1E6 <= cp <= 0x1F1FF or
        cp == 0x20E3 or
        0xFE00 <= cp <= 0xFE0F):
        return True
    # Allow Zero-Width-Joiner and Variation Selectors
    if cp == 0x200D or cp == 0xFE0F:
        return True
    return False

class RaceConfigDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Personalizza Anki Race")
        self.resize(550, 650)
        self.setMinimumSize(500, 600)
        
        self.car_cpu_file_val = race_config.get("car_cpu_file", "")
        self.car_user_file_val = race_config.get("car_user_file", "")
        self.road_image_file_val = race_config.get("road_image_file", "")
        self.road_solid_color_val = race_config.get("road_solid_color", "#1e272e")
        self.preview_loaded = False
        
        self._init_ui()
        self._load_config_values()
        
        # Connect changes to update preview in real-time
        self._connect_signals()
        
        # Load the preview WebView
        self._load_preview_html()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 1. Preview Area (At the top of the dialog, visible across all custom edits)
        preview_box = QGroupBox("Anteprima Tracciato (Real-time)")
        preview_layout = QVBoxLayout()
        preview_box.setLayout(preview_layout)
        
        self.preview_webview = AnkiWebView(self)
        self.preview_webview.setFixedHeight(110)
        self.preview_webview.setStyleSheet("background: transparent;")
        self.preview_webview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        preview_layout.addWidget(self.preview_webview)
        main_layout.addWidget(preview_box)
        
        # 2. Tabs Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.tab_general = QWidget()
        self.tab_road_cars = QWidget()
        self.tab_support = QWidget()
        
        self.tabs.addTab(self.tab_general, "Generale")
        self.tabs.addTab(self.tab_road_cars, "Strada & Auto")
        self.tabs.addTab(self.tab_support, "Supporto")
        
        # Setup individual tabs content
        self._setup_general_tab()
        self._setup_road_cars_tab()
        self._setup_support_tab()
        
        # 3. Action Buttons (Save / Cancel)
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("Salva")
        self.save_btn.setDefault(True)
        self.cancel_btn = QPushButton("Annulla")
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        main_layout.addLayout(buttons_layout)
        
        # Connect actions
        self.save_btn.clicked.connect(self._save_config)
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_general_tab(self) -> None:
        layout = QVBoxLayout()
        self.tab_general.setLayout(layout)
        
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Show overview button
        self.overview_btn_cb = QCheckBox("Mostra il bottone 'Gareggia' nella schermata del mazzo")
        form_layout.addRow("Integrazione UI:", self.overview_btn_cb)
        
        # Default game mode
        self.default_mode_combo = QComboBox()
        self.default_mode_combo.addItems(["Normale", "Fuga"])
        form_layout.addRow("Modalità di default:", self.default_mode_combo)
        
        # Default time
        self.default_time_spin = QDoubleSpinBox()
        self.default_time_spin.setRange(1.0, 120.0)
        self.default_time_spin.setSingleStep(0.5)
        self.default_time_spin.setSuffix(" minuti")
        form_layout.addRow("Tempo di default:", self.default_time_spin)
        
        # Default headstart advantage
        self.default_advantage_combo = QComboBox()
        self.default_advantage_combo.addItems(["10%", "20%", "30%", "40%", "50%"])
        form_layout.addRow("Vantaggio default (Fuga):", self.default_advantage_combo)
        
        # Keyboard Shortcut Sequence Edit
        self.shortcut_edit = QKeySequenceEdit()
        form_layout.addRow("Scorciatoia avvio gara:", self.shortcut_edit)
        
        layout.addStretch()

    def _setup_road_cars_tab(self) -> None:
        # Wrap everything in a scroll area to prevent overflow on smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Form for road variables
        road_box = QGroupBox("Geometria della Strada")
        road_layout = QFormLayout()
        road_box.setLayout(road_layout)
        
        # Adjusted height slider range to 20 - 50 px as requested
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(20, 50)
        self.height_label = QLabel("35 px")
        self.height_slider.valueChanged.connect(lambda v: self.height_label.setText(f"{v} px"))
        
        height_widget = QHBoxLayout()
        height_widget.addWidget(self.height_slider)
        height_widget.addWidget(self.height_label)
        road_layout.addRow("Altezza strada (20px - 50px):", height_widget)
        
        scroll_layout.addWidget(road_box)
        
        # Form for road styling
        road_style_box = QGroupBox("Personalizzazione Stile Strada")
        road_style_layout = QFormLayout()
        road_style_box.setLayout(road_style_layout)
        
        self.road_style_combo = QComboBox()
        self.road_style_combo.addItems(["Immagine (Texture)", "Tinta Unita"])
        road_style_layout.addRow("Stile Sfondo:", self.road_style_combo)
        
        # Solid Color selection
        self.road_color_btn = QPushButton("Scegli Colore...")
        self.road_color_preview = QLabel("   ")
        self.road_color_preview.setFixedWidth(50)
        self.road_color_preview.setFrameShape(QFrame.Shape.Box)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.road_color_btn)
        color_layout.addWidget(self.road_color_preview)
        road_style_layout.addRow("Colore Sfondo:", color_layout)
        
        # Road texture file selection
        self.road_file_btn = QPushButton("Sfoglia texture...")
        self.road_file_label = QLabel("Nessun file selezionato")
        self.road_file_label.setStyleSheet("font-size: 10px; color: gray;")
        
        road_file_layout = QHBoxLayout()
        road_file_layout.addWidget(self.road_file_btn)
        road_file_layout.addWidget(self.road_file_label)
        road_style_layout.addRow("File Texture:", road_file_layout)
        
        self.road_style_combo.currentTextChanged.connect(self._toggle_road_style_widgets)
        self.road_color_btn.clicked.connect(self._choose_road_color)
        self.road_file_btn.clicked.connect(self._browse_road_file)
        
        scroll_layout.addWidget(road_style_box)
        
        # Form for car layouts
        cars_pos_box = QGroupBox("Corsie Automobili (Allineamento Y)")
        cars_pos_layout = QFormLayout()
        cars_pos_box.setLayout(cars_pos_layout)
        
        # Offset CPU (range -20 to 70)
        self.cpu_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.cpu_y_slider.setRange(-20, 70)
        self.cpu_y_label = QLabel("2 px")
        self.cpu_y_slider.valueChanged.connect(lambda v: self.cpu_y_label.setText(f"{v} px"))
        
        cpu_y_widget = QHBoxLayout()
        cpu_y_widget.addWidget(self.cpu_y_slider)
        cpu_y_widget.addWidget(self.cpu_y_label)
        cars_pos_layout.addRow("Offset CPU (Inseguitore):", cpu_y_widget)
        
        # Offset User (range -20 to 70)
        self.user_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.user_y_slider.setRange(-20, 70)
        self.user_y_label = QLabel("18 px")
        self.user_y_slider.valueChanged.connect(lambda v: self.user_y_label.setText(f"{v} px"))
        
        user_y_widget = QHBoxLayout()
        user_y_widget.addWidget(self.user_y_slider)
        user_y_widget.addWidget(self.user_y_label)
        cars_pos_layout.addRow("Offset Utente (Tua Auto):", user_y_widget)
        
        scroll_layout.addWidget(cars_pos_box)
        
        # Car overrides: CPU
        cpu_box = QGroupBox("Icona CPU (Avversario/Inseguitore)")
        cpu_box_layout = QFormLayout()
        cpu_box.setLayout(cpu_box_layout)
        
        self.cpu_type_combo = QComboBox()
        self.cpu_type_combo.addItems(["Emoji", "Immagine personalizzata"])
        cpu_box_layout.addRow("Tipo:", self.cpu_type_combo)
        
        # Changed CPU emoji input to QLineEdit with emoji validator
        self.cpu_emoji_input = QLineEdit()
        self.cpu_emoji_input.setPlaceholderText("Incolla o digita emoji qui...")
        cpu_box_layout.addRow("Emoji:", self.cpu_emoji_input)
        self.cpu_emoji_input.textChanged.connect(self._on_cpu_emoji_changed)
        
        self.cpu_file_btn = QPushButton("Sfoglia immagine...")
        self.cpu_file_label = QLabel("Nessun file selezionato")
        self.cpu_file_label.setStyleSheet("font-size: 10px; color: gray;")
        cpu_file_widget = QHBoxLayout()
        cpu_file_widget.addWidget(self.cpu_file_btn)
        cpu_file_widget.addWidget(self.cpu_file_label)
        cpu_box_layout.addRow("File:", cpu_file_widget)
        
        self.cpu_flip_cb = QCheckBox("Specchia / Inverti direzione orizzontale")
        cpu_box_layout.addRow("Orientamento:", self.cpu_flip_cb)
        
        scroll_layout.addWidget(cpu_box)
        
        # Car overrides: USER
        user_box = QGroupBox("Icona Utente (Tua Auto)")
        user_box_layout = QFormLayout()
        user_box.setLayout(user_box_layout)
        
        self.user_type_combo = QComboBox()
        self.user_type_combo.addItems(["Emoji", "Immagine personalizzata"])
        user_box_layout.addRow("Tipo:", self.user_type_combo)
        
        # Changed User emoji input to QLineEdit with emoji validator
        self.user_emoji_input = QLineEdit()
        self.user_emoji_input.setPlaceholderText("Incolla o digita emoji qui...")
        user_box_layout.addRow("Emoji:", self.user_emoji_input)
        self.user_emoji_input.textChanged.connect(self._on_user_emoji_changed)
        
        self.user_file_btn = QPushButton("Sfoglia immagine...")
        self.user_file_label = QLabel("Nessun file selezionato")
        self.user_file_label.setStyleSheet("font-size: 10px; color: gray;")
        user_file_widget = QHBoxLayout()
        user_file_widget.addWidget(self.user_file_btn)
        user_file_widget.addWidget(self.user_file_label)
        user_box_layout.addRow("File:", user_file_widget)
        
        self.user_flip_cb = QCheckBox("Specchia / Inverti direzione orizzontale")
        user_box_layout.addRow("Orientamento:", self.user_flip_cb)
        
        scroll_layout.addWidget(user_box)
        
        # Connect type toggle visibility
        self.cpu_type_combo.currentTextChanged.connect(self._toggle_cpu_widgets)
        self.user_type_combo.currentTextChanged.connect(self._toggle_user_widgets)
        
        self.cpu_file_btn.clicked.connect(self._browse_cpu_file)
        self.user_file_btn.clicked.connect(self._browse_user_file)
        
        scroll.setWidget(scroll_content)
        
        layout = QVBoxLayout()
        layout.addWidget(scroll)
        self.tab_road_cars.setLayout(layout)

    def _setup_support_tab(self) -> None:
        layout = QVBoxLayout()
        self.tab_support.setLayout(layout)
        
        info_label = QLabel()
        info_label.setOpenExternalLinks(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True) # Word Wrap enabled to adapt to dialog resizing
        info_label.setText("""
        <h3>Anki Race Add-on</h3>
        <p><b>Versione:</b> 1.0.0</p>
        <p>Gamifica lo studio quotidiano trasformando i tuoi ripassi in una gara automobilistica in tempo reale!</p>
        <hr/>
        <h4>Come personalizzare gli Asset:</h4>
        <ul>
          <li>Puoi selezionare emoji o caricare file personalizzati direttamente in questo pannello.</li>
          <li>I file supportati sono <b>PNG, JPG, JPEG, SVG</b>.</li>
          <li>Per ottenere prestazioni migliori, usa immagini con sfondo trasparente (.png o .svg).</li>
        </ul>
        <hr/>
        <p>Sviluppato con ❤️ per rendere lo studio divertente e motivante.</p>
        """)
        layout.addWidget(info_label)
        layout.addStretch()

    def _on_cpu_emoji_changed(self, text: str) -> None:
        # Filter input to contain only emoji characters
        cleaned = "".join([c for c in text if is_emoji(c)])
        if cleaned != text:
            self.cpu_emoji_input.blockSignals(True)
            self.cpu_emoji_input.setText(cleaned)
            self.cpu_emoji_input.blockSignals(False)
        self.update_preview()

    def _on_user_emoji_changed(self, text: str) -> None:
        # Filter input to contain only emoji characters
        cleaned = "".join([c for c in text if is_emoji(c)])
        if cleaned != text:
            self.user_emoji_input.blockSignals(True)
            self.user_emoji_input.setText(cleaned)
            self.user_emoji_input.blockSignals(False)
        self.update_preview()

    def _toggle_cpu_widgets(self, text: str) -> None:
        is_emoji = text == "Emoji"
        self.cpu_emoji_input.setEnabled(is_emoji)
        self.cpu_file_btn.setEnabled(not is_emoji)

    def _toggle_user_widgets(self, text: str) -> None:
        is_emoji = text == "Emoji"
        self.user_emoji_input.setEnabled(is_emoji)
        self.user_file_btn.setEnabled(not is_emoji)

    def _toggle_road_style_widgets(self, text: str) -> None:
        is_solid = text == "Tinta Unita"
        self.road_color_btn.setEnabled(is_solid)
        self.road_file_btn.setEnabled(not is_solid)

    def _choose_road_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.road_solid_color_val), self, "Seleziona Colore Strada")
        if color.isValid():
            self.road_solid_color_val = color.name()
            self.road_color_preview.setStyleSheet(f"background-color: {self.road_solid_color_val};")
            self.update_preview()

    def _browse_road_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Texture Strada", "", "Immagini (*.png *.jpg *.jpeg)"
        )
        if file_path:
            filename = os.path.basename(file_path)
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(addon_dir, "user_files")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(file_path, dest_path)
            
            self.road_image_file_val = filename
            self.road_file_label.setText(filename)
            self.update_preview()

    def _load_config_values(self) -> None:
        # Tab 1: Generale
        self.overview_btn_cb.setChecked(race_config.get("show_overview_button", True))
        
        mode = race_config.get("default_mode", "normale")
        self.default_mode_combo.setCurrentText("Fuga" if mode == "fuga" else "Normale")
        self.default_time_spin.setValue(race_config.get("default_time", 5.0))
        
        adv = int(race_config.get("default_advantage", 30.0))
        self.default_advantage_combo.setCurrentText(f"{adv}%")
        
        # Shortcut key sequence
        shortcut_str = race_config.get("shortcut", "Ctrl+R")
        self.shortcut_edit.setKeySequence(QKeySequence(shortcut_str))
        
        # Tab 2: Strada e Auto
        self.height_slider.setValue(race_config.get("road_height", 35))
        self.cpu_y_slider.setValue(race_config.get("car_cpu_offset_y", 2))
        self.user_y_slider.setValue(race_config.get("car_user_offset_y", 18))
        
        style = race_config.get("road_style", "image")
        self.road_style_combo.setCurrentText("Tinta Unita" if style == "solid" else "Immagine (Texture)")
        self.road_color_preview.setStyleSheet(f"background-color: {self.road_solid_color_val};")
        self.road_file_label.setText(self.road_image_file_val if self.road_image_file_val else "Nessun file selezionato")
        
        cpu_type = "Emoji" if race_config.get("car_cpu_type", "emoji") == "emoji" else "Immagine personalizzata"
        self.cpu_type_combo.setCurrentText(cpu_type)
        self.cpu_emoji_input.setText(race_config.get("car_cpu_emoji", "🚓"))
        self.cpu_flip_cb.setChecked(race_config.get("car_cpu_flip", True))
        self.cpu_file_label.setText(self.car_cpu_file_val if self.car_cpu_file_val else "Nessun file selezionato")
        
        user_type = "Emoji" if race_config.get("car_user_type", "emoji") == "emoji" else "Immagine personalizzata"
        self.user_type_combo.setCurrentText(user_type)
        self.user_emoji_input.setText(race_config.get("car_user_emoji", "🏎️"))
        self.user_flip_cb.setChecked(race_config.get("car_user_flip", False))
        self.user_file_label.setText(self.car_user_file_val if self.car_user_file_val else "Nessun file selezionato")
        
        # Trigger visibility toggles
        self._toggle_cpu_widgets(cpu_type)
        self._toggle_user_widgets(user_type)
        self._toggle_road_style_widgets(self.road_style_combo.currentText())

    def _connect_signals(self) -> None:
        # Re-render preview whenever values are modified
        widgets = [
            self.overview_btn_cb, self.cpu_flip_cb, self.user_flip_cb,
            self.height_slider, self.cpu_y_slider, self.user_y_slider
        ]
        for w in widgets:
            if isinstance(w, QSlider):
                w.valueChanged.connect(self._on_widget_changed)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self._on_widget_changed)
                
        combos = [
            self.cpu_type_combo, self.user_type_combo, self.road_style_combo
        ]
        for c in combos:
            c.currentTextChanged.connect(self._on_widget_changed)

    def _on_widget_changed(self, *args: Any) -> None:
        self.update_preview()

    def _load_preview_html(self) -> None:
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(addon_dir, "web", "index.html")
        
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            # Inline CSS
            css_path = os.path.join(addon_dir, "web", "css", "race.css")
            if os.path.exists(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    html_content = html_content.replace(
                        '<link rel="stylesheet" href="css/race.css">',
                        f"<style>{f.read()}</style>"
                    )
            # Inline JS
            js_path = os.path.join(addon_dir, "web", "js", "race.js")
            if os.path.exists(js_path):
                with open(js_path, "r", encoding="utf-8") as f:
                    html_content = html_content.replace(
                        '<script src="js/race.js"></script>',
                        f"<script>{f.read()}</script>"
                    )
            
            get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
            server_url = get_url() if get_url else "http://127.0.0.1/"
            base_url = f"{server_url}_addons/{addon_package}/web/"
            
            self.preview_webview.setHtml(html_content, QUrl(base_url))
            self.preview_webview.page().loadFinished.connect(self._on_preview_loaded)
        except Exception as e:
            print(f"[AnkiRaceConfig] Error loading preview WebView: {e}")

    def _on_preview_loaded(self, ok: bool) -> None:
        self.preview_loaded = True
        self.update_preview()

    def _get_dialog_state_dict(self) -> Dict[str, Any]:
        from .gui import get_asset_url
        user_car_url = get_asset_url("car_user")
        cpu_car_url = get_asset_url("car_cpu")
        road_texture_url = get_asset_url("road_texture")
        
        # Override file URLs if custom file is selected
        cpu_file = self.car_cpu_file_val
        if cpu_file:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_path = os.path.join(addon_dir, "user_files", cpu_file)
            if os.path.exists(user_path):
                get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
                server_url = get_url() if get_url else "http://127.0.0.1/"
                cpu_car_url = f"{server_url}_addons/{addon_package}/user_files/{cpu_file}"
                
        user_file = self.car_user_file_val
        if user_file:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_path = os.path.join(addon_dir, "user_files", user_file)
            if os.path.exists(user_path):
                get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
                server_url = get_url() if get_url else "http://127.0.0.1/"
                user_car_url = f"{server_url}_addons/{addon_package}/user_files/{user_file}"

        # Resolve custom road texture image file
        road_image_name = self.road_image_file_val
        if road_image_name:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_path = os.path.join(addon_dir, "user_files", road_image_name)
            if os.path.exists(user_path):
                get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
                server_url = get_url() if get_url else "http://127.0.0.1/"
                road_texture_url = f"{server_url}_addons/{addon_package}/user_files/{road_image_name}"

        return {
            "user_position": 60.0,
            "cpu_position": 25.0,
            "total_cards": 100,
            "remaining_cards": 40,
            "mode": "normale",
            "chosen_time": 5,
            "race_in_progress": True,
            "start_time": 0,
            "deck_name": "Anteprima",
            "user_car_url": user_car_url,
            "cpu_car_url": cpu_car_url,
            "road_texture_url": road_texture_url,
            "advantage": 0,
            
            # Form values
            "road_scrolling": False,
            "road_height": self.height_slider.value(),
            "car_cpu_offset_y": self.cpu_y_slider.value(),
            "car_user_offset_y": self.user_y_slider.value(),
            "car_cpu_type": "emoji" if self.cpu_type_combo.currentText() == "Emoji" else "file",
            "car_cpu_emoji": self.cpu_emoji_input.text(),
            "car_cpu_flip": self.cpu_flip_cb.isChecked(),
            "car_user_type": "emoji" if self.user_type_combo.currentText() == "Emoji" else "file",
            "car_user_emoji": self.user_emoji_input.text(),
            "car_user_flip": self.user_flip_cb.isChecked(),
            "road_style": "solid" if self.road_style_combo.currentText() == "Tinta Unita" else "image",
            "road_solid_color": self.road_solid_color_val,
            "road_image_file": self.road_image_file_val,
            "is_preview": True
        }

    def update_preview(self) -> None:
        if not self.preview_loaded:
            return
        state = self._get_dialog_state_dict()
        self.preview_webview.eval(f"if (window.updateRaceState) {{ window.updateRaceState({json.dumps(state)}); }}")

    def _browse_cpu_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Immagine CPU", "", "Immagini (*.png *.jpg *.jpeg *.svg)"
        )
        if file_path:
            filename = os.path.basename(file_path)
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(addon_dir, "user_files")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(file_path, dest_path)
            
            self.car_cpu_file_val = filename
            self.cpu_file_label.setText(filename)
            self.update_preview()

    def _browse_user_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Immagine Utente", "", "Immagini (*.png *.jpg *.jpeg *.svg)"
        )
        if file_path:
            filename = os.path.basename(file_path)
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(addon_dir, "user_files")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(file_path, dest_path)
            
            self.car_user_file_val = filename
            self.user_file_label.setText(filename)
            self.update_preview()

    def _save_config(self) -> None:
        # Collect parameters
        mode_text = self.default_mode_combo.currentText().lower()
        adv_text = self.default_advantage_combo.currentText().replace("%", "")
        
        updates = {
            "road_scrolling": False,
            "show_overview_button": self.overview_btn_cb.isChecked(),
            "default_mode": mode_text,
            "default_time": self.default_time_spin.value(),
            "default_advantage": float(adv_text),
            "road_height": self.height_slider.value(),
            "car_cpu_offset_y": self.cpu_y_slider.value(),
            "car_user_offset_y": self.user_y_slider.value(),
            "car_cpu_type": "emoji" if self.cpu_type_combo.currentText() == "Emoji" else "file",
            "car_cpu_emoji": self.cpu_emoji_input.text(),
            "car_cpu_flip": self.cpu_flip_cb.isChecked(),
            "car_cpu_file": self.car_cpu_file_val,
            "car_user_type": "emoji" if self.user_type_combo.currentText() == "Emoji" else "file",
            "car_user_emoji": self.user_emoji_input.text(),
            "car_user_flip": self.user_flip_cb.isChecked(),
            "car_user_file": self.car_user_file_val,
            "road_style": "solid" if self.road_style_combo.currentText() == "Tinta Unita" else "image",
            "road_solid_color": self.road_solid_color_val,
            "road_image_file": self.road_image_file_val,
            "shortcut": self.shortcut_edit.keySequence().toString()
        }
        
        race_config.update(updates)
        
        # Apply updates to active widgets in Anki if visible
        from .hooks import race_bar_widget, register_shortcut
        if race_bar_widget and race_bar_widget.isVisible():
            race_bar_widget.setFixedHeight(updates["road_height"] + 18)
            race_bar_widget.update_state()
            
        # Re-register the shortcut in case it changed
        register_shortcut()
        
        self.accept()
