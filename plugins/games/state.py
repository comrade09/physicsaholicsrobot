"""
games/state.py
----------------
Lightweight in-memory state for "live" games (trivia in progress, a tic-tac-toe
board mid-match, an open horse race betting window, etc).

Only END RESULTS (aura/karma/wins) are persisted to Mongo via db.py — the
turn-by-turn game state lives here in RAM, keyed by chat_id (or, for
per-player games like Blackjack, by (chat_id, user_id)).

If your bot runs multiple processes/workers, this state will NOT be shared
across them. For a single-process bot (the normal case) this is fine.
"""

active_games: dict = {}   # key -> {"type": str, "data": dict}


def start_game(key, game_type: str, data: dict):
    active_games[key] = {"type": game_type, "data": data}


def get_game(key):
    return active_games.get(key)


def update_game_data(key, **kwargs):
    if key in active_games:
        active_games[key]["data"].update(kwargs)


def end_game(key):
    active_games.pop(key, None)


def is_busy(key) -> bool:
    return key in active_games
