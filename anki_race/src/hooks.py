from typing import Any
from aqt import mw, gui_hooks
from aqt.utils import showInfo
from .race import race_manager

def on_menu_action() -> None:
    """Triggered when the user clicks 'Test Anki Race' in the Tools menu."""
    if not mw or not mw.col:
        return
        
    current_deck_id = mw.col.decks.selected()
    due_count = race_manager._get_due_card_count(current_deck_id)
    
    if due_count == 0:
        showInfo("Non ci sono carte da studiare in questo mazzo!")
        return
        
    settings = {"mode": "normale", "chosen_time": 5.0}
    race_manager.start_race(current_deck_id, settings)
    
    showInfo(f"Gara avviata! Carte: {race_manager.total_cards}. Tempo: {race_manager.chosen_time} min.")
    mw.moveToState("review")

def on_overview_will_render_content(overview: Any, content: Any) -> None:
    """Injects a 'Gareggia' button into the deck overview screen beneath the 'Study Now' button."""
    # We append a script to content.table to query the DOM and insert our button
    content.table += """
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
            raceBtn.className = "study race-button";
            raceBtn.style.marginTop = "10px";
            raceBtn.style.backgroundColor = "#e74c3c";
            raceBtn.style.color = "#ffffff";
            raceBtn.style.border = "none";
            raceBtn.style.borderRadius = "4px";
            raceBtn.style.padding = "10px 24px";
            raceBtn.style.cursor = "pointer";
            raceBtn.style.fontSize = "1em";
            
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
        due_count = race_manager._get_due_card_count(current_deck_id)
        
        if due_count == 0:
            showInfo("Non ci sono carte da studiare in questo mazzo!")
            return (True, None)
            
        settings = {"mode": "normale", "chosen_time": 5.0}
        race_manager.start_race(current_deck_id, settings)
        
        # Transition to the review screen
        mw.moveToState("review")
        return (True, None)
        
    return handled

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
    # 1. Tools Menu Item
    mw.form.menuTools.addAction("Test Anki Race", on_menu_action)
    
    # 2. Overview screen content injection hook
    gui_hooks.overview_will_render_content.append(on_overview_will_render_content)
    
    # 3. WebView JS message handler hook
    gui_hooks.webview_did_receive_js_message.append(on_js_message)
    
    # 4. Reviewer answer hook
    gui_hooks.reviewer_did_answer_card.append(on_card_answered)
