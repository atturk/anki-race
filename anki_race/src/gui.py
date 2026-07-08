from typing import Dict, Any, Optional
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QRadioButton,
    Qt
)

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
        # Apply standard Anki color (blue-ish) or race theme (red/green)
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
