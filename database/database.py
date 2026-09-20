import os
import time
import math
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME
from bson import ObjectId

# Use Motor for async MongoDB operations
dbclient = AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

user_data = database['users']
accounts_data = database['accounts']
batches_data = database['batches']

# --- GYM TRACKER COLLECTIONS ---
gym_profiles = database['gym_profiles']
gym_workouts = database['gym_workouts']
gym_prs = database['gym_prs']


# --- USER FUNCTIONS ---

async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    await user_data.insert_one({'_id': user_id})

async def full_userbase():
    # Motor requires .to_list() to fetch all documents
    user_docs = await user_data.find().to_list(length=None)
    return [doc['_id'] for doc in user_docs]

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})


# --- TELETHON STRING SESSION FUNCTIONS ---

async def save_session(user_id: int, session_string: str):
    """Saves the Telethon string session to MongoDB for a specific user."""
    await user_data.update_one(
        {'_id': user_id},
        {'$set': {'session_string': session_string}},
        upsert=True
    )

async def get_session(user_id: int):
    """Retrieves the Telethon string session from MongoDB."""
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('session_string')
    return None

async def delete_session(user_id: int):
    """Deletes the saved string session."""
    await user_data.update_one(
        {'_id': user_id},
        {'$unset': {'session_string': ""}}
    )


# --- ACCOUNTS LOGIC ---

async def add_new_person(user_id: int, name: str):
    await accounts_data.insert_one({
        "user_id": user_id,
        "name": name,
        "spent": 0.0,  
        "owed": 0.0,   
        "transactions": []
    })

async def get_people(user_id: int):
    return await accounts_data.find({"user_id": user_id}).to_list(length=None)

async def get_person_by_id(person_id: str):
    return await accounts_data.find_one({"_id": ObjectId(person_id)})

async def add_transaction(person_id: str, tx_type: str, amount: float, reason: str, date_str: str):
    inc_fields = {}
    if tx_type == 'spent': inc_fields["spent"] = amount
    elif tx_type == 'owed': inc_fields["owed"] = amount
    elif tx_type == 'they_paid': inc_fields["spent"] = -amount  
    elif tx_type == 'i_sent': inc_fields["owed"] = -amount   

    await accounts_data.update_one(
        {"_id": ObjectId(person_id)},
        {
            "$inc": inc_fields,
            "$push": {
                "transactions": {
                    "date": date_str,
                    "amount": amount,
                    "type": tx_type,
                    "reason": reason
                }
            }
        }
    )

async def get_total_stats(user_id: int):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_spending": {"$sum": "$spent"},
            "total_debt": {"$sum": "$owed"}
        }}
    ]
    result = await accounts_data.aggregate(pipeline).to_list(length=1)
    if result:
        return result[0].get("total_spending", 0.0), result[0].get("total_debt", 0.0)
    return 0.0, 0.0


# --- BATCHES LOGIC FOR TELEGRAM BOT ---

async def get_batch(batch_id: str):
    return await batches_data.find_one({"batch_id": batch_id})

async def get_all_batches():
    return await batches_data.find({}, {"_id": 0}).to_list(length=None)

async def update_batch_data(batch_id: str, batch_title: str, batch_url: str, teachers: list, last_updated: str):
    await batches_data.update_one(
        {"batch_id": batch_id},
        {
            "$set": {
                "batch_id": batch_id,
                "batch_title": batch_title,
                "batch_url": batch_url,
                "teachers": teachers,
                "last_updated": last_updated
            }
        },
        upsert=True
    )


# =====================================================================
# GYM PROGRESS TRACKER LOGIC
# =====================================================================

# --- Level curve -----------------------------------------------------
# XP required to clear level N grows ~15% per level, starting at 100 XP.
# calculate_level() turns a lifetime XP total into (level, xp_into_level, xp_needed_for_next).

LEVEL_XP_BASE = 100
LEVEL_XP_GROWTH = 1.15

LEVEL_TITLES = [
    (1, "Rookie"),
    (6, "Trainee"),
    (11, "Lifter"),
    (16, "Grinder"),
    (21, "Beast"),
    (26, "Veteran"),
    (31, "Elite"),
    (41, "Legend"),
    (51, "Titan"),
]

def _title_for_level(level: int) -> str:
    title = LEVEL_TITLES[0][1]
    for threshold, name in LEVEL_TITLES:
        if level >= threshold:
            title = name
        else:
            break
    return title

def calculate_level(total_xp: float):
    """Returns (level, xp_into_current_level, xp_needed_for_next_level, title)."""
    level = 1
    remaining = max(0.0, total_xp)
    xp_needed = LEVEL_XP_BASE
    while remaining >= xp_needed:
        remaining -= xp_needed
        level += 1
        xp_needed = int(LEVEL_XP_BASE * (LEVEL_XP_GROWTH ** (level - 1)))
    return level, round(remaining), xp_needed, _title_for_level(level)


