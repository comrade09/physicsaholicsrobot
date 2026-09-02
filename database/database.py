import os
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME
from bson import ObjectId

# Use Motor for async MongoDB operations
dbclient = AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

user_data = database['users']
accounts_data = database['accounts']
batches_data = database['batches']


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
