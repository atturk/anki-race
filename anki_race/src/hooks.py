from aqt import mw
from aqt.utils import showInfo

def show_test_message() -> None:
    """Displays a simple popup to confirm the addon was loaded successfully."""
    showInfo("Anki Race caricato con successo!")

# Add a menu item to Anki's Tools (Strumenti) menu
# Anki's main window (mw) has a 'menuTools' menu, we add a new action directly to it.
# The addAction(text, callback) method automatically creates a QAction and connects it.
if mw:
    mw.form.menuTools.addAction("Test Anki Race", show_test_message)