# --- Profile -----------------------------------------------------------

async def get_gym_profile(user_id: int):
    return await gym_profiles.find_one({'_id': user_id})

async def is_gym_profile_complete(user_id: int) -> bool:
    profile = await get_gym_profile(user_id)
    if not profile:
        return False
    return all(profile.get(field) for field in ("height_cm", "weight_kg", "age"))

async def save_gym_profile(user_id: int, height_cm: float = None, weight_kg: float = None,
                            age: int = None, gender: str = None, activity_level: str = None,
                            name: str = None):
    """Upserts whichever fields are provided; keeps existing values for the rest."""
    now = datetime.utcnow()
    set_fields = {"updated_at": now}
    if height_cm is not None: set_fields["height_cm"] = float(height_cm)
    if weight_kg is not None: set_fields["weight_kg"] = float(weight_kg)
    if age is not None: set_fields["age"] = int(age)
    if gender is not None: set_fields["gender"] = gender
    if activity_level is not None: set_fields["activity_level"] = activity_level
    if name is not None: set_fields["name"] = name

    await gym_profiles.update_one(
        {'_id': user_id},
        {
            "$set": set_fields,
            "$setOnInsert": {"xp": 0, "created_at": now, "weight_log": []},
        },
        upsert=True
    )

    # Keep a weight-over-time history for the progress chart
    if weight_kg is not None:
        await gym_profiles.update_one(
            {'_id': user_id},
            {"$push": {"weight_log": {"date": now, "weight_kg": float(weight_kg)}}}
        )

    return await get_gym_profile(user_id)

async def get_weight_history(user_id: int, limit: int = 60):
    profile = await get_gym_profile(user_id)
    if not profile:
        return []
    log = profile.get("weight_log", [])
    return log[-limit:]


# --- XP / Levels ---------------------------------------------------------

async def add_xp(user_id: int, amount: int):
    """Adds XP and returns (old_level, new_level, total_xp) so callers can detect level-ups."""
    profile = await get_gym_profile(user_id) or {}
    old_xp = profile.get("xp", 0)
    old_level, *_ = calculate_level(old_xp)

    await gym_profiles.update_one(
        {'_id': user_id},
        {"$inc": {"xp": amount}, "$setOnInsert": {"created_at": datetime.utcnow(), "weight_log": []}},
        upsert=True
    )

    new_profile = await get_gym_profile(user_id)
    new_xp = new_profile.get("xp", 0)
    new_level, *_ = calculate_level(new_xp)
    return old_level, new_level, new_xp

async def get_level_info(user_id: int):
    profile = await get_gym_profile(user_id) or {}
    total_xp = profile.get("xp", 0)
    level, xp_into, xp_needed, title = calculate_level(total_xp)
    return {
        "level": level,
        "title": title,
        "total_xp": total_xp,
        "xp_into_level": xp_into,
        "xp_needed": xp_needed,
        "progress_pct": round((xp_into / xp_needed) * 100, 1) if xp_needed else 0,
    }


# --- Workout logging -------------------------------------------------------

def _calc_volume(sets: list) -> float:
    """sets = [{'reps': int, 'weight': float}, ...] -> total kg lifted."""
    return sum(float(s.get("reps", 0)) * float(s.get("weight", 0)) for s in sets)

async def log_workout(user_id: int, exercise_name: str, muscle: str, sets: list, notes: str = None):
    """
    Logs a workout entry, updates the PR collection if a new record was hit,
    and awards XP (base + per-set + PR bonus).
    Returns a dict describing what happened, for the bot/mini-app to display.
    """
    now = datetime.utcnow()
    volume = _calc_volume(sets)
    max_weight = max((float(s.get("weight", 0)) for s in sets), default=0)
    max_reps = max((int(s.get("reps", 0)) for s in sets), default=0)

    entry = {
        "user_id": user_id,
        "exercise": exercise_name,
        "muscle": muscle,
        "sets": sets,
        "volume": volume,
        "notes": notes,
        "date": now,
    }
    result = await gym_workouts.insert_one(entry)

    # --- PR check ---
    existing_pr = await gym_prs.find_one({"user_id": user_id, "exercise": exercise_name})
    is_new_pr = False
    pr_type = None
    if not existing_pr:
        is_new_pr = True
        pr_type = "first_log"
        await gym_prs.insert_one({
            "user_id": user_id,
            "exercise": exercise_name,
            "muscle": muscle,
            "max_weight": max_weight,
            "max_reps": max_reps,
            "best_volume": volume,
            "achieved_at": now,
        })
    else:
        updates = {}
        if max_weight > existing_pr.get("max_weight", 0):
            updates["max_weight"] = max_weight
            pr_type = "weight"
            is_new_pr = True
        if max_reps > existing_pr.get("max_reps", 0):
            updates["max_reps"] = max_reps
            pr_type = "weight" if is_new_pr else "reps"
            is_new_pr = True
        if volume > existing_pr.get("best_volume", 0):
            updates["best_volume"] = volume
            if not is_new_pr:
                pr_type = "volume"
            is_new_pr = True
        if updates:
            updates["achieved_at"] = now
            await gym_prs.update_one({"_id": existing_pr["_id"]}, {"$set": updates})

    # --- XP award ---
    xp_gain = 20 + (len(sets) * 3) + (50 if is_new_pr else 0)
    old_level, new_level, total_xp = await add_xp(user_id, xp_gain)

    return {
        "workout_id": str(result.inserted_id),
        "volume": volume,
        "is_new_pr": is_new_pr,
        "pr_type": pr_type,
        "xp_gain": xp_gain,
        "leveled_up": new_level > old_level,
        "old_level": old_level,
        "new_level": new_level,
        "total_xp": total_xp,
    }

