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
        self.answered_cards: int = 0
        self.user_position: float = 0.0       # 0 to 100
        self.cpu_position: float = 0.0        # 0 to 100
        self.race_in_progress: bool = False
        self.race_paused: bool = False        # Tracks whether the race is currently paused
        self.deck_id: Optional[int] = None    # ID of the deck being studied in the race
        
        # Nitro tracking
        self.nitro_streak: int = 0
        self.nitro_streak_history: list = []
        self.nitro_active: bool = False
        
        # Timing helpers
        self.start_time: float = 0.0
        self.elapsed_before_pause: float = 0.0 # Time accumulated before a pause

    def start_race(self, deck_id: int, settings: Dict[str, Any]) -> None:
        """Initializes the race state and reads cards to study for the selected deck."""
        from .config import race_config
        race_config.load()
        self.deck_id = deck_id
        self.mode = settings.get("mode", "normale")
        self.chosen_time = float(settings.get("chosen_time", 5.0)) # Default 5 minutes
        self.advantage = float(settings.get("advantage", 0.0)) if self.mode == "fuga" else 0.0
        
        # Read the number of due cards from Anki
        self.answered_cards = 0
        if mw and mw.col:
            mw.col.decks.select(deck_id)
            self.total_cards = sum(mw.col.sched.counts())
        else:
            self.total_cards = self._get_due_card_count(deck_id)
        self.remaining_cards = self.total_cards
        
        # Reset positions (User starts at their advantage percentage)
        self.user_position = self.advantage
        self.cpu_position = 0.0
        self.elapsed_before_pause = 0.0
        self.race_paused = False
        
        self.nitro_streak = 0
        self.nitro_streak_history = []
        self.nitro_active = False
            
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

    def update_streak(self, is_good_easy: bool, is_undo: bool = False) -> None:
        """Updates the nitro streak based on whether the answer was Good/Easy and undo state."""
        if not self.race_in_progress:
            return
            
        from .config import race_config
        race_config.load()
        if not race_config.get("nitro_enabled", False):
            self.nitro_active = False
            self.nitro_streak = 0
            return
            
        if is_undo:
            if self.nitro_streak_history:
                self.nitro_streak = self.nitro_streak_history.pop()
            else:
                self.nitro_streak = 0
        else:
            # Push current to history before updating
            self.nitro_streak_history.append(self.nitro_streak)
            
            if is_good_easy:
                self.nitro_streak += 1
            else:
                self.nitro_streak = 0
                
        # Check if nitro boost is active for this update
        target_streak = int(race_config.get("nitro_cards", 5))
        self.nitro_active = (self.nitro_streak >= target_streak)

    def update_remaining(self, remaining: int, is_undo: bool = False) -> None:
        """Updates remaining cards and adjusts total cards start target to handle added cards/undo."""
        if not self.race_in_progress:
            return
            
        if not is_undo and remaining > self.remaining_cards:
            diff = remaining - self.remaining_cards
            self.total_cards += diff
            
        self.remaining_cards = remaining
        self.calculate_positions()

    def calculate_positions(self) -> None:
        """Calculates user and CPU positions based on card progress and time elapsed."""
        if not self.race_in_progress:
            return

        # 1. User position (advances based on done cards / total active cards at start)
        if self.total_cards > 0:
            done_cards = self.total_cards - self.remaining_cards
            progress_ratio = done_cards / self.total_cards
            self.user_position = min(100.0, self.advantage + ((100.0 - self.advantage) * progress_ratio))
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

    def get_race_stats(self) -> Dict[str, Any]:
        """Calculates elapsed time, answered cards count, and average seconds per card."""
        elapsed = self.elapsed_before_pause
        if not self.race_paused and self.start_time > 0:
            import time
            elapsed += time.time() - self.start_time
            
        completed = self.total_cards - self.remaining_cards
        avg_sec = (elapsed / completed) if completed > 0 else 0.0
        
        return {
            "elapsed": elapsed,
            "cards_answered": completed,
            "avg_seconds": avg_sec
        }

    def on_card_answered(self, correct: bool) -> None:
        """Deprecated: hook handles updating counts now."""
        pass

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
