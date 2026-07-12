"""Storage-Schicht Haushaltskasse (SQLite, projektspezifisch).

Storage wird nie direkt angesprochen — immer über diese Schicht.
"""
from .db import connect, init_db, kennzahlen

__all__ = ["connect", "init_db", "kennzahlen"]
