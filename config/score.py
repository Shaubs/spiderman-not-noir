"""
Score and Game Configuration

Contains:
- ScoreConfig: Scoreboard and infection spread settings
- Score persistence and leaderboard
"""

from dataclasses import dataclass, field
from typing import List, Optional
import json
import time
from pathlib import Path


@dataclass
class ScoreConfig:
    """Configuration for scoring and infection spread."""
    
    # Infection spread (BFS rotten oranges)
    infection_enabled: bool = True
    infection_spread_rate: float = 1.0  # seconds per spread iteration
    infection_radius: int = 10  # pixels to infect per iteration
    infection_max_radius: int = 100  # max spread radius from hit point
    
    # Score multipliers
    destroy_points: int = 100
    hit_penalty: int = 50
    web_cost: int = 5  # small penalty for spamming webs
    
    # Combo system
    combo_window: float = 2.0  # seconds to maintain combo
    combo_multiplier: float = 0.5  # bonus per combo level


@dataclass
class GameScore:
    """Single game score record."""
    player_name: str
    webs_shot: int
    balls_destroyed: int
    hits_taken: int
    final_score: int
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)
    difficulty: str = "normal"
    
    def to_dict(self) -> dict:
        return {
            'player_name': self.player_name,
            'webs_shot': self.webs_shot,
            'balls_destroyed': self.balls_destroyed,
            'hits_taken': self.hits_taken,
            'final_score': self.final_score,
            'duration_seconds': self.duration_seconds,
            'timestamp': self.timestamp,
            'difficulty': self.difficulty,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameScore':
        return cls(**data)


class Scoreboard:
    """Manages game scores and leaderboard."""
    
    def __init__(self, scores_file: Optional[Path] = None, config: ScoreConfig = None):
        if scores_file is None:
            # Navigate up from config/ to find data/
            scores_file = Path(__file__).parent.parent / "data" / "scores.json"
        self.scores_file = scores_file
        self.config = config or ScoreConfig()
        self.scores: List[GameScore] = []
        
        # Current game state
        self.game_start_time: Optional[float] = None
        self.combo_count: int = 0
        self.last_destroy_time: float = 0
        
        self._load_scores()
    
    def _load_scores(self):
        """Load scores from file."""
        if self.scores_file.exists():
            try:
                with open(self.scores_file, 'r') as f:
                    data = json.load(f)
                    self.scores = [GameScore.from_dict(s) for s in data]
            except (json.JSONDecodeError, KeyError):
                self.scores = []
        else:
            self.scores = []
    
    def _save_scores(self):
        """Save scores to file."""
        self.scores_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.scores_file, 'w') as f:
            json.dump([s.to_dict() for s in self.scores], f, indent=2)
    
    def start_game(self):
        """Start tracking a new game."""
        self.game_start_time = time.time()
        self.combo_count = 0
        self.last_destroy_time = 0
    
    def calculate_score(self, webs_shot: int, balls_destroyed: int, hits_taken: int) -> int:
        """Calculate final score."""
        cfg = self.config
        
        # Base score
        destroy_score = balls_destroyed * cfg.destroy_points
        hit_penalty = hits_taken * cfg.hit_penalty
        web_penalty = webs_shot * cfg.web_cost
        
        # Final calculation
        score = destroy_score - hit_penalty - web_penalty
        return max(0, score)
    
    def record_destroy(self) -> int:
        """Record a ball destroy, return combo multiplier."""
        now = time.time()
        if now - self.last_destroy_time <= self.config.combo_window:
            self.combo_count += 1
        else:
            self.combo_count = 1
        self.last_destroy_time = now
        return self.combo_count
    
    def end_game(self, player_name: str, webs_shot: int, 
                 balls_destroyed: int, hits_taken: int, difficulty: str = "normal") -> GameScore:
        """End game and record score."""
        duration = time.time() - (self.game_start_time or time.time())
        final_score = self.calculate_score(webs_shot, balls_destroyed, hits_taken)
        
        score = GameScore(
            player_name=player_name,
            webs_shot=webs_shot,
            balls_destroyed=balls_destroyed,
            hits_taken=hits_taken,
            final_score=final_score,
            duration_seconds=duration,
            difficulty=difficulty,
        )
        
        self.scores.append(score)
        self._save_scores()
        return score
    
    def get_leaderboard(self, limit: int = 10, difficulty: Optional[str] = None) -> List[GameScore]:
        """Get top scores."""
        filtered = self.scores
        if difficulty:
            filtered = [s for s in filtered if s.difficulty == difficulty]
        
        return sorted(filtered, key=lambda s: s.final_score, reverse=True)[:limit]
    
    def get_stats_summary(self) -> dict:
        """Get aggregate statistics."""
        if not self.scores:
            return {'total_games': 0}
        
        return {
            'total_games': len(self.scores),
            'total_webs_shot': sum(s.webs_shot for s in self.scores),
            'total_balls_destroyed': sum(s.balls_destroyed for s in self.scores),
            'total_hits_taken': sum(s.hits_taken for s in self.scores),
            'highest_score': max(s.final_score for s in self.scores),
            'average_score': sum(s.final_score for s in self.scores) // len(self.scores),
        }


# Active configuration
ACTIVE_SCORE_CONFIG = ScoreConfig()

__all__ = [
    'ScoreConfig',
    'GameScore',
    'Scoreboard',
    'ACTIVE_SCORE_CONFIG',
]
