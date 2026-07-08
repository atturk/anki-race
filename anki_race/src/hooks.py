import os
from typing import Any
from aqt import mw, gui_hooks
from aqt.utils import showInfo
from aqt.reviewer import Reviewer
from .race import race_manager
from .gui import RaceSetupDialog

addon_package = __name__.split('.')[0]

def get_asset_url(filename: str) -> str:
    """Checks if a custom asset exists in user_files/, else falls back to default in web/assets/."""
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try different extensions in user_files
    for ext in ["png", "jpg", "svg"]:
        user_path = os.path.join(addon_dir, "user_files", f"{filename}.{ext}")
        if os.path.exists(user_path):
            return f"/_addons/{addon_package}/user_files/{filename}.{ext}"
            
    # Fallback to default SVG in web assets
    return f"/_addons/{addon_package}/web/assets/{filename}.svg"

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
    """Handles messages sent from JavaScript inside Anki webviews."""
    if message == "anki_race_setup":
        if not mw or not mw.col:
            return (True, None)
            
        current_deck_id = mw.col.decks.selected()
        start_race_flow(current_deck_id)
        return (True, None)
        
    elif message == "anki_race_finished":
        # Disable race in progress state when overlay is displayed
        race_manager.race_in_progress = False
        return (True, None)
        
    return handled

def on_webview_will_set_content(web_content: Any, context: Any) -> None:
    """Injects the race interface container, state, and assets when the Reviewer webview loads."""
    if not isinstance(context, Reviewer):
        return
        
    # Check if a race is actually in progress
    if not race_manager.race_in_progress:
        return
        
    # Determine asset paths (allowing hot-swapping from user_files)
    user_car_url = get_asset_url("car_user")
    cpu_car_url = get_asset_url("car_cpu")
    road_texture_url = get_asset_url("road_texture")
    
    # Get deck info
    current_deck_id = mw.col.decks.selected()
    deck = mw.col.decks.get(current_deck_id)
    deck_name = deck.get("name", "Mazzo")
    
    # Register CSS and JS scripts
    web_content.css.append(f"/_addons/{addon_package}/web/css/race.css")
    web_content.js.append(f"/_addons/{addon_package}/web/js/race.js")
    
    # Inject race state inside <head>
    web_content.head += f"""
<script>
window.ankiRaceState = {{
    user_position: {race_manager.user_position},
    cpu_position: {race_manager.cpu_position},
    total_cards: {race_manager.total_cards},
    remaining_cards: {race_manager.remaining_cards},
    mode: "{race_manager.mode}",
    chosen_time: {race_manager.chosen_time},
    race_in_progress: {"true" if race_manager.race_in_progress else "false"},
    start_time: {race_manager.start_time},
    deck_name: "{deck_name}",
    user_car_url: "{user_car_url}",
    cpu_car_url: "{cpu_car_url}",
    road_texture_url: "{road_texture_url}"
}};
</script>
"""
    
    # Prepend the HTML container for the race bar at the top of <body>
    web_content.body = f"""
<div id="anki-race-container"></div>
{web_content.body}
"""

def on_card_answered(reviewer: Any, card: Any, ease: int) -> None:
    """Updates the race state when a card is rated in the reviewer."""
    if race_manager.race_in_progress:
        # Ease: 1=Again (incorrect), 2=Hard, 3=Good, 4=Easy (correct)
        correct = ease > 1
        race_manager.on_card_answered(correct)
        
        # Print status to debug console for validation
        print(f"[AnkiRace] Card answered (correct={correct}). "
              f"Remaining cards: {race_manager.remaining_cards}/{race_manager.total_cards}. "
              f"Positions: User {race_manager.user_position:.1f}% vs CPU {race_manager.cpu_position:.1f}%")

# Setup Hooks
if mw:
    # 1. Register Web Exports so Anki's local web server serves files under /_addons/
    mw.addonManager.setWebExports(addon_package, r"(web|user_files)/.*")
    
    # 2. Tools Menu Item
    mw.form.menuTools.addAction("Test Anki Race", on_menu_action)
    
    # 3. Overview screen content injection hook
    gui_hooks.overview_will_render_content.append(on_overview_will_render_content)
    
    # 4. WebView JS message handler hook
    gui_hooks.webview_did_receive_js_message.append(on_js_message)
    
    # 5. Reviewer webview injection hook
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    
    # 6. Reviewer answer hook
    gui_hooks.reviewer_did_answer_card.append(on_card_answered)
