import time
from typing import Dict, Any, Optional
from aqt import mw

class AnkiRaceManager:
    def __init__(self) -> None:
        # State variables
        self.mode: str = "normale"            # "normale" or "fuga"
        self.chosen_time: float = 5.0        # chosen time in minutes
        self.total_cards: int = 0
        self.remaining_cards: int = 0
        self.user_position: float = 0.0      # 0 to 100
        self.cpu_position: float = 0.0       # 0 to 100
        self.race_in_progress: bool = False
        
        # Timing helpers
        self.start_time: float = 0.0

    def start_race(self, deck_id: int, settings: Dict[str, Any]) -> None:
        """Initializes the race state and reads cards to study for the selected deck."""
        self.mode = settings.get("mode", "normale")
        self.chosen_time = float(settings.get("chosen_time", 5.0)) # Default 5 minutes
        
        # Read the number of due cards from Anki
        self.total_cards = self._get_due_card_count(deck_id)
        self.remaining_cards = self.total_cards
        
        # Reset positions
        self.user_position = 0.0
        self.cpu_position = 0.0
        self.start_time = time.time()
        self.race_in_progress = True

    def calculate_positions(self) -> None:
        """Calculates user and CPU positions."""
        if not self.race_in_progress:
            return

        # 1. Calculate user position (0-100%)
        if self.total_cards > 0:
            completed = self.total_cards - self.remaining_cards
            self.user_position = min(100.0, (completed / self.total_cards) * 100.0)
        else:
            self.user_position = 100.0

        # 2. Calculate CPU position based on constant speed over time
        elapsed_seconds = time.time() - self.start_time
        total_seconds = self.chosen_time * 60.0
        if total_seconds > 0:
            self.cpu_position = min(100.0, (elapsed_seconds / total_seconds) * 100.0)
        else:
            self.cpu_position = 100.0

    def on_card_answered(self, correct: bool) -> None:
        """Updates remaining cards and recalculates positions on review answer."""
        if not self.race_in_progress:
            return

        if self.remaining_cards > 0:
            self.remaining_cards -= 1
        
        self.calculate_positions()

    def _get_due_card_count(self, deck_id: int) -> int:
        """Helper to get total due/new cards for a deck from Anki's scheduler."""
        if not mw or not mw.col:
            return 0
            
        try:
            tree = mw.col.sched.deck_due_tree()
            
            # Recursive helper to find the deck node in the due tree
            def find_node(node: Any, target_id: int) -> Optional[Any]:
                if node.deck_id == target_id:
                    return node
                for child in node.children:
                    res = find_node(child, target_id)
                    if res:
                        return res
                return None

            node = find_node(tree, deck_id)
            if node:
                # Include New, Learning, and Review cards in the total race count
                return node.new_count + node.learn_count + node.review_count
        except Exception:
            # Fallback in case of scheduler version/API discrepancies
            pass
            
        return 0

# Global race manager instance
race_manager = AnkiRaceManager()
