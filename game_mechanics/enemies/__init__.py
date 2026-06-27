"""
Enemy Systems

Symbiote balls and infection spread mechanics.
"""

from .symbiote import SymbioteBall, SymbioteManager
from .infection import InfectionSource, InfectionManager

__all__ = [
    'SymbioteBall',
    'SymbioteManager',
    'InfectionSource',
    'InfectionManager',
]
