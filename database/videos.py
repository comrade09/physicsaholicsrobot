import pymongo
from config import DB_URI, DB_NAME

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]
video_collection = database['stream_videos']

async def save_video_code(question_code: str, message_id: int):
    video_collection.update_one(
        {'_id': question_code.upper()},
        {'$set': {'message_id': message_id}},
        upsert=True
    )

async def get_video_message_id(question_code: str):
    data = video_collection.find_one({'_id': question_code.upper()})
    return data.get('message_id') if data else None

# --- NEW ANALYTICS FUNCTIONS ---

async def increment_view_count(question_code: str):
    """Increments the search/view counter for a specific code."""
    video_collection.update_one(
        {'_id': question_code.upper()},
        {'$inc': {'views': 1}},
        upsert=True
    )

async def get_top_videos(limit: int = 10):
    """Fetches the top most searched videos."""
    cursor = video_collection.find({'views': {'$exists': True}}).sort('views', -1).limit(limit)
    return list(cursor)

# -------------------------------

async def count_total_videos() -> int:
    return video_collection.count_documents({})

async def delete_single_video(question_code: str) -> bool:
    result = video_collection.delete_one({'_id': question_code.upper()})
    return result.deleted_count > 0

async def delete_all_video_records() -> int:
    result = video_collection.delete_many({})
    return result.deleted_count

async def get_recent_codes(limit: int = 5):
    cursor = video_collection.find().sort('_id', -1).limit(limit)
    return [doc['_id'] for doc in cursor]

async def get_all_records():
    return list(video_collection.find({}))
