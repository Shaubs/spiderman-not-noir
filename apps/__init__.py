"""
Application Entry Points

Web shooter application variants.
- web_shooter.py: Landmarks mode (shows hand skeleton)
- web_shooter_glove.py: Glove mode (filled red hand)
- web_shooter_base.py: Shared base class
"""

from .web_shooter_base import BaseWebShooter

__all__ = [
    'BaseWebShooter',
]
