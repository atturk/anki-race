from typing import Any, Optional
from aqt import mw, gui_hooks
from aqt.qt import QMenu, QShortcut, QKeySequence
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
        
    if mw and mw.col:
        mw.col.decks.select(deck_id)
        due_count = sum(mw.col.sched.counts())
    else:
        due_count = race_manager._get_due_card_count(deck_id)
    if due_count == 0:
        showInfo("There are no cards to study in this deck!")
        return
        
    # Get deck name
    deck = mw.col.decks.get(deck_id)
    deck_name = deck.get("name", "Unknown Deck")
    
    # Open the setup dialog modal
    dialog = RaceSetupDialog(mw, deck_name, due_count)
    if dialog.exec():  # User clicked "Gareggia!"
        settings = dialog.get_settings()
        race_manager.start_race(deck_id, settings)
        
        # Load assets and show the persistent race bar widget
        if race_bar_widget:
            from .config import race_config
            race_bar_widget.setFixedHeight(race_config.get("road_height", 35))
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
    """Injects a 'Gareggia' (or 'Interrompi Gara') button into the deck overview screen beneath the 'Study Now' button."""
    from .config import race_config
    if not race_config.get("show_overview_button", True):
        return
        
    current_deck_id = mw.col.decks.selected() if mw and mw.col else None
    is_active_race = (
        current_deck_id is not None
        and race_manager.race_in_progress
        and race_manager.deck_id == current_deck_id
    )
    
    btn_text = "Stop Race" if is_active_race else "Race!"
    btn_cmd = "anki_race_stop" if is_active_race else "anki_race_setup"
    
    # Red styling for Gareggia, dark slate styling for Interrompi Gara
    if is_active_race:
        btn_style = """
#anki-race-btn {
    margin-top: 10px !important;
    background: #34495e !important;
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
    background: #2c3e50 !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(52, 73, 94, 0.35) !important;
}
#anki-race-btn:active {
    transform: translateY(0px) !important;
    box-shadow: 0 2px 4px rgba(52, 73, 94, 0.2) !important;
}
"""
    else:
        btn_style = """
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
"""

    content.table += f"""
<style>
{btn_style}
</style>
<script>
(function() {{
    function injectButton() {{
        const studyBtn = document.querySelector("button.study") || document.querySelector("button");
        if (studyBtn) {{
            // Avoid duplicate injection
            if (document.getElementById("anki-race-btn")) return;
            
            const raceBtn = document.createElement("button");
            raceBtn.id = "anki-race-btn";
            raceBtn.innerText = "{btn_text}";
            
            raceBtn.onclick = function() {{
                pycmd("{btn_cmd}");
            }};
            studyBtn.parentNode.insertBefore(raceBtn, studyBtn.nextSibling);
        }} else {{
            // Retry if the study button isn't loaded yet
            setTimeout(injectButton, 50);
        }}
    }}
    injectButton();
}})();
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
def stop_active_race() -> None:
    """Instantly cancels the active race, hiding widgets and refreshing views."""
    race_manager.race_in_progress = False
    race_manager.race_paused = False
    
    if race_bar_widget:
        race_bar_widget.hide()
        
    if mw:
        if mw.state == "overview" and getattr(mw, "overview", None):
            mw.overview.refresh()
        elif mw.state == "deckBrowser" and getattr(mw, "deckBrowser", None):
            mw.deckBrowser.refresh()

def on_js_message(handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
    """Handles messages sent from JavaScript inside Anki's standard webviews (Overview)."""
    if message == "anki_race_setup":
        if not mw or not mw.col:
            return (True, None)
            
        current_deck_id = mw.col.decks.selected()
        start_race_flow(current_deck_id)
        return (True, None)
    elif message == "anki_race_stop":
        stop_active_race()
        return (True, None)
        
    return handled

def on_card_answered(reviewer: Any, card: Any, ease: int) -> None:
    """Updates the race state when a card is rated in the reviewer."""
    if race_manager.race_in_progress:
        # Ease: 1=Again (incorrect), 2=Hard, 3=Good, 4=Easy (correct)
        correct = ease > 1
        
        # Determine if it is Good or Easy
        # By default, for 4 buttons: 3=Good, 4=Easy (so ease >= 3)
        # For 3 buttons: 2=Good, 3=Easy (so ease >= 2)
        # For 2 buttons: 2=Good (so ease >= 2)
        num_buttons = 4
        if mw and mw.col and card:
            try:
                num_buttons = mw.col.sched.answerButtons(card)
            except Exception:
                pass
                
        if num_buttons == 4:
            is_good_easy = (ease >= 3)
        else:
            is_good_easy = (ease >= 2)
            
        race_manager.update_streak(is_good_easy, is_undo=False)
        race_manager.on_card_answered(correct)
        
        # Check if victory achieved directly in Python to prevent timing conflicts
        if race_manager.remaining_cards <= 0:
            if race_bar_widget:
                race_bar_widget.trigger_victory_directly()
            return
        
        # Push updated positions to our persistent top widget Webview
        if race_bar_widget:
            race_bar_widget.update_state()

