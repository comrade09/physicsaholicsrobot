"""(©) Codexbotz — modernized for Python 3.12+ with Button Colors & Blockquotes"""
from __future__ import annotations

import asyncio
import uuid

import humanize
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    ReplyParameters,
)

from bot import Bot
from config import (
    ADMINS,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    FORCE_MSG,
    PROTECT_CONTENT,
)
from database.database import add_user, del_user, full_userbase, present_user
from formatting import bold, join_lines
from helper_func import decode, encode, get_messages, subscribed

FILE_AUTO_DELETE_SECONDS = 600
FILE_AUTO_DELETE_HUMAN = humanize.naturaldelta(FILE_AUTO_DELETE_SECONDS)

# Welcome text updated with Telegram's modern blockquote feature
WELCOME_TEXT = '<blockquote><b>Hey! {first}</b>\nI am Physicsaholics Bot <a href="https://i.ibb.co/vCJrx4PN/x.jpg">.</a></blockquote>'
WAIT_MSG = "<b>Processing ...</b>"
REPLY_ERROR = "<code>Use this command as a reply to any telegram message without any spaces.</code>"

# --- Broadcast State Management ---
broadcast_sessions: dict[str, 'BroadcastSession'] = {}

class BroadcastSession:
    def __init__(self, mode: str):
        self.id = str(uuid.uuid4())[:8]  
        self.is_running = True
        self.mode = mode 
        self.sent_messages: list[tuple[int, int]] = []  
        self.stats = {"total": 0, "successful": 0, "blocked": 0, "deleted": 0, "unsuccessful": 0}


def _greeting_kwargs(message: Message) -> dict:
    user = message.from_user
    return {
        "first": user.first_name,
        "last": user.last_name,
        "username": None if not user.username else f"@{user.username}",
        "mention": user.mention,
        "id": user.id,
    }


def _resolve_requested_ids(argument: list[str], db_channel_id: int) -> list[int] | None:
    """Turn a decoded `get-<id>[-<id>]` payload into the real DB-channel message ids."""
    match len(argument):
        case 3:
            try:
                start = int(int(argument[1]) / abs(db_channel_id))
                end = int(int(argument[2]) / abs(db_channel_id))
            except (ValueError, ZeroDivisionError):
                return None
            if start <= end:
                return list(range(start, end + 1))
            return list(range(start, end - 1, -1))
        case 2:
            try:
                return [int(int(argument[1]) / abs(db_channel_id))]
            except (ValueError, ZeroDivisionError):
                return None
            
        case _:
            return None


@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception:
            pass

    text = message.text
    if len(text) <= 7:
        await _send_welcome(message)
        return

    try:
        base64_string = text.split(" ", 1)[1]
    except IndexError:
        return

    string = await decode(base64_string)
    argument = string.split("-")
    ids = _resolve_requested_ids(argument, client.db_channel.id)
    if ids is None:
        return

    await _deliver_files(client, message, ids)


async def _send_welcome(message: Message) -> None:
    reply_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="Menu", callback_data="help_cb", style=ButtonStyle.PRIMARY)],
            [
                InlineKeyboardButton(text="Support ✨", url="https://t.me/voltaic_network", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(text="Updates 📡", url="https://t.me/voltaic_network", style=ButtonStyle.SUCCESS),
            ],
        ]
    )
    await message.reply_text(
        text=WELCOME_TEXT.format(**_greeting_kwargs(message)),
        reply_markup=reply_markup,
        link_preview_options=LinkPreviewOptions(is_disabled=False),
        reply_parameters=ReplyParameters(message_id=message.id),
        parse_mode=ParseMode.HTML, 
    )


async def _deliver_files(client: Client, message: Message, ids: list[int]) -> None:
    temp_msg = await message.reply("Please Wait...", reply_parameters=ReplyParameters(message_id=message.id))
    try:
        messages = await get_messages(client, ids)
    except Exception:
        await message.reply_text("Something Went Wrong..!", reply_parameters=ReplyParameters(message_id=message.id))
        return
    await temp_msg.delete()

    sent_messages: list[Message] = []
    for msg in messages:
        if CUSTOM_CAPTION and msg.document:
            caption = CUSTOM_CAPTION.format(
                previouscaption="" if not msg.caption else msg.caption.html,
                filename=msg.document.file_name,
            )
        else:
            caption = "" if not msg.caption else msg.caption.html

        reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

        try:
            sent = await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT,
            )
            sent_messages.append(sent)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            sent = await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT,
            )
            sent_messages.append(sent)
        except Exception:
            pass

    status = await client.send_message(
        chat_id=message.from_user.id,
        text=join_lines(
            f" {bold('DONE ✅')}",
            f"These files will auto-delete in {FILE_AUTO_DELETE_HUMAN} to save space.",
        ),
    )

    asyncio.create_task(delete_files(sent_messages, status))


async def delete_files(messages: list[Message], status_message: Message) -> None:
    await asyncio.sleep(FILE_AUTO_DELETE_SECONDS)
    for msg in messages:
        try:
            await msg.delete()
        except Exception:
            pass
    try:
        await status_message.edit(
            f"<b>Your files have been auto-deleted</b> after {FILE_AUTO_DELETE_HUMAN}. "
            "Use the link again to resend them."
        )
    except Exception:
        pass


