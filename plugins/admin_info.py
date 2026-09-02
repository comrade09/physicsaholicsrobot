import os
import re
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot

from database.videos import (
    count_total_videos,
    delete_single_video,
    delete_all_video_records,
    get_recent_codes,
    get_all_records
)

# IMPORTANT: Set your personal Telegram User ID here
ADMIN_ID = int(os.environ.get("ADMIN_ID", 1442684727)) 

ADMIN_STATES = {}

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ Delete Specific Code", callback_data="admin_del_single"),
            InlineKeyboardButton("💥 Delete All Videos", callback_data="admin_del_all_warn")
        ],
        [
            InlineKeyboardButton("📥 Export All Codes (.txt)", callback_data="admin_export_codes"),
            InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_refresh")
        ]
    ])

async def build_info_text():
    total = await count_total_videos()
    recent = await get_recent_codes(limit=5)
    recent_str = ", ".join([f"`{c}`" for c in recent]) if recent else "None"

    return (
        "📊 **Bot Database Status & Analytics**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 **Total Saved Codes:** `{total}`\n"
        f"🕒 **Recent Codes:** {recent_str}\n"
        f"⚡ **Storage Status:** Connected & Active\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select an action below:"
    )

@Bot.on_message(filters.command(["info", "stats"]) & filters.private & filters.user(ADMIN_ID),group=8872)
async def admin_info_hub(bot: Bot, message: Message):
    ADMIN_STATES.pop(message.from_user.id, None)
    text = await build_info_text()
    await message.reply_text(text=text, reply_markup=get_admin_keyboard())

@Bot.on_message(filters.command(["del", "delete"]) & filters.private & filters.user(ADMIN_ID),group=2551)
async def quick_delete_code(bot: Bot, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Format:** `/del DB0149`")
        return
    
    target_code = message.command[1].upper()
    deleted = await delete_single_video(target_code)
    
    if deleted:
        await message.reply_text(f"✅ Code `{target_code}` removed from database.")
    else:
        await message.reply_text(f"❌ Code `{target_code}` was not found in database.")

@Bot.on_callback_query(filters.user(ADMIN_ID),group=6563)
async def admin_callbacks(bot: Bot, cb: CallbackQuery):
    data = cb.data
    user_id = cb.from_user.id

    if data == "admin_refresh":
        text = await build_info_text()
        await cb.message.edit_text(text=text, reply_markup=get_admin_keyboard())
        await cb.answer("Stats updated!")

    elif data == "admin_del_single":
        ADMIN_STATES[user_id] = "awaiting_delete_code"
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="admin_refresh")]])
        await cb.message.edit_text(
            "🗑️ **Delete Specific Video**\n\n"
            "Please send the Question Code you want to delete (e.g. `DB0149`):",
            reply_markup=cancel_kb
        )

    elif data == "admin_del_all_warn":
        warn_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Yes, Wipe Everything!", callback_data="admin_del_all_confirm")],
            [InlineKeyboardButton("🔙 Cancel / Keep Data", callback_data="admin_refresh")]
        ])
        await cb.message.edit_text(
            "⚠️ **DANGER ZONE: DELETE ALL VIDEOS** ⚠️\n\n"
            "Are you sure you want to delete **ALL** codes and mappings from the database?\n"
            "This action **cannot** be undone!",
            reply_markup=warn_kb
        )

    elif data == "admin_del_all_confirm":
        count = await delete_all_video_records()
        await cb.message.edit_text(
            f"💥 **Database Wiped Clean!**\n\nDeleted a total of `{count}` records.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Info", callback_data="admin_refresh")]])
        )

    elif data == "admin_export_codes":
        await cb.answer("Generating backup export...")
        records = await get_all_records()
        
        if not records:
            await cb.answer("Database is empty!", show_alert=True)
            return

        file_name = "database_codes_backup.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(f"--- BOT CODES BACKUP (Total: {len(records)}) ---\n")
            for item in records:
                f.write(f"Code: {item['_id']} | Channel Msg ID: {item.get('message_id')}\n")

        await bot.send_document(
            chat_id=cb.message.chat.id,
            document=file_name,
            caption=f"📁 **Backup Export Complete**\nTotal Records: `{len(records)}`"
        )
        if os.path.exists(file_name):
            os.remove(file_name)

@Bot.on_message(filters.private & filters.text & filters.user(ADMIN_ID), group=8337)
async def admin_text_input(bot: Bot, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_STATES:
        return

    state = ADMIN_STATES.pop(user_id, None)

    if state == "awaiting_delete_code":
        code = message.text.strip().upper()
        if not re.match(r"^[A-Z]{2}\d{4}$", code):
            await message.reply_text(
                "❌ **Invalid Format!** Must be 2 letters followed by 4 digits (e.g. `DB0149`). Action cancelled."
            )
            return

        deleted = await delete_single_video(code)
        if deleted:
            await message.reply_text(
                f"✅ **Deleted successfully!** Code `{code}` was removed from the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Info", callback_data="admin_refresh")]])
            )
        else:
            await message.reply_text(
                f"❌ Code `{code}` was not found in the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Info", callback_data="admin_refresh")]])
            )
