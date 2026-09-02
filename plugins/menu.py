from pyrogram import __version__
from bot import Bot
from config import OWNER_ID, BOT_USERNM
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram import filters
from pyrogram.enums import ParseMode

@Bot.on_callback_query(group=250)
async def hlpcallback(client: Bot, query: CallbackQuery):
    data = query.data

    # ================= HELP MAIN MENU =================
    if data == "help_cb":
        await query.message.edit_text(
            text="✨ **Here is the menu of the bot, select what you want:**",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("📚 Module Solution", callback_data="module_solution")
                    ],
                    [
                        InlineKeyboardButton("🔙 Back", callback_data="start"), # Assumes 'start' is your home callback
                        InlineKeyboardButton("❌ Close", callback_data="close")
                    ]
                ]
            )
        )

    # ================= MODULE SOLUTION =================
    elif data == "module_solution":
        await query.message.edit_text(
            text="Use `/search AB0000` to get the module solution.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🔙 Back", callback_data="help_cb"),
                        InlineKeyboardButton("❌ Close", callback_data="close")
                    ]
                ]
            )
        )

    # ================= CLOSE =================
    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
