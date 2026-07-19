import os
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from helper_func import subscribed, encode, decode, get_messages
from pyrogram import __version__
from config import OWNER_ID,BOT_USERNM
from pyrogram.enums import ParseMode


@Bot.on_message(filters.command('hessslp') & filters.private & subscribed, group=234)
async def help(bot: Bot, message: Message):
 buttons = [
        [
            InlineKeyboardButton("PYQ",   callback_data= "help_pyq"),
            InlineKeyboardButton("ELP",   callback_data= "helpooelp"),
        ],
        [
            InlineKeyboardButton("Notes",   callback_data= "help_nots"),
            InlineKeyboardButton("Teachers", callback_data= "help_six"),
        ], 
        [
            InlineKeyboardButton("Bots", url= f"https://t.me/{BOT_USERNM}?start=Z2V0LTE2MjUxMzgxODk5OTUyNjM"),   
            InlineKeyboardButton("Channels", url= f"https://t.me/{BOT_USERNM}?start=Z2V0LTE2MjMxMzU1NTUxMzM5MDE"),
        ],
        [
            InlineKeyboardButton("Back",   callback_data= "start_cb"),
            InlineKeyboardButton("Close", callback_data= "close"),
        ],
  
    ]
 await message.reply_text( text = f'''[✨](https://telegra.ph/file/aae81838e9198e85680b2.jpg) Hey there... I'm `Voltaic Bot` 
 🔮I have lots of features like  Books, Modules , Notes etc ,  and many others useful commands 
 🌀Click on the buttons below to get documentation about specific modules''',
   reply_markup = InlineKeyboardMarkup(buttons),                       
   disable_web_page_preview = False,
   parse_mode = ParseMode.MARKDOWN,                       
   )
