import re
import time
import hmac
import hashlib
import base64
import json
import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from bot import Bot
from database.videos import get_video_message_id, increment_view_count

# --- CONFIGURATION ---
KOYEB_DOMAIN = "https://rational-karel-comet67-bc9013b6.koyeb.app"
CLOUDFLARE_DOMAIN = "https://twilight-mode-66ac.fusionfiner.workers.dev" # Replace with your CF Worker URL
SECRET_KEY = b"84b6f10c7931c890e0e1a967f6515f40192ea62f25608d0f7a75932598be6f2d"
DUMP_CHANNEL_ID = -1004478362115

# Rate Limiter State
USER_SEARCH_DATA = {}

def generate_koyeb_link(message_id: int) -> str:
    """Generates a signed expiring link pointing to the Koyeb stream (uses message_id)."""
    expire_time = int(time.time()) + 900  # 15 minutes
    payload = {"mid": message_id, "exp": expire_time}
    payload_bytes = json.dumps(payload).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{KOYEB_DOMAIN}/watch?data={encoded_payload}&sig={signature}"

def generate_cloudflare_link(file_id: str) -> str:
    """Generates a signed expiring link pointing to Cloudflare (uses file_id)."""
    expire_time = int(time.time()) + 900  # 15 minutes
    payload = {"fid": file_id, "exp": expire_time}
    payload_bytes = json.dumps(payload).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY, encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{CLOUDFLARE_DOMAIN}/watch?data={encoded_payload}&sig={signature}"

@Bot.on_message(filters.command(["search"]) & filters.private, group=3838)
async def search_question_code(bot: Bot, message: Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    # 🛑 1. ANTI-SPAM & RATE LIMITING
    if user_id not in USER_SEARCH_DATA:
        USER_SEARCH_DATA[user_id] = []
        
    # Clean up timestamps older than 60 seconds
    USER_SEARCH_DATA[user_id] = [t for t in USER_SEARCH_DATA[user_id] if current_time - t < 60]
    
    if len(USER_SEARCH_DATA[user_id]) >= 5:
        await message.reply_text(
            "⚠️ **Rate Limit Exceeded!**\n\nYou are searching too fast. Please wait 60 seconds before trying again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
        
    USER_SEARCH_DATA[user_id].append(current_time)

    # 2. Command Parsing
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Format:** `/search DB0149`", parse_mode=ParseMode.MARKDOWN)
        return
        
    question_code = message.command[1].upper()
    
    if not re.match(r"^[A-Z]{2}\d{4}$", question_code):
        await message.reply_text("❌ **Invalid Code!** Must be 2 letters + 4 digits (e.g., DB0149).", parse_mode=ParseMode.MARKDOWN)
        return
        
    # 3. Fetch Message ID from DB
    message_id = await get_video_message_id(question_code)
    
    if not message_id:
        await message.reply_text(f"❌ **Not Found:** No video saved for code `{question_code}`.", parse_mode=ParseMode.MARKDOWN)
        return
        
    # 4. Fetch the File ID from the Dump Channel (Required for Cloudflare)
    try:
        msg = await bot.get_messages(DUMP_CHANNEL_ID, message_id)
        media = msg.video or msg.document or msg.animation or msg.video_note
        if not media:
            return await message.reply_text("❌ Media object missing in database channel.")
        file_id = media.file_id
    except Exception as e:
        return await message.reply_text(f"❌ Error fetching file from channel: {e}")

    # 📊 5. INCREMENT ANALYTICS VIEW COUNT
    await increment_view_count(question_code)
        
    # 🔗 6. GENERATE BOTH URLS
    koyeb_url = generate_koyeb_link(message_id)
    cloudflare_url = generate_cloudflare_link(file_id)
    
    # 7. Build Keyboard UI
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Link 1", url=cloudflare_url),
            InlineKeyboardButton("Link 2 ", url=koyeb_url)
        ]
    ])
    
    sent_msg = await message.reply_text(
        text=f"✅ **Found Solution For Code :** `{question_code}`",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # ⏳ 8. AUTO-DELETE BACKGROUND TIMER
    async def auto_delete_task(chat_id, msg_id):
        await asyncio.sleep(900) # Wait exactly 15 minutes
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=msg_id)
        except Exception:
            pass # Message might already be deleted by the user

    asyncio.create_task(auto_delete_task(message.chat.id, sent_msg.id))
