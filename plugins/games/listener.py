"""
games/listener.py
--------------------
ONE central text handler for every game that needs free-text answers
(trivia, hangman, emoji quiz, guess-the-number, word search, math race).

Centralizing this avoids Pyrogram handler-group collisions you'd get from
registering several `filters.text & filters.group` handlers in different
files with the same group id.
"""
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from bot import Bot

from . import db
from .state import get_game, end_game, update_game_data


@Bot.on_message(filters.text & filters.group & ~filters.via_bot, group=9500)
async def game_text_listener(bot: Bot, message: Message):
    game = get_game(message.chat.id)
    if not game:
        return

    gtype = game["type"]
    text = (message.text or "").strip().lower()
    user = message.from_user
    if not user:
        return

    handler = _HANDLERS.get(gtype)
    if handler:
        await handler(message, game["data"], user, text)


# ---------------- individual resolvers ----------------

async def _trivia(message: Message, data: dict, user, text: str):
    if text == data["answer"]:
        end_game(message.chat.id)
        await db.ensure_registered(user.id, message.chat.id)
        await db.add_aura(user.id, 10)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"✅ Correct, {user.first_name}! +`10` aura.", parse_mode=ParseMode.MARKDOWN
        )


async def _emojiquiz(message: Message, data: dict, user, text: str):
    if text == data["answer"]:
        end_game(message.chat.id)
        await db.ensure_registered(user.id, message.chat.id)
        await db.add_aura(user.id, 8)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"✅ Nailed it, {user.first_name}! +`8` aura.", parse_mode=ParseMode.MARKDOWN
        )


async def _guessnumber(message: Message, data: dict, user, text: str):
    if not text.lstrip("-").isdigit():
        return
    guess = int(text)
    number = data["number"]
    data["tries"] += 1

    if guess == number:
        end_game(message.chat.id)
        await db.ensure_registered(user.id, message.chat.id)
        reward = max(20 - data["tries"], 5)
        await db.add_aura(user.id, reward)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"🎯 Correct, {user.first_name}! It was `{number}`. +`{reward}` aura "
            f"(solved in {data['tries']} tries).",
            parse_mode=ParseMode.MARKDOWN
        )
    elif guess < number:
        await message.reply_text("📈 Higher!")
    else:
        await message.reply_text("📉 Lower!")


async def _hangman(message: Message, data: dict, user, text: str):
    word = data["word"]

    if text == word:
        end_game(message.chat.id)
        await db.ensure_registered(user.id, message.chat.id)
        await db.add_aura(user.id, 15)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"🎉 {user.first_name} solved it — the word was **{word}**! +`15` aura.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(text) != 1 or not text.isalpha():
        return

    if text in data["guessed"]:
        return
    data["guessed"].add(text)

    if text in word:
        display = " ".join(c if c in data["guessed"] else "_" for c in word)
        if "_" not in display:
            end_game(message.chat.id)
            await db.ensure_registered(user.id, message.chat.id)
            await db.add_aura(user.id, 15)
            await db.record_result(user.id, True)
            await message.reply_text(
                f"🎉 Word complete — **{word}**! +`15` aura to {user.first_name}.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(f"✅ `{text}` is in the word!\n`{display}`", parse_mode=ParseMode.MARKDOWN)
    else:
        data["lives"] -= 1
        if data["lives"] <= 0:
            end_game(message.chat.id)
            await message.reply_text(
                f"💀 Out of lives! The word was **{word}**.", parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(f"❌ No `{text}`. Lives left: {data['lives']} ❤️")


async def _wordsearch(message: Message, data: dict, user, text: str):
    words = data["words"]
    found = data["found"]
    if text in words and text not in found:
        found.add(text)
        await db.ensure_registered(user.id, message.chat.id)
        await db.add_aura(user.id, 6)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"🔍 {user.first_name} found **{text.upper()}**! +`6` aura. "
            f"({len(found)}/{len(words)} found)",
            parse_mode=ParseMode.MARKDOWN
        )
        if found == words:
            end_game(message.chat.id)
            await message.reply_text("🏁 All words found! Puzzle complete.")


async def _mathrace(message: Message, data: dict, user, text: str):
    if not text.lstrip("-").isdigit():
        return
    if int(text) == data["answer"]:
        end_game(message.chat.id)
        await db.ensure_registered(user.id, message.chat.id)
        await db.add_aura(user.id, 10)
        await db.record_result(user.id, True)
        await message.reply_text(
            f"🏁 {user.first_name} got it first! `{data['expr']} = {data['answer']}`. +`10` aura.",
            parse_mode=ParseMode.MARKDOWN
        )


_HANDLERS = {
    "trivia": _trivia,
    "emojiquiz": _emojiquiz,
    "guessnumber": _guessnumber,
    "hangman": _hangman,
    "wordsearch": _wordsearch,
    "mathrace": _mathrace,
}
