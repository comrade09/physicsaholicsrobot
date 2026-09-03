from bot import Bot
from pyrogram.types import Message
import asyncio
from pyrogram import filters
from config import ADMINS, BOT_STATS_TEXT
from datetime import datetime
from helper_func import get_readable_time
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON
import datetime
import pytz
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode


ERROR_TEXT = "⚠️ Invalid Command press /start "

@Bot.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    now = datetime.now()
    delta = now - bot.uptime
    time = get_readable_time(delta.seconds)
    await message.reply_text(f"{time}")



@Bot.on_message(filters.private & filters.incoming & ~filters.command(['start','lecture', 'solution', 'help', 'notes', 'ask', 'binging', 'chat', 'search', 'info', 'stats', 'del', 'delete']))
async def useless(_,message: Message):
    user = message.from_user
    asia_kolkata = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(asia_kolkata)
   
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')
    info_text = f"🌀User info:\n👤 Name:{user.first_name}{user.last_name}\n✨Username: @{user.username}\nUser ID: [{user.id}](tg://user?id={user.id})\n\n♻️Message sent: `{message.text}`\n\n🗓Time (Asia/Kolkata): {formatted_time}"

    if ERROR_TEXT:
         await _.send_message(chat_id= -1001719848813, text=info_text, parse_mode=ParseMode.MARKDOWN,disable_notification=True)
         await message.reply(ERROR_TEXT)
@Bot.on_callback_query(group=47287427)
async def callback_handler(_, query: CallbackQuery):
    user = query.from_user
    asia_kolkata = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(asia_kolkata)
   
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')
    info_text = f"🌀User info:\n👤 Name:{user.first_name}{user.last_name}\n✨Username: @{user.username}\nUser ID: [{user.id}](tg://user?id={user.id})\n\n♻️Message sent: `{query.data}`\n\n🗓Time (Asia/Kolkata): {formatted_time}"

    if ERROR_TEXT:
        await _.send_message(chat_id=-1002554844860, text=info_text, disable_notification=True,parse_mode=ParseMode.MARKDOWN)

@Bot.on_message(filters.private & (filters.photo | filters.video | filters.document),group=65675)
async def forward_to_log_channel(client, message):
    # Forward the message to the log channel
    await message.forward(chat_id=-1002554844860)
