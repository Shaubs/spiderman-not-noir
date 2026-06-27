"""
Entities Module

Contains base classes and entity implementations for game objects:
- FlyingEntity: Base class for objects that fly towards the player
- EntityManager: Base class for managing collections of entities
"""

from .base import FlyingEntity, EntityManager

__all__ = [
    'FlyingEntity',
    'EntityManager',
]
