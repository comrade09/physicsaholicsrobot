import re
from pyrogram import Client, filters
from pyrogram.types import Message
from database.videos import save_video_code

DUMP_CHANNEL_ID = -1003946902565

# Changed to group=-1 so it runs BEFORE CodeXBotz's default plugins intercept it
@Client.on_message(filters.chat(DUMP_CHANNEL_ID) & (filters.video | filters.document))
async def auto_save_channel_video(bot: Client, message: Message):
    
    # 1. First debug print - proves the bot actually saw the video
    print(f"👀 New video detected in channel! Message ID: {message.id}")
    
    # message.caption extracts the raw text automatically, ignoring bold/HTML formatting
    caption = message.caption or message.text or ""
    
    # 2. Scans anywhere in the text for 2 letters followed by 4 numbers
    match = re.search(r"([a-zA-Z]{2}\d{4})", caption)
    
    if not match:
        print("❌ Ignored: No question code (like DB0149) was found in the caption.")
        return
        
    question_code = match.group(1).upper()
    await save_video_code(question_code, message.id)
    
    # 3. Final success print
    print(f"✅ SUCCESS! Extracted Code: {question_code} -> Saved to Database.")