@Bot.on_message(filters.command("start") & filters.private)
async def not_joined(client: Client, message: Message) -> None:
    buttons = [[InlineKeyboardButton("Join Channel", url=client.invitelink, style=ButtonStyle.DANGER)]]
    try:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Try Again",
                    url=f"https://t.me/{client.username}?start={message.command[1]}",
                    style=ButtonStyle.PRIMARY,
                )
            ]
        )
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(**_greeting_kwargs(message)),
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_parameters=ReplyParameters(message_id=message.id),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message) -> None:
    msg = await client.send_message(
        chat_id=message.chat.id,
        text=WAIT_MSG,
        reply_parameters=ReplyParameters(message_id=message.id),
    )
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot ")


@Bot.on_message(filters.private & filters.command("broadcast") & filters.user(ADMINS))
async def send_text(client: Bot, message: Message) -> None:
    if not message.reply_to_message:
        msg = await message.reply(
            "<blockquote><b>⚠️ Broadcast Command Usage:</b>\n\n"
            "Reply to the message you want to broadcast.\n\n"
            "<b>Options:</b>\n"
            "<code>/broadcast</code> - Sends a copy\n"
            "<code>/broadcast forward</code> - Forwards the message</blockquote>",
            reply_parameters=ReplyParameters(message_id=message.id),
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(8)
        await msg.delete()
        return

    mode = "forward" if len(message.command) > 1 and message.command[1].lower() == "forward" else "copy"
    
    session = BroadcastSession(mode)
    broadcast_sessions[session.id] = session
    query = await full_userbase()
    broadcast_msg = message.reply_to_message

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛑 Stop Broadcast", callback_data=f"bcast_stop_{session.id}", style=ButtonStyle.DANGER)]]
    )
    
    pls_wait = await message.reply(
        f"<blockquote><b>🔄 Broadcasting Message ({mode} mode)...</b>\n"
        f"<i>Please wait, this will take some time.</i></blockquote>", 
        reply_parameters=ReplyParameters(message_id=message.id),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    for chat_id in query:
        if not session.is_running:
            break 

        session.stats["total"] += 1
        try:
            if mode == "forward":
                sent_msg = await broadcast_msg.forward(chat_id)
            else:
                sent_msg = await broadcast_msg.copy(chat_id)
            
            session.sent_messages.append((chat_id, sent_msg.id))
            session.stats["successful"] += 1
            
        except FloodWait as e:
            sleep_time = getattr(e, 'value', getattr(e, 'x', 5)) 
            await asyncio.sleep(sleep_time)
            
            if mode == "forward":
                sent_msg = await broadcast_msg.forward(chat_id)
            else:
                sent_msg = await broadcast_msg.copy(chat_id)
                
            session.sent_messages.append((chat_id, sent_msg.id))
            session.stats["successful"] += 1
        except UserIsBlocked:
            await del_user(chat_id)
            session.stats["blocked"] += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            session.stats["deleted"] += 1
        except Exception:
            session.stats["unsuccessful"] += 1

    status_text = (
        f"<blockquote><b><u>Broadcast {'Completed ✅' if session.is_running else 'Stopped 🛑'}</u></b>\n\n"
        f"<b>Total Users Checked:</b> <code>{session.stats['total']}</code>\n"
        f"<b>Successful:</b> <code>{session.stats['successful']}</code>\n"
        f"<b>Blocked Users:</b> <code>{session.stats['blocked']}</code>\n"
        f"<b>Deleted Accounts:</b> <code>{session.stats['deleted']}</code>\n"
        f"<b>Unsuccessful:</b> <code>{session.stats['unsuccessful']}</code></blockquote>"
    )

    final_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🗑 Revoke/Delete Broadcast", callback_data=f"bcast_revoke_{session.id}", style=ButtonStyle.DANGER)]]
    )

    await pls_wait.edit(text=status_text, reply_markup=final_markup, parse_mode=ParseMode.HTML)


@Bot.on_callback_query(filters.regex(r"^bcast_(stop|revoke)_(.+)$") & filters.user(ADMINS))
async def broadcast_callbacks(client: Client, query: CallbackQuery) -> None:
    action = query.matches[0].group(1)
    session_id = query.matches[0].group(2)

    session = broadcast_sessions.get(session_id)
    if not session:
        await query.answer("This broadcast session has expired.", show_alert=True)
        return

    if action == "stop":
        if not session.is_running:
            await query.answer("Broadcast is already stopped!", show_alert=True)
            return
        
        session.is_running = False
        await query.answer("Stopping broadcast...", show_alert=True)
        
    elif action == "revoke":
        await query.answer("Revoking messages... This might take a moment.", show_alert=True)
        
        await query.message.edit_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Revoking...", callback_data="none", style=ButtonStyle.PRIMARY)]])
        )

        deleted_count = 0
        for chat_id, msg_id in session.sent_messages:
            try:
                await client.delete_messages(chat_id, msg_id)
                deleted_count += 1
                await asyncio.sleep(0.05) 
            except Exception:
                pass
        
        text = query.message.html
        text += f"\n\n<blockquote><b>🗑 Revocation Complete:</b>\n<code>{deleted_count}</code> messages successfully deleted.</blockquote>"
        
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=None)
