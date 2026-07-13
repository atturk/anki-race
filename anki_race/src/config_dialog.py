import os
import shutil
import json
from typing import Any, Dict
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
from .config import race_config
from .gui import VICTORY_DONATION_PHRASES, VICTORY_RATING_PHRASES

# Formatting constants for the bottom support tab
BOTTOM_TABS_HEIGHT = 80
BOTTOM_SUPPORT_FONT_SIZE = 13
BOTTOM_SUPPORT_LINE_HEIGHT = 0.25
BOTTOM_SUPPORT_ICON_SIZE = 15

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
        self.setWindowTitle("Customize Anki Race")
        self.resize(715, 650)
        self.setMinimumSize(715, 600)
        
        self.car_cpu_file_val = race_config.get("car_cpu_file", "")
        self.car_user_file_val = race_config.get("car_user_file", "")
        self.road_image_file_val = race_config.get("road_image_file", "")
        self.decor_image_file_val = race_config.get("decor_image_file", "")
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
        preview_box = QGroupBox("Track Preview (Real-time)")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(5, 5, 5, 5)
        preview_layout.setSpacing(0)
        preview_box.setLayout(preview_layout)
        
        self.preview_webview = AnkiWebView(self)
        self.preview_webview.setFixedHeight(70)
        self.preview_webview.setStyleSheet("background: transparent;")
        self.preview_webview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        preview_layout.addWidget(self.preview_webview)
        main_layout.addWidget(preview_box)
        
        # 2. Tabs Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.tab_general = QWidget()
        self.tab_graphics = QWidget()
        self.tab_info = QWidget()
        
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_graphics, "Graphics")
        self.tabs.addTab(self.tab_info, "Info")
        
        # Setup individual tabs content
        self._setup_general_tab()
        self._setup_graphics_tab()
        self._setup_info_tab()
        
        # 2b. Bottom Tabs Widget (Supporto & Texture Extra)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setFixedHeight(BOTTOM_TABS_HEIGHT)
        
        # Tab 1: Supporto
        tab_support = QWidget()
        support_layout = QVBoxLayout()
        support_layout.setContentsMargins(10, 4, 10, 4)
        support_layout.setSpacing(4)
        tab_support.setLayout(support_layout)
        
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assets_dir = os.path.join(addon_dir, "web", "assets")
        bmac_path = os.path.join(assets_dir, "buymeacoffee.svg")
        kofi_path = os.path.join(assets_dir, "ko-fi.svg")
        tipeee_path = os.path.join(assets_dir, "tipeee.svg")
        
        import random
        donation_phrase = random.choice(VICTORY_DONATION_PHRASES)
        rating_phrase = random.choice(VICTORY_RATING_PHRASES)
        
        is_night = False
        try:
            from aqt.theme import theme_manager
            is_night = theme_manager.night_mode
        except Exception:
            pass
        text_color = "#cccccc" if is_night else "#333333"
        
        support_label = QLabel()
        support_label.setOpenExternalLinks(True)
        support_label.setTextFormat(Qt.TextFormat.RichText)
        support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_label.setWordWrap(True)
        support_label.setStyleSheet(f"font-size: {BOTTOM_SUPPORT_FONT_SIZE}px; color: {text_color}; background: transparent; border: none;")
        
        donation_html = (
            f"<div>"
            f"{donation_phrase} "
            f"<a href='https://buymeacoffee.com/hhrhrdbr6ys'><img src='file:///{bmac_path}' width='{BOTTOM_SUPPORT_ICON_SIZE}' height='{BOTTOM_SUPPORT_ICON_SIZE}' style='vertical-align: baseline; margin: 0 5px;' /></a> "
            f"<a href='https://it.tipeee.com/ankilius/'><img src='file:///{tipeee_path}' width='{BOTTOM_SUPPORT_ICON_SIZE}' height='{BOTTOM_SUPPORT_ICON_SIZE}' style='vertical-align: baseline; margin: 0 5px;' /></a> "
            f"<a href='https://ko-fi.com/ankilius'><img src='file:///{kofi_path}' width='{BOTTOM_SUPPORT_ICON_SIZE}' height='{BOTTOM_SUPPORT_ICON_SIZE}' style='vertical-align: baseline; margin: 0 5px;' /></a>"
            f"</div>"
        )
        
        link_html = f"<a href='https://ankiweb.net/shared/info/anki-race-placeholder'>rate it on AnkiWeb</a>"
        rating_html = rating_phrase.format(link=link_html)
        
        combined_html = (
            f"<div style='line-height: {BOTTOM_SUPPORT_LINE_HEIGHT};'>"
            f"{donation_html}"
            f"<div style='margin-top: 1em;'>{rating_html}</div>"
            f"</div>"
        )
        support_label.setText(combined_html)
        support_layout.addWidget(support_label)
        self.bottom_tabs.addTab(tab_support, "Support")
        
        # Tab 2: Texture Extra
        tab_extra = QWidget()
        extra_layout = QVBoxLayout()
        extra_layout.setContentsMargins(5, 2, 5, 2)
        tab_extra.setLayout(extra_layout)
        
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gif_path = os.path.join(assets_dir, "coming-soon.gif")
        
        new_height = 50
        new_width = 200
        from aqt.qt import QImageReader
        reader = QImageReader(gif_path)
        orig_size = reader.size()
        if orig_size.isValid() and orig_size.height() > 0:
            aspect_ratio = orig_size.width() / orig_size.height()
            new_width = int(new_height * aspect_ratio)
            
        gif_label.setFixedHeight(new_height)
        gif_label.setFixedWidth(new_width)
        gif_label.setScaledContents(True)
        
        self.coming_soon_movie = QMovie(gif_path)
        self.coming_soon_movie.setScaledSize(QSize(new_width, new_height))
        gif_label.setMovie(self.coming_soon_movie)
        self.coming_soon_movie.start()
        extra_layout.addWidget(gif_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.bottom_tabs.addTab(tab_extra, "Extra Textures")
        
        main_layout.addWidget(self.bottom_tabs)
        
        # 3. Action Buttons (Save / Cancel)
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.cancel_btn = QPushButton("Cancel")
        
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
        self.overview_btn_cb = QCheckBox("Show 'Race' / 'Stop Race' button on deck overview screen")
        form_layout.addRow(self.overview_btn_cb)
        
        # Default game mode
        self.default_mode_combo = QComboBox()
        self.default_mode_combo.addItems(["Normal", "Escape"])
        form_layout.addRow("Default mode", self.default_mode_combo)
        
        # Default time
        self.default_time_spin = QDoubleSpinBox()
        self.default_time_spin.setRange(1.0, 120.0)
        self.default_time_spin.setSingleStep(0.5)
        self.default_time_spin.setSuffix(" minutes")
        form_layout.addRow("Default duration", self.default_time_spin)
        
        # Default headstart advantage
        self.default_advantage_combo = QComboBox()
        self.default_advantage_combo.addItems(["10%", "20%", "30%", "40%", "50%"])
        form_layout.addRow("Default advantage (Escape)", self.default_advantage_combo)
        
        # Keyboard Shortcut Sequence Edit
        self.shortcut_edit = QKeySequenceEdit()
        form_layout.addRow("Shortcut to start race", self.shortcut_edit)
        
        # Action when leaving the deck
        self.deck_leave_combo = QComboBox()
        self.deck_leave_combo.addItems([
            "keep race running",
            "pause active race",
            "stop active race"
        ])
        form_layout.addRow("Action on leaving deck", self.deck_leave_combo)
        
        # Show active race flag in deck list
        self.show_flag_cb = QCheckBox("Show active race flag next to active decks")
        form_layout.addRow(self.show_flag_cb)
        
        # Show victory popup option
        self.show_victory_popup_cb = QCheckBox("Show victory popup and trigger confetti at the finish line")
        form_layout.addRow(self.show_victory_popup_cb)
        
        # Show support links in victory popup option
        self.show_support_in_victory_popup_cb = QCheckBox("Show donation and voting links in the victory popup")
        self.show_support_in_victory_popup_cb.setStyleSheet("margin-left: 20px;")
        form_layout.addRow(self.show_support_in_victory_popup_cb)
        
        # Connect victory popup checkbox to toggle support links checkbox
        self.show_victory_popup_cb.toggled.connect(self.show_support_in_victory_popup_cb.setEnabled)
        
        # Show defeat popup option
        self.show_defeat_popup_cb = QCheckBox("Show defeat popup when the CPU crosses the finish line first")
        form_layout.addRow(self.show_defeat_popup_cb)
        
        layout.addStretch()

    def _setup_info_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        info_text = QLabel()
        info_text.setOpenExternalLinks(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setWordWrap(True)
        
        # Load info.md from assets dynamically
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        info_md_path = os.path.join(addon_dir, "web", "assets", "info.md")
        
        markdown_content = ""
        if os.path.exists(info_md_path):
            try:
                with open(info_md_path, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
            except Exception as e:
                markdown_content = f"# Error\nUnable to read the info file: {e}"
        else:
            markdown_content = "# Error\nFile `info.md` not found in assets."
            
        doc = QTextDocument()
        doc.setMarkdown(markdown_content)
        info_text.setText(doc.toHtml())
        
        layout.addWidget(info_text)
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.tab_info.setLayout(main_layout)
    def _setup_graphics_tab(self) -> None:
        # Wrap everything in a scroll area to prevent overflow on smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Form for road variables
        road_box = QGroupBox("General bar height")
        road_layout = QFormLayout()
        road_box.setLayout(road_layout)
        
        # Adjusted height slider range to 20 - 70 px
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(20, 70)
        self.height_label = QLabel("35 px")
        self.height_slider.valueChanged.connect(lambda v: self.height_label.setText(f"{v} px"))
        
        height_widget = QHBoxLayout()
        height_widget.addWidget(self.height_slider)
        height_widget.addWidget(self.height_label)
        road_layout.addRow("General bar height", height_widget)
        
        scroll_layout.addWidget(road_box)
        
        # 4. Vehicle Tabs Widget (Tu & Avversario) - Form layouts directly inside tabs without groupboxes
        self.vehicle_tabs = QTabWidget()
        
        # Tab A: Tu (User)
        tab_user = QWidget()
        user_tab_layout = QFormLayout()
        tab_user.setLayout(user_tab_layout)
        
        self.user_type_combo = QComboBox()
        self.user_type_combo.addItems(["Emoji", "Custom Image"])
        user_tab_layout.addRow("Type", self.user_type_combo)
        
        self.user_emoji_input = QLineEdit()
        self.user_emoji_input.setPlaceholderText("Paste or type emoji here...")
        user_tab_layout.addRow("Emoji", self.user_emoji_input)
        self.user_emoji_input.textChanged.connect(self._on_user_emoji_changed)
        
        self.user_file_btn = QPushButton("Browse Image...")
        self.user_file_label = QLabel("No file selected")
        self.user_file_label.setStyleSheet("font-size: 10px; color: gray;")
        user_file_widget = QHBoxLayout()
        user_file_widget.addWidget(self.user_file_btn)
        user_file_widget.addWidget(self.user_file_label)
        user_tab_layout.addRow("File", user_file_widget)
        
        self.user_flip_cb = QCheckBox("Mirror / Flip horizontal direction")
        user_tab_layout.addRow(self.user_flip_cb)
        
        # Offset User (range -70 to 70)
        self.user_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.user_y_slider.setRange(-70, 70)
        self.user_y_label = QLabel("18 px")
        self.user_y_slider.valueChanged.connect(lambda v: self.user_y_label.setText(f"{v} px"))
        user_y_widget = QHBoxLayout()
        user_y_widget.addWidget(self.user_y_slider)
        user_y_widget.addWidget(self.user_y_label)
        user_tab_layout.addRow("Position", user_y_widget)
        
        # Size User (range 15 to 100)
        self.user_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.user_size_slider.setRange(15, 100)
        self.user_size_label = QLabel("32 px")
        self.user_size_slider.valueChanged.connect(lambda v: self.user_size_label.setText(f"{v} px"))
        user_size_widget = QHBoxLayout()
        user_size_widget.addWidget(self.user_size_slider)
        user_size_widget.addWidget(self.user_size_label)
        user_tab_layout.addRow("Size", user_size_widget)

        # Nitro boost option
        self.nitro_enabled_cb = QCheckBox("Nitro boost")
        user_tab_layout.addRow(self.nitro_enabled_cb)
        
        self.nitro_cards_spin = QSpinBox()
        self.nitro_cards_spin.setRange(1, 50)
        self.nitro_cards_spin.setSuffix(" cards")
        self.nitro_cards_spin.setValue(5)
        user_tab_layout.addRow("Activate after", self.nitro_cards_spin)
        self.nitro_enabled_cb.stateChanged.connect(self._toggle_nitro_widgets)
        
        self.vehicle_tabs.addTab(tab_user, "You")
        
        # Tab B: Avversario (CPU)
        tab_cpu = QWidget()
        cpu_tab_layout = QFormLayout()
        tab_cpu.setLayout(cpu_tab_layout)
        
        self.cpu_type_combo = QComboBox()
        self.cpu_type_combo.addItems(["Emoji", "Custom Image"])
        cpu_tab_layout.addRow("Type", self.cpu_type_combo)
        
        self.cpu_emoji_input = QLineEdit()
        self.cpu_emoji_input.setPlaceholderText("Paste or type emoji here...")
        cpu_tab_layout.addRow("Emoji", self.cpu_emoji_input)
        self.cpu_emoji_input.textChanged.connect(self._on_cpu_emoji_changed)
        
        self.cpu_file_btn = QPushButton("Browse Image...")
        self.cpu_file_label = QLabel("No file selected")
        self.cpu_file_label.setStyleSheet("font-size: 10px; color: gray;")
        cpu_file_widget = QHBoxLayout()
        cpu_file_widget.addWidget(self.cpu_file_btn)
        cpu_file_widget.addWidget(self.cpu_file_label)
        cpu_tab_layout.addRow("File", cpu_file_widget)
        
        self.cpu_flip_cb = QCheckBox("Mirror / Flip horizontal direction")
        cpu_tab_layout.addRow(self.cpu_flip_cb)

        # Offset CPU (range -70 to 70)
        self.cpu_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.cpu_y_slider.setRange(-70, 70)
        self.cpu_y_label = QLabel("2 px")
        self.cpu_y_slider.valueChanged.connect(lambda v: self.cpu_y_label.setText(f"{v} px"))
        cpu_y_widget = QHBoxLayout()
        cpu_y_widget.addWidget(self.cpu_y_slider)
        cpu_y_widget.addWidget(self.cpu_y_label)
        cpu_tab_layout.addRow("Position", cpu_y_widget)
        
        # Size CPU (range 15 to 100)
        self.cpu_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.cpu_size_slider.setRange(15, 100)
        self.cpu_size_label = QLabel("32 px")
        self.cpu_size_slider.valueChanged.connect(lambda v: self.cpu_size_label.setText(f"{v} px"))
        cpu_size_widget = QHBoxLayout()
        cpu_size_widget.addWidget(self.cpu_size_slider)
        cpu_size_widget.addWidget(self.cpu_size_label)
        cpu_tab_layout.addRow("Size", cpu_size_widget)
        
        self.vehicle_tabs.addTab(tab_cpu, "Opponent")
        
        scroll_layout.addWidget(self.vehicle_tabs)
        
        # Connect type toggle visibility & click actions
        self.cpu_type_combo.currentTextChanged.connect(self._toggle_cpu_widgets)
        self.user_type_combo.currentTextChanged.connect(self._toggle_user_widgets)
        
        self.cpu_file_btn.clicked.connect(self._browse_cpu_file)
        self.user_file_btn.clicked.connect(self._browse_user_file)

        # 5. Nested Road Tabs Widget (Strada & Strada avanzato) - Form layouts directly inside tabs without groupboxes
        self.road_tabs = QTabWidget()
        
        # Tab A: Strada
        tab_road = QWidget()
        road_tab_layout = QFormLayout()
        tab_road.setLayout(road_tab_layout)
        
        self.road_style_combo = QComboBox()
        self.road_style_combo.addItems(["Image (Texture)", "Solid Color"])
        road_tab_layout.addRow("Background Style", self.road_style_combo)
        
        self.road_color_btn = QPushButton("Choose Color...")
        self.road_color_preview = QLabel("   ")
        self.road_color_preview.setFixedWidth(50)
        self.road_color_preview.setFrameShape(QFrame.Shape.Box)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.road_color_btn)
        color_layout.addWidget(self.road_color_preview)
        road_tab_layout.addRow("Background Color", color_layout)
        
        self.road_file_btn = QPushButton("Browse texture...")
        self.road_file_label = QLabel("No file selected")
        self.road_file_label.setStyleSheet("font-size: 10px; color: gray;")
        
        road_file_layout = QHBoxLayout()
        road_file_layout.addWidget(self.road_file_btn)
        road_file_layout.addWidget(self.road_file_label)
        road_tab_layout.addRow("Texture File", road_file_layout)
        
        self.road_style_combo.currentTextChanged.connect(self._toggle_road_style_widgets)
        self.road_color_btn.clicked.connect(self._choose_road_color)
        self.road_file_btn.clicked.connect(self._browse_road_file)
        
        self.road_tabs.addTab(tab_road, "Background")
        
        # Tab B: Strada (avanzato)
        tab_road_adv = QWidget()
        road_adv_tab_layout = QFormLayout()
        tab_road_adv.setLayout(road_adv_tab_layout)
        
        self.decor_enabled_cb = QCheckBox("Enable Decorations")
        road_adv_tab_layout.addRow(self.decor_enabled_cb)
        
        self.decor_type_combo = QComboBox()
        self.decor_type_combo.addItems(["Emoji", "Custom Image"])
        road_adv_tab_layout.addRow("Decoration Type", self.decor_type_combo)
        
        self.decor_emoji_input = QLineEdit()
        self.decor_emoji_input.setPlaceholderText("E.g. 🌲   🏠   🌲")
        road_adv_tab_layout.addRow("Text / Emoji", self.decor_emoji_input)
        
        self.decor_file_btn = QPushButton("Browse decoration...")
        self.decor_file_label = QLabel("No file selected")
        self.decor_file_label.setStyleSheet("font-size: 10px; color: gray;")
        
        decor_file_layout = QHBoxLayout()
        decor_file_layout.addWidget(self.decor_file_btn)
        decor_file_layout.addWidget(self.decor_file_label)
        road_adv_tab_layout.addRow("Image", decor_file_layout)
        
        self.decor_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.decor_y_slider.setRange(-70, 70)
        self.decor_y_label = QLabel("10 px")
        self.decor_y_slider.valueChanged.connect(lambda v: self.decor_y_label.setText(f"{v} px"))
        
        decor_y_widget = QHBoxLayout()
        decor_y_widget.addWidget(self.decor_y_slider)
        decor_y_widget.addWidget(self.decor_y_label)
        road_adv_tab_layout.addRow("Position Y", decor_y_widget)
        
        self.decor_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.decor_size_slider.setRange(10, 100)
        self.decor_size_label = QLabel("24 px")
        self.decor_size_slider.valueChanged.connect(lambda v: self.decor_size_label.setText(f"{v} px"))
        
        decor_size_widget = QHBoxLayout()
        decor_size_widget.addWidget(self.decor_size_slider)
        decor_size_widget.addWidget(self.decor_size_label)
        road_adv_tab_layout.addRow("Size (Zoom)", decor_size_widget)
        
        self.decor_replicate_cb = QCheckBox("Enable Replication (Loop)")
        road_adv_tab_layout.addRow(self.decor_replicate_cb)
        
        # Spacer range updated to 0 - 500 px
        self.decor_spacer_slider = QSlider(Qt.Orientation.Horizontal)
        self.decor_spacer_slider.setRange(0, 500)
        self.decor_spacer_label = QLabel("100 px")
        self.decor_spacer_slider.valueChanged.connect(lambda v: self.decor_spacer_label.setText(f"{v} px"))
        
        decor_spacer_widget = QHBoxLayout()
        decor_spacer_widget.addWidget(self.decor_spacer_slider)
        decor_spacer_widget.addWidget(self.decor_spacer_label)
        road_adv_tab_layout.addRow("Spacer Distance", decor_spacer_widget)
        
        self.decor_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.decor_x_slider.setRange(0, 100)
        self.decor_x_label = QLabel("50 %")
        self.decor_x_slider.valueChanged.connect(lambda v: self.decor_x_label.setText(f"{v} %"))
        
        decor_x_widget = QHBoxLayout()
        decor_x_widget.addWidget(self.decor_x_slider)
        decor_x_widget.addWidget(self.decor_x_label)
        road_adv_tab_layout.addRow("Position X", decor_x_widget)
        
        self.decor_scrolling_cb = QCheckBox("Enable scrolling")
        road_adv_tab_layout.addRow(self.decor_scrolling_cb)
        
        self.decor_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.decor_speed_slider.setRange(1, 10)
        self.decor_speed_label = QLabel("2")
        self.decor_speed_slider.valueChanged.connect(lambda v: self.decor_speed_label.setText(str(v)))
        
        decor_speed_widget = QHBoxLayout()
        decor_speed_widget.addWidget(self.decor_speed_slider)
        decor_speed_widget.addWidget(self.decor_speed_label)
        road_adv_tab_layout.addRow("Scrolling Speed", decor_speed_widget)
        
        self.decor_enabled_cb.stateChanged.connect(self._toggle_decor_widgets)
        self.decor_type_combo.currentTextChanged.connect(self._toggle_decor_widgets)
        self.decor_replicate_cb.stateChanged.connect(self._toggle_decor_widgets)
        self.decor_scrolling_cb.stateChanged.connect(self._toggle_decor_widgets)
        self.decor_file_btn.clicked.connect(self._browse_decor_file)
        
        self.road_tabs.addTab(tab_road_adv, "Advanced Road")
        
        scroll_layout.addWidget(self.road_tabs)
        
        scroll.setWidget(scroll_content)
        
        layout = QVBoxLayout()
        layout.addWidget(scroll)
        self.tab_graphics.setLayout(layout)

    def _toggle_decor_widgets(self, *args: Any) -> None:
        enabled = self.decor_enabled_cb.isChecked()
        self.decor_type_combo.setEnabled(enabled)
        self.decor_y_slider.setEnabled(enabled)
        self.decor_size_slider.setEnabled(enabled)
        self.decor_replicate_cb.setEnabled(enabled)
        
        is_emoji = self.decor_type_combo.currentText() == "Emoji"
        self.decor_emoji_input.setEnabled(enabled and is_emoji)
        self.decor_file_btn.setEnabled(enabled and not is_emoji)
        
        replicate = self.decor_replicate_cb.isChecked()
        self.decor_spacer_slider.setEnabled(enabled and replicate)
        self.decor_x_slider.setEnabled(enabled and not replicate)
        
        self.decor_scrolling_cb.setEnabled(enabled and replicate)
        self.decor_speed_slider.setEnabled(enabled and replicate and self.decor_scrolling_cb.isChecked())
        
        self.update_preview()
        
    def _browse_decor_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Immagine Decorazione", "", "Immagini (*.png *.jpg *.jpeg *.svg *.gif)"
        )
        if file_path:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(addon_dir, "user_files")
            os.makedirs(dest_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            dest_path = os.path.join(dest_dir, filename)
            try:
                shutil.copy2(file_path, dest_path)
                self.decor_image_file_val = filename
                self.decor_file_label.setText(filename)
                self.update_preview()
            except Exception as e:
                from aqt.utils import showWarning
                showWarning(f"Impossibile copiare il file: {e}")

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

    def _toggle_nitro_widgets(self, state: int) -> None:
        self.nitro_cards_spin.setEnabled(self.nitro_enabled_cb.isChecked())

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
            self, "Seleziona Texture Strada", "", "Immagini (*.png *.jpg *.jpeg *.svg *.gif)"
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
        self.default_mode_combo.setCurrentText("Escape" if mode == "fuga" else "Normal")
        self.default_time_spin.setValue(race_config.get("default_time", 5.0))
        
        adv = int(race_config.get("default_advantage", 30.0))
        self.default_advantage_combo.setCurrentText(f"{adv}%")
        
        # Shortcut key sequence
        shortcut_str = race_config.get("shortcut", "Ctrl+R")
        self.shortcut_edit.setKeySequence(QKeySequence(shortcut_str))
        
        # Action on leaving deck
        leave_action = race_config.get("deck_leave_action", "pause")
        if leave_action == "continue":
            self.deck_leave_combo.setCurrentText("keep race running")
        elif leave_action == "interrupt":
            self.deck_leave_combo.setCurrentText("stop active race")
        else:
            self.deck_leave_combo.setCurrentText("pause active race")
        
        # Show active race flag in deck list
        self.show_flag_cb.setChecked(race_config.get("show_deck_list_flag", True))
        
        self.show_victory_popup_cb.setChecked(race_config.get("show_victory_popup", True))
        self.show_support_in_victory_popup_cb.setChecked(race_config.get("show_support_in_victory_popup", True))
        self.show_support_in_victory_popup_cb.setEnabled(self.show_victory_popup_cb.isChecked())
        self.show_defeat_popup_cb.setChecked(race_config.get("show_defeat_popup", True))
        
        # Tab 2: Strada e Auto
        self.height_slider.setValue(race_config.get("road_height", 35))
        self.cpu_y_slider.setValue(race_config.get("car_cpu_offset_y", 2))
        self.cpu_size_slider.setValue(race_config.get("car_cpu_size", 32))
        self.user_y_slider.setValue(race_config.get("car_user_offset_y", 18))
        self.user_size_slider.setValue(race_config.get("car_user_size", 32))
        
        style = race_config.get("road_style", "image")
        self.road_style_combo.setCurrentText("Solid Color" if style == "solid" else "Image (Texture)")
        self.road_color_preview.setStyleSheet(f"background-color: {self.road_solid_color_val};")
        self.road_file_label.setText(self.road_image_file_val if self.road_image_file_val else "No file selected")
        
        cpu_type = "Emoji" if race_config.get("car_cpu_type", "emoji") == "emoji" else "Custom Image"
        self.cpu_type_combo.setCurrentText(cpu_type)
        self.cpu_emoji_input.setText(race_config.get("car_cpu_emoji", "🚓"))
        self.cpu_flip_cb.setChecked(race_config.get("car_cpu_flip", True))
        self.cpu_file_label.setText(self.car_cpu_file_val if self.car_cpu_file_val else "No file selected")
        
        user_type = "Emoji" if race_config.get("car_user_type", "emoji") == "emoji" else "Custom Image"
        self.user_type_combo.setCurrentText(user_type)
        self.user_emoji_input.setText(race_config.get("car_user_emoji", "🏎️"))
        self.user_flip_cb.setChecked(race_config.get("car_user_flip", False))
        self.user_file_label.setText(self.car_user_file_val if self.car_user_file_val else "No file selected")
        
        # Nitro
        self.nitro_enabled_cb.setChecked(race_config.get("nitro_enabled", False))
        self.nitro_cards_spin.setValue(race_config.get("nitro_cards", 5))
        self._toggle_nitro_widgets(0)

        # Decorazioni
        self.decor_enabled_cb.setChecked(race_config.get("decor_enabled", False))
        self.decor_type_combo.setCurrentText("Emoji" if race_config.get("decor_type", "emoji") == "emoji" else "Custom Image")
        self.decor_emoji_input.setText(race_config.get("decor_emoji", "🌲   🏠   🌲"))
        self.decor_file_label.setText(self.decor_image_file_val if self.decor_image_file_val else "No file selected")
        self.decor_y_slider.setValue(race_config.get("decor_y", 10))
        self.decor_size_slider.setValue(race_config.get("decor_size", 24))
        self.decor_replicate_cb.setChecked(race_config.get("decor_replicate", True))
        self.decor_spacer_slider.setValue(race_config.get("decor_spacer", 100))
        self.decor_x_slider.setValue(race_config.get("decor_x", 50))
        self.decor_scrolling_cb.setChecked(race_config.get("decor_scrolling", True))
        self.decor_speed_slider.setValue(race_config.get("decor_speed", 2))
        
        # Trigger visibility toggles
        self._toggle_cpu_widgets(cpu_type)
        self._toggle_user_widgets(user_type)
        self._toggle_road_style_widgets(self.road_style_combo.currentText())
        self._toggle_decor_widgets(0)

    def _connect_signals(self) -> None:
        # Re-render preview whenever values are modified
        widgets = [
            self.overview_btn_cb, self.cpu_flip_cb, self.user_flip_cb,
            self.height_slider, self.cpu_y_slider, self.user_y_slider,
            self.cpu_size_slider, self.user_size_slider,
            self.decor_enabled_cb, self.decor_y_slider, self.decor_size_slider,
            self.decor_replicate_cb, self.decor_spacer_slider, self.decor_x_slider,
            self.decor_scrolling_cb, self.decor_speed_slider,
            self.nitro_enabled_cb
        ]
        for w in widgets:
            if isinstance(w, QSlider):
                w.valueChanged.connect(self._on_widget_changed)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self._on_widget_changed)
                
        self.nitro_cards_spin.valueChanged.connect(self._on_widget_changed)

        combos = [
            self.cpu_type_combo, self.user_type_combo, self.road_style_combo,
            self.decor_type_combo
        ]
        for c in combos:
            c.currentTextChanged.connect(self._on_widget_changed)
            
        self.decor_emoji_input.textChanged.connect(self._on_widget_changed)

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
            get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
            server_url = get_url() if get_url else "http://127.0.0.1/"
            
            user_path = os.path.join(addon_dir, "user_files", road_image_name)
            if os.path.exists(user_path):
                road_texture_url = f"{server_url}_addons/{addon_package}/user_files/{road_image_name}"
            else:
                assets_path = os.path.join(addon_dir, "web", "assets", road_image_name)
                if os.path.exists(assets_path):
                    road_texture_url = f"{server_url}_addons/{addon_package}/web/assets/{road_image_name}"

        # Resolve custom decoration texture image file
        decor_texture_url = ""
        decor_image_name = self.decor_image_file_val
        if decor_image_name:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            get_url = getattr(mw, "serverURL", getattr(mw, "server_url", None))
            server_url = get_url() if get_url else "http://127.0.0.1/"
            
            user_path = os.path.join(addon_dir, "user_files", decor_image_name)
            if os.path.exists(user_path):
                decor_texture_url = f"{server_url}_addons/{addon_package}/user_files/{decor_image_name}"
            else:
                assets_path = os.path.join(addon_dir, "web", "assets", decor_image_name)
                if os.path.exists(assets_path):
                    decor_texture_url = f"{server_url}_addons/{addon_package}/web/assets/{decor_image_name}"

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
            "nitro_enabled": self.nitro_enabled_cb.isChecked(),
            "nitro_cards": self.nitro_cards_spin.value(),
            
            # Form values
            "road_scrolling": False,
            "road_height": self.height_slider.value(),
            "car_cpu_offset_y": self.cpu_y_slider.value(),
            "car_cpu_size": self.cpu_size_slider.value(),
            "car_user_offset_y": self.user_y_slider.value(),
            "car_user_size": self.user_size_slider.value(),
            "car_cpu_type": "emoji" if self.cpu_type_combo.currentText() == "Emoji" else "file",
            "car_cpu_emoji": self.cpu_emoji_input.text(),
            "car_cpu_flip": self.cpu_flip_cb.isChecked(),
            "car_user_type": "emoji" if self.user_type_combo.currentText() == "Emoji" else "file",
            "car_user_emoji": self.user_emoji_input.text(),
            "car_user_flip": self.user_flip_cb.isChecked(),
            "road_style": "solid" if self.road_style_combo.currentText() == "Solid Color" else "image",
            "road_solid_color": self.road_solid_color_val,
            "road_image_file": self.road_image_file_val,
            "is_preview": True,
            "decor_enabled": self.decor_enabled_cb.isChecked(),
            "decor_type": "emoji" if self.decor_type_combo.currentText() == "Emoji" else "image",
            "decor_emoji": self.decor_emoji_input.text(),
            "decor_image_file": self.decor_image_file_val,
            "decor_texture_url": decor_texture_url,
            "decor_y": self.decor_y_slider.value(),
            "decor_size": self.decor_size_slider.value(),
            "decor_replicate": self.decor_replicate_cb.isChecked(),
            "decor_spacer": self.decor_spacer_slider.value(),
            "decor_x": self.decor_x_slider.value(),
            "decor_scrolling": self.decor_scrolling_cb.isChecked(),
            "decor_speed": self.decor_speed_slider.value()
        }

    def update_preview(self) -> None:
        if not self.preview_loaded:
            return
        state = self._get_dialog_state_dict()
        self.preview_webview.eval(f"if (window.updateRaceState) {{ window.updateRaceState({json.dumps(state)}); }}")

    def _browse_cpu_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Opponent Image", "", "Images (*.png *.jpg *.jpeg *.svg *.gif)"
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
            self, "Select User Image", "", "Images (*.png *.jpg *.jpeg *.svg *.gif)"
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
        mode_text = "fuga" if self.default_mode_combo.currentText() == "Escape" else "normale"
        adv_text = self.default_advantage_combo.currentText().replace("%", "")
        
        leave_text = self.deck_leave_combo.currentText()
        if leave_text == "keep race running":
            leave_val = "continue"
        elif leave_text == "stop active race":
            leave_val = "interrupt"
        else:
            leave_val = "pause"
            
        updates = {
            "road_scrolling": False,
            "show_overview_button": self.overview_btn_cb.isChecked(),
            "default_mode": mode_text,
            "default_time": self.default_time_spin.value(),
            "default_advantage": float(adv_text),
            "road_height": self.height_slider.value(),
            "car_cpu_offset_y": self.cpu_y_slider.value(),
            "car_cpu_size": self.cpu_size_slider.value(),
            "car_user_offset_y": self.user_y_slider.value(),
            "car_user_size": self.user_size_slider.value(),
            "car_cpu_type": "emoji" if self.cpu_type_combo.currentText() == "Emoji" else "file",
            "car_cpu_emoji": self.cpu_emoji_input.text(),
            "car_cpu_flip": self.cpu_flip_cb.isChecked(),
            "car_cpu_file": self.car_cpu_file_val,
            "car_user_type": "emoji" if self.user_type_combo.currentText() == "Emoji" else "file",
            "car_user_emoji": self.user_emoji_input.text(),
            "car_user_flip": self.user_flip_cb.isChecked(),
            "car_user_file": self.car_user_file_val,
            "road_style": "solid" if self.road_style_combo.currentText() == "Solid Color" else "image",
            "road_solid_color": self.road_solid_color_val,
            "road_image_file": self.road_image_file_val,
            "shortcut": self.shortcut_edit.keySequence().toString(),
            "show_deck_list_flag": self.show_flag_cb.isChecked(),
            "show_victory_popup": self.show_victory_popup_cb.isChecked(),
            "show_support_in_victory_popup": self.show_support_in_victory_popup_cb.isChecked(),
            "show_defeat_popup": self.show_defeat_popup_cb.isChecked(),
            "decor_enabled": self.decor_enabled_cb.isChecked(),
            "decor_type": "emoji" if self.decor_type_combo.currentText() == "Emoji" else "image",
            "decor_emoji": self.decor_emoji_input.text(),
            "decor_image_file": self.decor_image_file_val,
            "decor_y": self.decor_y_slider.value(),
            "decor_size": self.decor_size_slider.value(),
            "decor_replicate": self.decor_replicate_cb.isChecked(),
            "decor_spacer": self.decor_spacer_slider.value(),
            "decor_x": self.decor_x_slider.value(),
            "decor_scrolling": self.decor_scrolling_cb.isChecked(),
            "decor_speed": self.decor_speed_slider.value(),
            "deck_leave_action": leave_val,
            "nitro_enabled": self.nitro_enabled_cb.isChecked(),
            "nitro_cards": self.nitro_cards_spin.value()
        }
        
        race_config.update(updates)
        
        # Apply updates to active widgets in Anki if visible
        from .hooks import race_bar_widget, register_shortcut
        if race_bar_widget and race_bar_widget.isVisible():
            race_bar_widget.setFixedHeight(updates["road_height"])
            race_bar_widget.update_state()
            
        # Refresh the active view to reflect settings changes instantly
        if mw:
            if mw.state == "deckBrowser" and getattr(mw, "deckBrowser", None):
                mw.deckBrowser.refresh()
            elif mw.state == "overview" and getattr(mw, "overview", None):
                mw.overview.refresh()
            
        # Re-register the shortcut in case it changed
        register_shortcut()
        
        self.accept()
