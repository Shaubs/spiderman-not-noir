"""
Rendering Module

Graphics and visual effects rendering.
- GraphicsManager: THWIP effects, hand styling
- WebEffectRenderer: Web shooting visual effects
"""

from .graphics_manager import GraphicsManager, ThwipEffect
from .web_renderer import WebEffectRenderer, WebShot, WebLine

__all__ = [
    'GraphicsManager',
    'ThwipEffect',
    'WebEffectRenderer',
    'WebShot',
    'WebLine',
]
