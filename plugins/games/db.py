"""
games/db.py
------------
Mongo (Motor) layer for the Aura / Karma / Games system.

This reuses your existing Mongo connection. It assumes your main
database file (the one you already have, with `dbclient` / `database`)
is importable as `database` -> i.e. `from database import database`.

If your file is named differently (e.g. `db.py`, `mongo.py`), just
change the import line below to match.
"""
import time
from database import database  # noqa: your existing Motor `database` object

# Collections (separate from your existing ones, so nothing collides)
aura_data = database['aura']                 # per-user GLOBAL aura + game stats
karma_data = database['karma']                # per-user GLOBAL karma
group_members = database['game_group_members']  # {chat_id, user_id} -> who has played in which group


# ---------------- REGISTRATION ----------------

async def ensure_registered(user_id: int, chat_id: int | None = None):
    """Call this at the top of any game handler. Creates user docs if missing
    and (if chat_id given) marks the user as a member of that group for
    leaderboard purposes."""
    await aura_data.update_one(
        {'_id': user_id},
        {'$setOnInsert': {'aura': 0, 'wins': 0, 'losses': 0, 'games_played': 0}},
        upsert=True
    )
    await karma_data.update_one(
        {'_id': user_id},
        {'$setOnInsert': {'karma': 0, 'last_given': {}}},
        upsert=True
    )
    if chat_id is not None:
        await group_members.update_one(
            {'chat_id': chat_id, 'user_id': user_id},
            {'$set': {'chat_id': chat_id, 'user_id': user_id}},
            upsert=True
        )


# ---------------- AURA ----------------

async def add_aura(user_id: int, amount: int):
    """amount can be negative (loss). Aura is allowed to go negative on purpose
    (that's the risk of betting games) — clamp here if you don't want that."""
    await aura_data.update_one({'_id': user_id}, {'$inc': {'aura': amount}}, upsert=True)


async def get_aura(user_id: int) -> int:
    doc = await aura_data.find_one({'_id': user_id})
    return doc.get('aura', 0) if doc else 0


async def record_result(user_id: int, won: bool):
    inc = {'games_played': 1, ('wins' if won else 'losses'): 1}
    await aura_data.update_one({'_id': user_id}, {'$inc': inc}, upsert=True)


async def get_user_stats(user_id: int) -> dict:
    doc = await aura_data.find_one({'_id': user_id}) or {}
    karma_doc = await karma_data.find_one({'_id': user_id}) or {}
    return {
        'aura': doc.get('aura', 0),
        'wins': doc.get('wins', 0),
        'losses': doc.get('losses', 0),
        'games_played': doc.get('games_played', 0),
        'karma': karma_doc.get('karma', 0),
    }


# ---------------- KARMA ----------------

async def add_karma(user_id: int, amount: int = 1):
    await karma_data.update_one({'_id': user_id}, {'$inc': {'karma': amount}}, upsert=True)


async def get_karma(user_id: int) -> int:
    doc = await karma_data.find_one({'_id': user_id})
    return doc.get('karma', 0) if doc else 0


async def can_give_karma(giver_id: int, receiver_id: int) -> bool:
    """One karma per (giver -> receiver) pair per 24h."""
    doc = await karma_data.find_one({'_id': giver_id})
    last = (doc or {}).get('last_given', {}).get(str(receiver_id))
    if last and (time.time() - last) < 86400:
        return False
    return True


async def mark_karma_given(giver_id: int, receiver_id: int):
    await karma_data.update_one(
        {'_id': giver_id},
        {'$set': {f'last_given.{receiver_id}': time.time()}},
        upsert=True
    )


# ---------------- LEADERBOARD (scoped to a single group) ----------------

async def get_group_leaderboard(chat_id: int, limit: int = 10):
    members = await group_members.find({'chat_id': chat_id}).to_list(length=None)
    user_ids = [m['user_id'] for m in members]
    if not user_ids:
        return []
    cursor = aura_data.find({'_id': {'$in': user_ids}}).sort('aura', -1).limit(limit)
    return await cursor.to_list(length=limit)
