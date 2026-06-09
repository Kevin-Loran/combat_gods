import json
import os
import time
from settings import PROJECT_DIR

ANALYTICS_FILE = os.path.join(PROJECT_DIR, "player_habits.json")

class CombatTracker:
    def __init__(self):
        self.reset_session()
        self.load_global_habits()

    def reset_session(self):
        """Reset data for a single fight session."""
        self.session_data = {
            "attacks": 0,
            "jumps": 0,
            "rolls": 0,
            "potions": 0,
            "damage_taken": 0,
            "air_attacks": 0,
            "distance_to_boss_sum": 0.0,
            "distance_samples": 0,
            "roll_after_hit": 0,  # Counts if player rolls within ~0.6s of hitting
            "hit_last_time": 0.0,
        }

    def load_global_habits(self):
        """Load accumulated habits from disk."""
        if os.path.exists(ANALYTICS_FILE):
            try:
                with open(ANALYTICS_FILE, "r") as f:
                    self.global_data = json.load(f)
            except Exception as e:
                print(f"[analytics] Error loading habits: {e}")
                self.global_data = self._get_empty_global()
        else:
            self.global_data = self._get_empty_global()

    def _get_empty_global(self):
        return {
            "total_fights": 0,
            "style_profile": "Unknown",
            "habit_scores": {
                "aviator": 0.0,      # High jumping/air attacks
                "berserker": 0.0,    # Stays very close
                "twitchy": 0.0,      # Rolls immediately after attacking
            }
        }

    def log_event(self, event_type, value=1):
        if event_type in self.session_data:
            self.session_data[event_type] += value
        
        # Special logic for tracking "Roll after Hit"
        if event_type == "hit_boss":
            self.session_data["hit_last_time"] = time.time()
            self.session_data["attacks"] += 1
        
        if event_type == "rolls":
            if time.time() - self.session_data["hit_last_time"] < 0.6:
                self.session_data["roll_after_hit"] += 1

    def update_distance(self, dist):
        self.session_data["distance_to_boss_sum"] += dist
        self.session_data["distance_samples"] += 1

    def finalize_fight(self, won=True):
        """Process session data and merge into global habits."""
        # Only log if there was some activity (prevents empty restarts from polluting data)
        if self.session_data["attacks"] == 0 and self.session_data["damage_taken"] == 0:
            return

        self.global_data["total_fights"] += 1
        
        # Calculate session scores
        avg_dist = 0
        if self.session_data["distance_samples"] > 0:
            avg_dist = self.session_data["distance_to_boss_sum"] / self.session_data["distance_samples"]
        
        # Learning rate (alpha): how much this fight influences the average
        alpha = 0.4
        
        # 1. Aviator: ratio of air attacks and jump frequency
        air_ratio = 0
        if self.session_data["attacks"] > 0:
            air_ratio = self.session_data["air_attacks"] / self.session_data["attacks"]
        self.global_data["habit_scores"]["aviator"] = (1-alpha)*self.global_data["habit_scores"]["aviator"] + alpha*air_ratio
        
        # 2. Berserker: low average distance
        # Score 1.0 if dist < 120, scales down to 0 at dist 400
        dist_score = 1.0 - (max(0, avg_dist - 120) / 280)
        dist_score = max(0.0, min(1.0, dist_score))
        self.global_data["habit_scores"]["berserker"] = (1-alpha)*self.global_data["habit_scores"]["berserker"] + alpha*dist_score
        
        # 3. Twitchy: ratio of rolls happening after hits
        twitch_ratio = 0
        if self.session_data["attacks"] > 0:
            twitch_ratio = self.session_data["roll_after_hit"] / self.session_data["attacks"]
        self.global_data["habit_scores"]["twitchy"] = (1-alpha)*self.global_data["habit_scores"]["twitchy"] + alpha*twitch_ratio

        # Determine Style Profile
        scores = self.global_data["habit_scores"]
        top_habit = max(scores, key=scores.get)
        if scores[top_habit] > 0.35:
            self.global_data["style_profile"] = top_habit.capitalize()
        else:
            self.global_data["style_profile"] = "Balanced"

        self.save_to_disk()
        print(f"[analytics] Fight finalized. Profile: {self.global_data['style_profile']} (Habits: {scores})")

    def save_to_disk(self):
        try:
            with open(ANALYTICS_FILE, "w") as f:
                json.dump(self.global_data, f, indent=4)
        except Exception as e:
            print(f"[analytics] Error saving habits: {e}")

# Global instance
tracker = CombatTracker()
