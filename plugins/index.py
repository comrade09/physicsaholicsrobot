import re
import time
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait as PyrogramFloodWait
from bot import Bot

# Telethon imports for the Userbot scraper
from telethon import TelegramClient
from telethon.sessions import StringSession

# Import your databases
from database.videos import video_collection
from database.database import get_session

# Configuration for the Telethon User Client (Must match your login script)
API_ID = 13678305
API_HASH = 'a5d9be6f810f31e5c56bad6eebbd7ba8'

# Regex pattern for your codes
CODE_PATTERN = r"([A-Z]{2}\d{4})" 
ADMIN_IDS = [5496035221]

@Bot.on_message(filters.command("index") & filters.user(ADMIN_IDS) & filters.private,group=7836)
async def auto_index_channel(bot: Bot, message: Message):
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a channel ID.\nUsage: `/index -100123456789`")
        
    channel_id_str = message.command[1]
    
    try:
        channel_id = int(channel_id_str)
    except ValueError:
        return await message.reply_text("❌ Invalid Channel ID format. Must be a number like -100123456789")
        
    # Retrieve the Telethon session saved by your /login command
    session_str = await get_session(user_id)
    
    if not session_str:
        return await message.reply_text(
            "❌ **You are not logged in.**\n\n"
            "Please use the `/login` command first so the bot can use your account to scrape the channel."
        )
        
    status_msg = await message.reply_text(f"⏳ Starting Userbot deep index for `{channel_id}`...")
    
    indexed_count = 0
    skipped_count = 0
    scanned_count = 0
    last_update_time = time.time()
    
    # Initialize Telethon client using the saved session
    userbot = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    
    try:
        await userbot.connect()
        if not await userbot.is_user_authorized():
            await status_msg.edit_text("❌ String Session is invalid or expired. Please generate a new one using `/logout_session` then `/login`.")
            return

        # Telethon's iter_messages handles fetching the channel history smoothly without Bot API limits
        async for msg in userbot.iter_messages(channel_id):
            scanned_count += 1
            
            # In Telethon, msg.text safely grabs both standard text and media captions
            text_content = msg.text
            
            if text_content:
                match = re.search(CODE_PATTERN, text_content)
                if match:
                    file_code = match.group(1).upper()
                    
                    # Synchronous PyMongo check
                    exists = video_collection.find_one({'_id': file_code})
                    
                    if exists:
                        skipped_count += 1
                    else:
                        video_collection.update_one(
                            {'_id': file_code},
                            {'$set': {
                                'message_id': msg.id,
                                'channel_id': channel_id
                            }},
                            upsert=True
                        )
                        indexed_count += 1
                
            # Update Pyrogram status message every 5 seconds
            current_time = time.time()
            if current_time - last_update_time >= 5:
                try:
                    await status_msg.edit_text(
                        f"🔄 **Userbot Indexing...**\n\n"
                        f"📦 **Channel:** `{channel_id}`\n"
                        f"🔍 **Messages Scanned:** {scanned_count}\n"
                        f"✅ **New Added:** {indexed_count}\n"
                        f"⏭ **Skipped (Dupes):** {skipped_count}"
                    )
                except PyrogramFloodWait as e:
                    # Catch Pyrogram rate limits if we edit the message too fast
                    await asyncio.sleep(e.value)
                except Exception:
                    pass 
                    
                last_update_time = time.time()
                
        # Final Success Message
        await status_msg.edit_text(
            f"✅ **Userbot Indexing Complete!**\n\n"
            f"📦 **Channel:** `{channel_id}`\n"
            f"🔍 **Total Messages Scanned:** {scanned_count}\n"
            f"✅ **Total New Added:** {indexed_count}\n"
            f"⏭ **Total Skipped:** {skipped_count}"
        )
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Error during Userbot indexing:**\n`{str(e)}`\n\n"
            f"**Troubleshooting:** Make sure the account you logged in with is actually a member of `{channel_id}`."
        )
    finally:
        # Always gracefully disconnect the Telethon client when done
        await userbot.disconnect()
        
