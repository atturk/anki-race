from typing import Any, Optional
from aqt import mw, gui_hooks
from aqt.utils import showInfo
from .race import race_manager
from .gui import RaceSetupDialog, RaceBarWebView

addon_package = __name__.split('.')[0]

# Global reference to the persistent race bar widget
race_bar_widget: Optional[RaceBarWebView] = None

def init_race_bar() -> None:
    """Instantiates the persistent race bar webview and inserts it at the top of Anki's window layout."""
    global race_bar_widget
    if not race_bar_widget and mw:
        race_bar_widget = RaceBarWebView(mw)
        # Index 0 places it at the absolute top, above deck list / reviewer contents
        mw.mainLayout.insertWidget(0, race_bar_widget)
        # Hidden by default, shown only during a race study session
        race_bar_widget.hide()

def start_race_flow(deck_id: int) -> None:
    """Helper to open the setup dialog, initialize the race, and start studying."""
    if not mw or not mw.col:
        return
        
    due_count = race_manager._get_due_card_count(deck_id)
    if due_count == 0:
        showInfo("Non ci sono carte da studiare in questo mazzo!")
        return
        
    # Get deck name
    deck = mw.col.decks.get(deck_id)
    deck_name = deck.get("name", "Mazzo Sconosciuto")
    
    # Open the setup dialog modal
    dialog = RaceSetupDialog(mw, deck_name, due_count)
    if dialog.exec():  # User clicked "Gareggia!"
        settings = dialog.get_settings()
        race_manager.start_race(deck_id, settings)
        
        # Load assets and show the persistent race bar widget
        if race_bar_widget:
            race_bar_widget.load_race_html()
            race_bar_widget.show()
            
        # Start studying by changing main window state to review
        mw.moveToState("review")

def on_menu_action() -> None:
    """Triggered when the user clicks 'Test Anki Race' in the Tools menu."""
    if not mw or not mw.col:
        return
    current_deck_id = mw.col.decks.selected()
    start_race_flow(current_deck_id)

def on_overview_will_render_content(overview: Any, content: Any) -> None:
    """Injects a 'Gareggia' button into the deck overview screen beneath the 'Study Now' button."""
    # We append custom styles and a script to content.table
    content.table += """
<style>
#anki-race-btn {
    margin-top: 10px !important;
    background: #e74c3c !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 5px !important;
    padding: 10px 24px !important;
    cursor: pointer !important;
    font-size: 1em !important;
    font-weight: bold !important;
    transition: all 0.2s ease !important;
    display: inline-block !important;
    text-decoration: none !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
}
#anki-race-btn:hover {
    background: #c0392b !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(231, 76, 60, 0.35) !important;
}
#anki-race-btn:active {
    transform: translateY(0px) !important;
    box-shadow: 0 2px 4px rgba(231, 76, 60, 0.2) !important;
}
</style>
<script>
(function() {
    function injectButton() {
        const studyBtn = document.querySelector("button.study") || document.querySelector("button");
        if (studyBtn) {
            // Avoid duplicate injection
            if (document.getElementById("anki-race-btn")) return;
            
            const raceBtn = document.createElement("button");
            raceBtn.id = "anki-race-btn";
            raceBtn.innerText = "Gareggia";
            
            raceBtn.onclick = function() {
                pycmd("anki_race_setup");
            };
            studyBtn.parentNode.insertBefore(raceBtn, studyBtn.nextSibling);
        } else {
            // Retry if the study button isn't loaded yet
            setTimeout(injectButton, 50);
        }
    }
    injectButton();
})();
</script>
"""

def on_js_message(handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
    """Handles messages sent from JavaScript inside Anki's standard webviews (Overview)."""
    if message == "anki_race_setup":
        if not mw or not mw.col:
            return (True, None)
            
        current_deck_id = mw.col.decks.selected()
        start_race_flow(current_deck_id)
        return (True, None)
        
    return handled

def on_card_answered(reviewer: Any, card: Any, ease: int) -> None:
    """Updates the race state when a card is rated in the reviewer."""
    if race_manager.race_in_progress:
        # Ease: 1=Again (incorrect), 2=Hard, 3=Good, 4=Easy (correct)
        correct = ease > 1
        race_manager.on_card_answered(correct)
        
        # Push updated positions to our persistent top widget Webview
        if race_bar_widget:
            race_bar_widget.update_state()
            
        # Print status to debug console for validation
        print(f"[AnkiRace] Card answered (correct={correct}). "
              f"Remaining cards: {race_manager.remaining_cards}/{race_manager.total_cards}. "
              f"Positions: User {race_manager.user_position:.1f}% vs CPU {race_manager.cpu_position:.1f}%")

def on_state_did_change(new_state: str, old_state: str) -> None:
    """Ensures that the persistent race bar widget is paused/resumed and shown/hidden based on state."""
    if new_state == "review":
        if race_manager.race_in_progress:
            current_deck_id = mw.col.decks.selected()
            if current_deck_id == race_manager.deck_id:
                if race_manager.race_paused:
                    race_manager.resume_race()
                    if race_bar_widget:
                        race_bar_widget.update_state()
                        race_bar_widget.show()
            else:
                # User switched to a different deck, abort the old race
                race_manager.race_in_progress = False
                race_manager.race_paused = False
                if race_bar_widget:
                    race_bar_widget.hide()
    else: # new_state != "review"
        if race_bar_widget:
            race_bar_widget.hide()
        if race_manager.race_in_progress and not race_manager.race_paused:
            race_manager.pause_race()

# Setup Hooks
if mw:
    # 1. Register Web Exports so Anki's local web server serves files under /_addons/
    mw.addonManager.setWebExports(addon_package, r"(web|user_files)/.*")
    
    # 2. Tools Menu Item
    mw.form.menuTools.addAction("Test Anki Race", on_menu_action)
    
    # 3. Overview screen content injection hook
    gui_hooks.overview_will_render_content.append(on_overview_will_render_content)
    
    # 4. WebView JS message handler hook (captures signals from Overview deck screen)
    gui_hooks.webview_did_receive_js_message.append(on_js_message)
    
    # 5. Reviewer answer hook
    gui_hooks.reviewer_did_answer_card.append(on_card_answered)
    
    # 6. State change hook to show/hide the persistent widget
    gui_hooks.state_did_change.append(on_state_did_change)
    
    # 7. Initialize persistent race bar widget
    init_race_bar()
