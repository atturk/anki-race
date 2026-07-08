import time
from typing import Dict, Any, Optional
from aqt import mw

class AnkiRaceManager:
    def __init__(self) -> None:
        # State variables
        self.mode: str = "normale"            # "normale" or "fuga"
        self.chosen_time: float = 5.0         # chosen time in minutes
        self.advantage: float = 0.0           # User starting position advantage in Escape mode (10%, 20%, 30%)
        self.total_cards: int = 0
        self.remaining_cards: int = 0
        self.user_position: float = 0.0       # 0 to 100
        self.cpu_position: float = 0.0        # 0 to 100
        self.race_in_progress: bool = False
        self.race_paused: bool = False        # Tracks whether the race is currently paused
        self.deck_id: Optional[int] = None    # ID of the deck being studied in the race
        
        # Timing helpers
        self.start_time: float = 0.0
        self.elapsed_before_pause: float = 0.0 # Time accumulated before a pause

    def start_race(self, deck_id: int, settings: Dict[str, Any]) -> None:
        """Initializes the race state and reads cards to study for the selected deck."""
        self.deck_id = deck_id
        self.mode = settings.get("mode", "normale")
        self.chosen_time = float(settings.get("chosen_time", 5.0)) # Default 5 minutes
        self.advantage = float(settings.get("advantage", 0.0)) if self.mode == "fuga" else 0.0
        
        # Read the number of due cards from Anki
        self.total_cards = self._get_due_card_count(deck_id)
        self.remaining_cards = self.total_cards
        
        # Reset positions (User starts at their advantage percentage)
        self.user_position = self.advantage
        self.cpu_position = 0.0
        self.elapsed_before_pause = 0.0
        self.race_paused = False
            
        self.start_time = time.time()
        self.race_in_progress = True

    def pause_race(self) -> None:
        """Pauses the race timer and execution."""
        if self.race_in_progress and not self.race_paused:
            self.elapsed_before_pause += time.time() - self.start_time
            self.race_paused = True

    def resume_race(self) -> None:
        """Resumes the race from a paused state."""
        if self.race_in_progress and self.race_paused:
            self.start_time = time.time()
            self.race_paused = False

    def calculate_positions(self) -> None:
        """Calculates user and CPU positions based on card progress and time elapsed."""
        if not self.race_in_progress:
            return

        # 1. User position (advances constants cards percentage, starting from advantage)
        if self.total_cards > 0:
            completed = self.total_cards - self.remaining_cards
            self.user_position = min(100.0, self.advantage + ((100.0 - self.advantage) * completed / self.total_cards))
        else:
            self.user_position = 100.0

        # 2. CPU position (travels at constant speed to reach 100% in chosen_time in both modes)
        elapsed_seconds = self.elapsed_before_pause
        if not self.race_paused:
            elapsed_seconds += time.time() - self.start_time
            
        total_seconds = self.chosen_time * 60.0
        
        if total_seconds > 0:
            self.cpu_position = min(100.0, (elapsed_seconds / total_seconds) * 100.0)
        else:
            self.cpu_position = 100.0

    def on_card_answered(self, correct: bool) -> None:
        """Updates remaining cards and recalculates positions on review answer (independent of correctness)."""
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