def on_reviewer_show_question(card: Any) -> None:
    """Triggered when a new card is shown. Syncs the scheduler counts."""
    if race_manager.race_in_progress and mw and mw.col:
        try:
            remaining = sum(mw.col.sched.counts())
            is_undo = getattr(race_manager, "just_did_undo", False)
            race_manager.just_did_undo = False
            
            race_manager.update_remaining(remaining, is_undo=is_undo)
            
            if race_manager.remaining_cards <= 0:
                if race_bar_widget:
                    race_bar_widget.trigger_victory_directly()
                return
                
            if race_bar_widget:
                race_bar_widget.update_state()
        except Exception as e:
            print(f"[AnkiRace] Error in on_reviewer_show_question: {e}")

def on_state_did_undo(changes: Any) -> None:
    """Triggered when Anki successfully performs an undo action."""
    if race_manager.race_in_progress and mw and mw.col:
        try:
            remaining = sum(mw.col.sched.counts())
            race_manager.just_did_undo = True
            race_manager.update_streak(False, is_undo=True)
            race_manager.update_remaining(remaining, is_undo=True)
            if race_bar_widget:
                race_bar_widget.update_state()
        except Exception as e:
            print(f"[AnkiRace] Error in on_state_did_undo: {e}")

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
                stop_active_race()
    else: # new_state != "review"
        if race_bar_widget:
            race_bar_widget.hide()
            
        if race_manager.race_in_progress:
            if mw and mw.col:
                try:
                    remaining = sum(mw.col.sched.counts())
                    if remaining <= 0:
                        race_manager.update_remaining(0, is_undo=False)
                        if race_bar_widget:
                            race_bar_widget.trigger_victory_directly()
                        return
                except Exception as e:
                    print(f"[AnkiRace] Error checking remaining count on state change: {e}")
            
            from .config import race_config
            action = race_config.get("deck_leave_action", "pause")
            if action == "interrupt":
                stop_active_race()
            elif action == "pause":
                if not race_manager.race_paused:
                    race_manager.pause_race()

shortcut_instance: Optional[QShortcut] = None

def register_shortcut() -> None:
    """Registers or updates the keyboard shortcut for starting a race."""
    global shortcut_instance
    if not mw:
        return
    
    # Disable/remove existing shortcut
    if shortcut_instance:
        shortcut_instance.setEnabled(False)
        shortcut_instance.setParent(None)
        shortcut_instance = None
        
    from .config import race_config
    shortcut_str = race_config.get("shortcut", "Ctrl+R")
    if shortcut_str:
        try:
            shortcut_instance = QShortcut(QKeySequence(shortcut_str), mw)
            shortcut_instance.activated.connect(on_menu_action)
        except Exception as e:
            print(f"[AnkiRace] Failed to register shortcut '{shortcut_str}': {e}")

def on_deck_browser_will_render_content(deck_browser: Any, content: Any) -> None:
    """Prepend a checkered flag emoji next to the active race deck in the main deck tree browser."""
    from .config import race_config
    import re
    if not race_config.get("show_deck_list_flag", True):
        return
        
    if race_manager.race_in_progress and race_manager.deck_id is not None:
        deck_id = race_manager.deck_id
        # Modern Anki deck links use the onclick="return pycmd('open:deck_id')" pattern.
        # We define separate patterns for double-quoted and single-quoted onclick attributes to avoid quotes conflicts.
        pattern_double = rf'(<a\s+[^>]*onclick="[^"]*open:{deck_id}[^"]*"[^>]*>)([^<]+)(</a>)'
        pattern_single = rf'(<a\s+[^>]*onclick=\'[^\']*open:{deck_id}[^\']*\'[^>]*>)([^<]+)(</a>)'
        content.tree = re.sub(pattern_double, r'\1🏁 \2\3', content.tree)
        content.tree = re.sub(pattern_single, r'\1🏁 \2\3', content.tree)

def setup_tools_menu() -> None:
    """Creates a sub-menu under Tools -> Anki Race with options to start, stop, and customize races."""
    if not mw:
        return
    
    # Create the sub-menu under tools
    menu = QMenu("Anki Race", mw.form.menuTools)
    
    # Add actions
    action_start = menu.addAction("Start Race")
    action_start.triggered.connect(on_menu_action)
    
    action_stop = menu.addAction("Stop Race")
    action_stop.triggered.connect(stop_active_race)
    
    action_config = menu.addAction("Customize...")
    action_config.triggered.connect(on_open_config)
    
    # Enable Interrompi Gara dynamically right before the menu is shown to the user
    def update_actions_state() -> None:
        action_stop.setEnabled(race_manager.race_in_progress)
        
    menu.aboutToShow.connect(update_actions_state)
    
    # Add to Tools menu
    mw.form.menuTools.addMenu(menu)
    
    # Register keyboard shortcut
    register_shortcut()

def on_open_config() -> None:
    """Opens the custom configuration dialog."""
    from .config_dialog import RaceConfigDialog
    dialog = RaceConfigDialog(mw)
    dialog.exec()

# Setup Hooks
if mw:
    # 1. Register Web Exports so Anki's local web server serves files under /_addons/
    mw.addonManager.setWebExports(addon_package, r"(web|user_files)/.*")
    
    # 2. Tools Sub-menu
    setup_tools_menu()
    
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
    
    # 8. Deck browser content injection hook
    gui_hooks.deck_browser_will_render_content.append(on_deck_browser_will_render_content)
    
    # 9. Reviewer show question hook
    if hasattr(gui_hooks, "reviewer_did_show_question"):
        gui_hooks.reviewer_did_show_question.append(on_reviewer_show_question)
        
    # 10. Undo hooks
    if hasattr(gui_hooks, "state_did_undo"):
        gui_hooks.state_did_undo.append(on_state_did_undo)
