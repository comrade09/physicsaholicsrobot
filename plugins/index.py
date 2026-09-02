import re
import time
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from bot import Bot

# Importing your synchronous PyMongo collection
from database.videos import video_collection

# Strictly matches exactly 2 Uppercase Letters followed by exactly 4 Digits (e.g., "MC0176")
CODE_PATTERN = r"([A-Z]{2}\d{4})" 

# Your Admin ID
ADMIN_IDS = [1442684727]

@Bot.on_message(filters.command("index") & filters.user(ADMIN_IDS) & filters.private,group=6436)
async def auto_index_channel(bot: Bot, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a channel ID.\nUsage: `/index -100123456789`")
        
    channel_id_str = message.command[1]
    
    try:
        channel_id = int(channel_id_str)
    except ValueError:
        return await message.reply_text("❌ Invalid Channel ID format. Must be a number like -100123456789")
        
    status_msg = await message.reply_text(f"⏳ Starting deep index for `{channel_id}`... This may take a while.")
    
    indexed_count = 0
    skipped_count = 0
    scanned_count = 0
    
    last_update_time = time.time()
    
    try:
        # Iterates from newest to oldest message in the channel
        async for msg in bot.get_chat_history(channel_id):
            scanned_count += 1
            # Check caption first for videos, fallback to text
            text_content = msg.caption or msg.text
            
            if text_content:
                # Search for the AB0000 format in the caption
                match = re.search(CODE_PATTERN, text_content)
                if match:
                    file_code = match.group(1).upper()
                    
                    # Check if code already exists in MongoDB
                    exists = video_collection.find_one({'_id': file_code})
                    
                    if exists:
                        skipped_count += 1
                    else:
                        # Saves the code, message_id, and channel_id to support multiple channels
                        video_collection.update_one(
                            {'_id': file_code},
                            {'$set': {
                                'message_id': msg.id,
                                'channel_id': channel_id
                            }},
                            upsert=True
                        )
                        indexed_count += 1
                
            # Update the status message every 5 seconds
            current_time = time.time()
            if current_time - last_update_time >= 5:
                try:
                    await status_msg.edit_text(
                        f"🔄 **Indexing in progress...**\n\n"
                        f"📦 **Channel:** `{channel_id}`\n"
                        f"🔍 **Messages Scanned:** {scanned_count}\n"
                        f"✅ **New Added:** {indexed_count}\n"
                        f"⏭ **Skipped (Dupes):** {skipped_count}"
                    )
                except FloodWait as e:
                    # Prevents the bot from crashing if it edits too quickly
                    await asyncio.sleep(e.value)
                except Exception:
                    pass 
                    
                last_update_time = time.time()
                
        # Final summary once all messages are scanned
        await status_msg.edit_text(
            f"✅ **Indexing Complete!**\n\n"
            f"📦 **Channel:** `{channel_id}`\n"
            f"🔍 **Total Messages Scanned:** {scanned_count}\n"
            f"✅ **Total New Added:** {indexed_count}\n"
            f"⏭ **Total Skipped:** {skipped_count}"
        )
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Error during indexing:**\n`{str(e)}`\n\n"
            f"**Troubleshooting:** Make sure the bot is an **Admin** in `{channel_id}`."
        )
        
