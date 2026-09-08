from pyrogram import filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode
from bot import Bot

from . import db
from .keyboards import games_menu_keyboard, back_to_games_keyboard

GAME_LIST_TEXT = (
    "🎮 **Game Center**\n\n"
    "Play games in this group to earn **Aura** — winning games gives you points, "
    "losing bets takes them away. Check the group ranking with the Aura Board!\n\n"
    "Tap a game below to see how to play it."
)

HOW_TO_PLAY = {
    "coinflip": "🪙 **Coin Flip**\n`/coinflip <amount> <heads|tails>`\nGuess right, double your bet. Guess wrong, lose it.",
    "dicebattle": "🎲 **Dice Duel**\n`/dicebattle <amount>` — anyone in the group can accept. Higher dice roll wins the pot.",
    "rps": "✂️ **Rock Paper Scissors**\nReply to your opponent's message with `/rps <amount>`. Both pick a move — winner takes the pot.",
    "tictactoe": "⭕ **Tic Tac Toe**\nReply to your opponent's message with `/tictactoe`. Winner gets +15 aura, loser -5.",
    "trivia": "🧠 **Trivia**\n`/trivia` — answer in the chat. First correct answer gets +10 aura.",
    "hangman": "🔤 **Hangman**\n`/hangman` — guess a letter (or the full word) in chat. Solve it for +15 aura.",
    "wordsearch": "🔍 **Word Search**\n`/wordsearch` — I'll send a puzzle image. Anyone can reply with a hidden word to claim +6 aura per word.",
    "mathrace": "➗ **Math Race**\n`/mathrace` — first person to reply with the correct answer gets +10 aura.",
    "guessnumber": "🔢 **Guess the Number**\n`/guessnumber` — I pick 1-100, reply with guesses. I'll say higher/lower. Faster solves earn more aura.",
    "slots": "🎰 **Slot Machine**\n`/slots <amount>` — match 2 or 3 symbols to win. Jackpot pays 5x!",
    "horserace": "🐎 **Horse Race Betting**\n`/horserace <amount> <horse 1-5>` — 20 second open betting window, anyone can join. Winning horse pays 4x.",
    "emojiquiz": "😂 **Emoji Quiz**\n`/emojiquiz` — guess what the emoji combo means for +8 aura.",
    "reaction": "⚡ **Reaction**\n`/reaction` — wait for GO, then tap fastest to win +10 aura. Tap early and you're disqualified!",
    "blackjack": "🃏 **Blackjack**\n`/blackjack <amount>` — Hit or Stand vs the dealer. Beat 21, win double your bet.",
    "roulette": "🎡 **Roulette**\n`/roulette <amount> <red|black|green|0-36>` — color bets pay 2x (14x on green), exact numbers pay 35x.",
}


@Bot.on_message(filters.command("games"), group=1924)
async def games_command(bot: Bot, message: Message):
    chat_id = message.chat.id if message.chat.type != "private" else None
    await db.ensure_registered(message.from_user.id, chat_id)
    await message.reply_text(GAME_LIST_TEXT, reply_markup=games_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)


# This is the callback your bot's main menu should point to for the "🎮 Games" button.
@Bot.on_callback_query(filters.regex("^games$"), group=509)
async def games_menu_callback(bot: Bot, query: CallbackQuery):
    chat_id = query.message.chat.id if query.message.chat.type != "private" else None
    await db.ensure_registered(query.from_user.id, chat_id)
    await query.message.edit_text(GAME_LIST_TEXT, reply_markup=games_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^ginfo_(\w+)$"), group=4606)
async def game_info_callback(bot: Bot, query: CallbackQuery):
    key = query.matches[0].group(1)
    text = HOW_TO_PLAY.get(key, "No info available.")
    await query.message.edit_text(text, reply_markup=back_to_games_keyboard(), parse_mode=ParseMode.MARKDOWN)
    await query.answer()


# ---------------- /me ----------------
async def _show_me(user, message, edit: bool):
    await db.ensure_registered(user.id)
    stats = await db.get_user_stats(user.id)
    text = (
        f"👤 **{user.first_name}'s Stats**\n\n"
        f"✨ Aura: `{stats['aura']}`\n"
        f"💠 Karma: `{stats['karma']}`\n"
        f"🏆 Wins: `{stats['wins']}`\n"
        f"💀 Losses: `{stats['losses']}`\n"
        f"🎮 Games Played: `{stats['games_played']}`"
    )
    if edit:
        await message.edit_text(text, reply_markup=back_to_games_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@Bot.on_message(filters.command("me"), group=4112)
async def me_command(bot: Bot, message: Message):
    await _show_me(message.from_user, message, edit=False)


@Bot.on_callback_query(filters.regex("^game_me$"), group=3757)
async def me_callback(bot: Bot, query: CallbackQuery):
    await _show_me(query.from_user, query.message, edit=True)
    await query.answer()


# ---------------- /auraboard (per-group leaderboard) ----------------
async def _show_auraboard(chat_id: int, message: Message, edit: bool):
    top = await db.get_group_leaderboard(chat_id, limit=10)
    if not top:
        text = "No aura recorded in this group yet — play some games!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 **Top Aura — This Group**\n"]
        for i, doc in enumerate(top):
            tag = medals[i] if i < 3 else f"{i+1}."
            try:
                u = await message._client.get_users(doc["_id"])
                name = u.first_name
            except Exception:
                name = f"User {doc['_id']}"
            lines.append(f"{tag} {name} — `{doc.get('aura', 0)}` aura")
        text = "\n".join(lines)

    if edit:
        await message.edit_text(text, reply_markup=back_to_games_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@Bot.on_message(filters.command("auraboard"), group=2386)
async def auraboard_command(bot: Bot, message: Message):
    if message.chat.type == "private":
        await message.reply_text("⚠️ The Aura Board only works inside a group.")
        return
    await _show_auraboard(message.chat.id, message, edit=False)


@Bot.on_callback_query(filters.regex("^game_auraboard$"), group=1779)
async def auraboard_callback(bot: Bot, query: CallbackQuery):
    if query.message.chat.type == "private":
        await query.answer("This only works in groups.", show_alert=True)
        return
    await _show_auraboard(query.message.chat.id, query.message, edit=True)
    await query.answer()


# ---------------- /karma ----------------
@Bot.on_message(filters.command("karma"), group=9035)
async def karma_command(bot: Bot, message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("↩️ Reply to someone's message with `/karma` to give them karma.", parse_mode=ParseMode.MARKDOWN)
        return

    giver = message.from_user
    receiver = message.reply_to_message.from_user
    if giver.id == receiver.id:
        await message.reply_text("😅 You can't give karma to yourself.")
        return

    await db.ensure_registered(giver.id)
    await db.ensure_registered(receiver.id)

    if not await db.can_give_karma(giver.id, receiver.id):
        await message.reply_text("⏳ You already gave this person karma today. Try again tomorrow!")
        return

    await db.add_karma(receiver.id, 1)
    await db.mark_karma_given(giver.id, receiver.id)
    total = await db.get_karma(receiver.id)
    await message.reply_text(
        f"💠 {giver.first_name} gave karma to {receiver.first_name}! Now at `{total}` karma.",
        parse_mode=ParseMode.MARKDOWN
    )
