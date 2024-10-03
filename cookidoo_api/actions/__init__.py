"""Cookidoo automation actions."""

from .clicker import clicker
from .hoverer import hoverer
from .scroller import scroller
from .selector import selector
from .state_waiter import state_waiter
from .waiter import waiter

__all__ = [
    "selector",
    "waiter",
    "scroller",
    "hoverer",
    "clicker",
    "state_waiter",
]