async def get_workout_history(user_id: int, limit: int = 50, muscle: str = None, exercise: str = None):
    query = {"user_id": user_id}
    if muscle:
        query["muscle"] = muscle
    if exercise:
        query["exercise"] = exercise
    cursor = gym_workouts.find(query).sort("date", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def delete_workout(user_id: int, workout_id: str):
    await gym_workouts.delete_one({"_id": ObjectId(workout_id), "user_id": user_id})


# --- Personal Records -----------------------------------------------------

async def get_prs(user_id: int):
    cursor = gym_prs.find({"user_id": user_id}).sort("achieved_at", -1)
    return await cursor.to_list(length=None)

async def get_pr_for_exercise(user_id: int, exercise_name: str):
    return await gym_prs.find_one({"user_id": user_id, "exercise": exercise_name})


# --- Stats / Charts ---------------------------------------------------------

async def get_muscle_stats(user_id: int, days: int = 30):
    """Total volume lifted per muscle group in the last `days` days — feeds a pie/bar chart."""
    since = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": since}}},
        {"$group": {"_id": "$muscle", "total_volume": {"$sum": "$volume"}, "sessions": {"$sum": 1}}},
        {"$sort": {"total_volume": -1}},
    ]
    result = await gym_workouts.aggregate(pipeline).to_list(length=None)
    return [{"muscle": r["_id"], "volume": r["total_volume"], "sessions": r["sessions"]} for r in result]

async def get_weekly_volume(user_id: int, weeks: int = 8):
    """Total volume per ISO week for the last N weeks — feeds a line/bar progress chart."""
    since = datetime.utcnow() - timedelta(weeks=weeks)
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": since}}},
        {"$group": {
            "_id": {"year": {"$isoWeekYear": "$date"}, "week": {"$isoWeek": "$date"}},
            "total_volume": {"$sum": "$volume"},
            "sessions": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.week": 1}},
    ]
    result = await gym_workouts.aggregate(pipeline).to_list(length=None)
    return [
        {"year": r["_id"]["year"], "week": r["_id"]["week"], "volume": r["total_volume"], "sessions": r["sessions"]}
        for r in result
    ]

async def get_streak(user_id: int):
    """Current consecutive-day workout streak."""
    cursor = gym_workouts.find({"user_id": user_id}, {"date": 1}).sort("date", -1)
    dates = sorted({d["date"].date() for d in await cursor.to_list(length=1000)}, reverse=True)
    if not dates:
        return 0
    streak = 1
    today = datetime.utcnow().date()
    if dates[0] not in (today, today - timedelta(days=1)):
        return 0
    for i in range(len(dates) - 1):
        if (dates[i] - dates[i + 1]).days == 1:
            streak += 1
        else:
            break
    return streak

async def get_dashboard_summary(user_id: int):
    """One aggregated payload the mini-app home screen can render in a single call."""
    profile = await get_gym_profile(user_id)
    level_info = await get_level_info(user_id)
    prs = await get_prs(user_id)
    muscle_stats = await get_muscle_stats(user_id, days=30)
    weekly_volume = await get_weekly_volume(user_id, weeks=8)
    streak = await get_streak(user_id)
    recent = await get_workout_history(user_id, limit=10)

    bmi = None
    if profile and profile.get("height_cm") and profile.get("weight_kg"):
        h_m = profile["height_cm"] / 100
        bmi = round(profile["weight_kg"] / (h_m * h_m), 1)

    return {
        "profile": {
            "height_cm": profile.get("height_cm") if profile else None,
            "weight_kg": profile.get("weight_kg") if profile else None,
            "age": profile.get("age") if profile else None,
            "gender": profile.get("gender") if profile else None,
            "activity_level": profile.get("activity_level") if profile else None,
            "bmi": bmi,
        } if profile else None,
        "profile_complete": await is_gym_profile_complete(user_id),
        "level": level_info,
        "streak_days": streak,
        "pr_count": len(prs),
        "prs": prs[:10],
        "muscle_stats": muscle_stats,
        "weekly_volume": weekly_volume,
        "recent_workouts": recent,
    }
