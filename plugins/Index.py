import re
import time
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot

# IMPORT YOUR MONGODB COLLECTION HERE
from database import stream_videos_collection
# Ensure this matches the collection name you use for your video stream data.

# Regex pattern to identify your codes (e.g., "DB0149", "CC0248")
CODE_PATTERN = r"([A-Z]{2}\d{4})" 

# Assuming you have a list of Admin IDs in your bot config
ADMIN_IDS = [123456789] # Replace with your actual Telegram User ID

@Bot.on_message(filters.command("index") & filters.user(ADMIN_IDS) & filters.private)
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
    
    # Initialize the timestamp for our 5-second interval
    last_update_time = time.time()
    
    try:
        async for msg in bot.get_chat_history(channel_id):
            scanned_count += 1
            text_content = msg.caption or msg.text
            
            if text_content:
                match = re.search(CODE_PATTERN, text_content)
                if match:
                    file_code = match.group(1)
                    
                    # Check if it already exists in your MongoDB
                    exists = await stream_videos_collection.find_one({"code": file_code})
                    
                    if exists:
                        skipped_count += 1
                    else:
                        await stream_videos_collection.insert_one({
                            "code": file_code,
                            "message_id": msg.id,
                            "channel_id": channel_id
                        })
                        indexed_count += 1
                
            # Check if 5 seconds have passed since the last edit
            current_time = time.time()
            if current_time - last_update_time >= 5:
                await status_msg.edit_text(
                    f"🔄 **Indexing in progress...**\n\n"
                    f"📦 **Channel:** `{channel_id}`\n"
                    f"🔍 **Messages Scanned:** {scanned_count}\n"
                    f"✅ **New Added:** {indexed_count}\n"
                    f"⏭ **Skipped (Dupes):** {skipped_count}"
                )
                last_update_time = current_time # Reset the timer
                
        # Final success message when the loop completely finishes
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
            f"**Troubleshooting:** Make sure the bot is added as an **Admin** in `{channel_id}`."
        )
