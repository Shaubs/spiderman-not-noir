"""
Game Screen Manager

Handles:
- Intro screen with story and instructions
- In-game HUD (score, combo, balls destroyed)
- Game over screen with final score
- Scoreboard display
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple
from dataclasses import dataclass

from score_config import Scoreboard, GameScore, ScoreConfig


@dataclass
class GameStats:
    """Current game statistics."""
    webs_shot: int = 0
    balls_destroyed: int = 0
    hits_taken: int = 0
    combo: int = 0
    max_combo: int = 0
    grayscale_coverage: float = 0.0  # 0.0 to 1.0
    game_start_time: float = 0.0
    
    @property
    def elapsed_time(self) -> float:
        if self.game_start_time == 0:
            return 0.0
        return time.time() - self.game_start_time
    
    @property
    def elapsed_str(self) -> str:
        secs = int(self.elapsed_time)
        mins = secs // 60
        secs = secs % 60
        return f"{mins}:{secs:02d}"


class GameScreenManager:
    """
    Manages all game screen states: intro, playing, game over.
    """
    
    # Colors (BGR)
    RED = (0, 0, 200)
    BLUE = (200, 50, 50)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    YELLOW = (0, 255, 255)
    GREEN = (0, 255, 0)
    DARK_OVERLAY = (20, 20, 20)
    
    # Story text
    STORY_LINES = [
        "NEW YORK CITY, 2026",
        "",
        "The symbiotes have evolved.",
        "They don't just infect bodies anymore -",
        "they infect REALITY itself.",
        "",
        "Every symbiote ball that reaches the screen",
        "turns the world NOIR - grayscale, lifeless.",
        "",
        "You are the ONLY one who can stop them.",
        "Use your web shooters to destroy the symbiotes",
        "before they drain all color from the world.",
        "",
        "When the screen goes completely NOIR...",
        "it's GAME OVER.",
    ]
    
    INSTRUCTIONS = [
        "HOW TO PLAY:",
        "",
        "1. Show the SPIDER-MAN hand gesture",
        "   (thumb + index + pinky extended)",
        "",
        "2. Move your hand UP to ARM the web",
        "",
        "3. Move your hand DOWN to SHOOT!",
        "",
        "Destroy symbiotes before they hit the screen!",
    ]
    
    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scoreboard = Scoreboard()
        self.stats = GameStats()
        
        # State
        self.state = "intro"  # intro, playing, game_over
        self.intro_start_time = time.time()
        self.game_over_time: Optional[float] = None
        self.final_score: Optional[GameScore] = None
        
        # Animation
        self.blink_state = True
        self.last_blink_time = time.time()
    
    def start_game(self):
        """Transition from intro to playing."""
        self.state = "playing"
        self.stats = GameStats()
        self.stats.game_start_time = time.time()
        self.scoreboard.start_game()
        self.game_over_time = None
        self.final_score = None
    
    def end_game(self, player_name: str = "Player"):
        """Transition to game over."""
        if self.state == "game_over":
            return  # Already ended
        
        self.state = "game_over"
        self.game_over_time = time.time()
        
        # Record score
        self.final_score = self.scoreboard.end_game(
            player_name=player_name,
            webs_shot=self.stats.webs_shot,
            balls_destroyed=self.stats.balls_destroyed,
            hits_taken=self.stats.hits_taken,
        )
    
    def reset_to_intro(self):
        """Reset to intro screen."""
        self.state = "intro"
        self.intro_start_time = time.time()
        self.stats = GameStats()
        self.game_over_time = None
        self.final_score = None
    
    def update_stats(self, webs_shot: int, balls_destroyed: int, hits_taken: int,
                     combo: int, grayscale_coverage: float):
        """Update game statistics."""
        self.stats.webs_shot = webs_shot
        self.stats.balls_destroyed = balls_destroyed
        self.stats.hits_taken = hits_taken
        self.stats.combo = combo
        self.stats.max_combo = max(self.stats.max_combo, combo)
        self.stats.grayscale_coverage = grayscale_coverage
        
        # Check for game over condition
        if grayscale_coverage >= 1.0 and self.state == "playing":
            self.end_game()
    
    def render_intro(self, frame: np.ndarray) -> np.ndarray:
        """Render intro screen with story and instructions."""
        h, w = frame.shape[:2]
        
        # Dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), self.DARK_OVERLAY, -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)
        
        # Title
        title = "SPIDER-MAN: NOT NOIR"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 2.0, 3)[0]
        title_x = (w - title_size[0]) // 2
        cv2.putText(frame, title, (title_x, 80),
                    cv2.FONT_HERSHEY_DUPLEX, 2.0, self.RED, 3)
        
        # Subtitle
        subtitle = "A SYMBIOTE SURVIVAL GAME"
        sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        sub_x = (w - sub_size[0]) // 2
        cv2.putText(frame, subtitle, (sub_x, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.BLUE, 2)
        
        # Story (left side)
        story_x = 50
        story_y = 180
        for line in self.STORY_LINES:
            if line == "":
                story_y += 15
            else:
                cv2.putText(frame, line, (story_x, story_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.WHITE, 1)
                story_y += 28
        
        # Instructions (right side)
        inst_x = w // 2 + 50
        inst_y = 180
        for line in self.INSTRUCTIONS:
            if line == "":
                inst_y += 15
            else:
                color = self.YELLOW if line.startswith("HOW") else self.WHITE
                cv2.putText(frame, line, (inst_x, inst_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
                inst_y += 28
        
        # Blinking "Press SPACE to start"
        if time.time() - self.last_blink_time > 0.5:
            self.blink_state = not self.blink_state
            self.last_blink_time = time.time()
        
        if self.blink_state:
            start_text = ">>> PRESS SPACE TO START <<<"
            start_size = cv2.getTextSize(start_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            start_x = (w - start_size[0]) // 2
            cv2.putText(frame, start_text, (start_x, h - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.GREEN, 2)
        
        # Show high score if exists
        leaderboard = self.scoreboard.get_leaderboard(limit=1)
        if leaderboard:
            high_score = leaderboard[0].final_score
            hs_text = f"HIGH SCORE: {high_score}"
            hs_size = cv2.getTextSize(hs_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            hs_x = (w - hs_size[0]) // 2
            cv2.putText(frame, hs_text, (hs_x, h - 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.YELLOW, 2)
        
        return frame
    
    def render_hud(self, frame: np.ndarray) -> np.ndarray:
        """Render in-game HUD (heads-up display)."""
        h, w = frame.shape[:2]
        
        # Top bar background
        cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.rectangle(frame, (0, 0), (w, 50), self.RED, 2)
        
        # Left side: Score info
        score = self.scoreboard.calculate_score(
            self.stats.webs_shot,
            self.stats.balls_destroyed,
            self.stats.hits_taken
        )
        cv2.putText(frame, f"SCORE: {score}", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.WHITE, 2)
        
        # Center: Combo
        if self.stats.combo > 1:
            combo_text = f"COMBO x{self.stats.combo}!"
            combo_size = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
            combo_x = (w - combo_size[0]) // 2
            cv2.putText(frame, combo_text, (combo_x, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.YELLOW, 2)
        
        # Right side: Stats
        stats_text = f"DESTROYED: {self.stats.balls_destroyed}  HITS: {self.stats.hits_taken}  TIME: {self.stats.elapsed_str}"
        stats_size = cv2.getTextSize(stats_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        cv2.putText(frame, stats_text, (w - stats_size[0] - 10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.WHITE, 1)
        
        # Bottom: Noir meter (how much of screen is grayscale)
        meter_width = 300
        meter_height = 20
        meter_x = (w - meter_width) // 2
        meter_y = h - 40
        
        # Background
        cv2.rectangle(frame, (meter_x, meter_y), 
                      (meter_x + meter_width, meter_y + meter_height),
                      self.WHITE, 2)
        
        # Fill based on coverage
        fill_width = int(meter_width * self.stats.grayscale_coverage)
        if fill_width > 0:
            # Color goes from green to yellow to red as coverage increases
            if self.stats.grayscale_coverage < 0.5:
                color = self.GREEN
            elif self.stats.grayscale_coverage < 0.8:
                color = self.YELLOW
            else:
                color = self.RED
            cv2.rectangle(frame, (meter_x, meter_y),
                          (meter_x + fill_width, meter_y + meter_height),
                          color, -1)
        
        # Label
        noir_text = f"NOIR LEVEL: {int(self.stats.grayscale_coverage * 100)}%"
        noir_size = cv2.getTextSize(noir_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.putText(frame, noir_text, (meter_x + (meter_width - noir_size[0]) // 2, meter_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.WHITE, 1)
        
        return frame
    
    def render_game_over(self, frame: np.ndarray) -> np.ndarray:
        """Render game over screen."""
        h, w = frame.shape[:2]
        
        # The frame should already be mostly/fully grayscale
        # Add dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), self.BLACK, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        # GAME OVER title
        title = "GAME OVER"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 3.0, 4)[0]
        title_x = (w - title_size[0]) // 2
        cv2.putText(frame, title, (title_x, 150),
                    cv2.FONT_HERSHEY_DUPLEX, 3.0, self.RED, 4)
        
        # Subtitle
        subtitle = "THE WORLD HAS GONE NOIR"
        sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        sub_x = (w - sub_size[0]) // 2
        cv2.putText(frame, subtitle, (sub_x, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.WHITE, 2)
        
        # Final stats
        if self.final_score:
            stats_y = 280
            score = self.final_score
            
            stats = [
                f"FINAL SCORE: {score.final_score}",
                "",
                f"Symbiotes Destroyed: {score.balls_destroyed}",
                f"Hits Taken: {score.hits_taken}",
                f"Webs Shot: {score.webs_shot}",
                f"Survival Time: {int(score.duration_seconds // 60)}:{int(score.duration_seconds % 60):02d}",
                f"Max Combo: {self.stats.max_combo}",
            ]
            
            for stat in stats:
                if stat == "":
                    stats_y += 15
                else:
                    stat_size = cv2.getTextSize(stat, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                    stat_x = (w - stat_size[0]) // 2
                    color = self.YELLOW if "FINAL SCORE" in stat else self.WHITE
                    cv2.putText(frame, stat, (stat_x, stats_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    stats_y += 40
        
        # Leaderboard
        leaderboard = self.scoreboard.get_leaderboard(limit=5)
        if leaderboard:
            lb_y = 520
            cv2.putText(frame, "TOP SCORES", ((w - 150) // 2, lb_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.YELLOW, 2)
            lb_y += 30
            
            for i, score in enumerate(leaderboard):
                rank_text = f"{i + 1}. {score.final_score} pts - {score.balls_destroyed} destroyed"
                cv2.putText(frame, rank_text, ((w - 350) // 2, lb_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.WHITE, 1)
                lb_y += 25
        
        # Blinking restart prompt
        if time.time() - self.last_blink_time > 0.5:
            self.blink_state = not self.blink_state
            self.last_blink_time = time.time()
        
        if self.blink_state:
            restart_text = ">>> PRESS SPACE TO PLAY AGAIN <<<"
            restart_size = cv2.getTextSize(restart_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            restart_x = (w - restart_size[0]) // 2
            cv2.putText(frame, restart_text, (restart_x, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.GREEN, 2)
        
        return frame
    
    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render appropriate screen based on state."""
        if self.state == "intro":
            return self.render_intro(frame)
        elif self.state == "playing":
            return self.render_hud(frame)
        elif self.state == "game_over":
            return self.render_game_over(frame)
        return frame
    
    def handle_key(self, key: int) -> bool:
        """
        Handle keypress. Returns True if game should continue running.
        """
        if key == ord(' '):  # Space bar
            if self.state == "intro":
                self.start_game()
            elif self.state == "game_over":
                self.reset_to_intro()
        elif key == ord('q'):
            return False
        return True
