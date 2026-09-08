import random
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from bot import Bot

from . import db
from .state import start_game, get_game, is_busy
from .wordsearch import generate_grid, render_grid_image

TRIVIA_QUESTIONS = [
    {"q": "What does HTML stand for?", "a": "hypertext markup language"},
    {"q": "Which planet is known as the Red Planet?", "a": "mars"},
    {"q": "What is the capital of Japan?", "a": "tokyo"},
    {"q": "How many continents are there on Earth?", "a": "7"},
    {"q": "What is the chemical symbol for Gold?", "a": "au"},
    {"q": "Who developed the theory of relativity?", "a": "einstein"},
    {"q": "What is the largest mammal on Earth?", "a": "blue whale"},
    {"q": "In which language is 'Namaste' a common greeting?", "a": "hindi"},
    {"q": "What does CPU stand for?", "a": "central processing unit"},
    {"q": "Which country gifted the Statue of Liberty to the USA?", "a": "france"},
]

HANGMAN_WORDS = [
    "python", "telegram", "developer", "keyboard", "internet",
    "function", "variable", "monitor", "gaming", "cursor",
]

EMOJI_RIDDLES = [
    {"emoji": "🍎📱", "a": "iphone"},
    {"emoji": "🕷️🕸️", "a": "spiderman"},
    {"emoji": "🦁👑", "a": "lion king"},
    {"emoji": "❄️👸", "a": "frozen"},
    {"emoji": "🚗💨", "a": "fast and furious"},
    {"emoji": "🐝🎬", "a": "bee movie"},
    {"emoji": "🌊🐠", "a": "finding nemo"},
]


def _group_chat_id(message: Message):
    return message.chat.id if message.chat.type != "private" else None


# ================= COIN FLIP (instant) =================
@Bot.on_message(filters.command("coinflip"), group=1524)
async def coinflip_cmd(bot: Bot, message: Message):
    args = message.command[1:]
    if len(args) < 2 or not args[0].isdigit() or args[1].lower() not in ("heads", "tails"):
        await message.reply_text(
            "🪙 Usage: `/coinflip <amount> <heads|tails>`", parse_mode=ParseMode.MARKDOWN
        )
        return

    amount = int(args[0])
    choice = args[1].lower()
    user = message.from_user
    await db.ensure_registered(user.id, _group_chat_id(message))
    aura = await db.get_aura(user.id)

    if amount <= 0:
        await message.reply_text("⚠️ Bet must be a positive amount.")
        return
    if amount > aura:
        await message.reply_text(f"⚠️ You only have `{aura}` aura.", parse_mode=ParseMode.MARKDOWN)
        return

    result = random.choice(["heads", "tails"])
    won = result == choice
    await db.add_aura(user.id, amount if won else -amount)
    await db.record_result(user.id, won)

    outcome = "🎉 **You won!**" if won else "💀 **You lost.**"
    await message.reply_text(
        f"🪙 The coin landed on **{result}**.\n{outcome} {'+' if won else '-'}`{amount}` aura.",
        parse_mode=ParseMode.MARKDOWN
    )


# ================= SLOT MACHINE (instant) =================
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "💎", "7️⃣"]

@Bot.on_message(filters.command("slots"), group=9774)
async def slots_cmd(bot: Bot, message: Message):
    args = message.command[1:]
    if len(args) < 1 or not args[0].isdigit():
        await message.reply_text("🎰 Usage: `/slots <amount>`", parse_mode=ParseMode.MARKDOWN)
        return

    amount = int(args[0])
    user = message.from_user
    await db.ensure_registered(user.id, _group_chat_id(message))
    aura = await db.get_aura(user.id)

    if amount <= 0 or amount > aura:
        await message.reply_text(f"⚠️ You only have `{aura}` aura.", parse_mode=ParseMode.MARKDOWN)
        return

    spin = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    reel = " | ".join(spin)

    if spin[0] == spin[1] == spin[2]:
        payout = amount * 5
        await db.add_aura(user.id, payout)
        await db.record_result(user.id, True)
        text = f"🎰 [ {reel} ]\n🎉 **JACKPOT!** +`{payout}` aura!"
    elif len(set(spin)) == 2:
        payout = amount
        await db.add_aura(user.id, payout)
        await db.record_result(user.id, True)
        text = f"🎰 [ {reel} ]\n✨ Two match! +`{payout}` aura."
    else:
        await db.add_aura(user.id, -amount)
        await db.record_result(user.id, False)
        text = f"🎰 [ {reel} ]\n💀 No match. -`{amount}` aura."

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ================= TRIVIA (text answer, resolved in listener.py) =================
@Bot.on_message(filters.command("trivia"), group=7012)
async def trivia_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running in this chat. Finish it first!")
        return
    q = random.choice(TRIVIA_QUESTIONS)
    start_game(chat_id, "trivia", {"answer": q["a"]})
    await message.reply_text(
        f"🧠 **Trivia Time!**\n\n{q['q']}\n\n_Reply in the chat with your answer._",
        parse_mode=ParseMode.MARKDOWN
    )


# ================= HANGMAN (letter-by-letter, resolved in listener.py) =================
@Bot.on_message(filters.command("hangman"), group=620)
async def hangman_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running in this chat. Finish it first!")
        return
    word = random.choice(HANGMAN_WORDS)
    start_game(chat_id, "hangman", {"word": word, "guessed": set(), "lives": 6})
    display = " ".join("_" for _ in word)
    await message.reply_text(
        f"🔤 **Hangman started!**\nWord: `{display}`\nLives: 6 ❤️\n\n"
        "_Reply with a single letter to guess, or the full word._",
        parse_mode=ParseMode.MARKDOWN
    )


# ================= EMOJI QUIZ (text answer, resolved in listener.py) =================
@Bot.on_message(filters.command("emojiquiz"), group=588)
async def emojiquiz_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running in this chat. Finish it first!")
        return
    riddle = random.choice(EMOJI_RIDDLES)
    start_game(chat_id, "emojiquiz", {"answer": riddle["a"]})
    await message.reply_text(
        f"😂 **Emoji Quiz!**\n\n{riddle['emoji']}\n\n_Guess what it means!_",
        parse_mode=ParseMode.MARKDOWN
    )


# ================= GUESS THE NUMBER (text guesses, resolved in listener.py) =================
@Bot.on_message(filters.command("guessnumber"), group=1635)
async def guessnumber_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running in this chat. Finish it first!")
        return
    number = random.randint(1, 100)
    start_game(chat_id, "guessnumber", {"number": number, "tries": 0})
    await message.reply_text(
        "🔢 **Guess the Number!**\nI'm thinking of a number between `1` and `100`.\n"
        "_Reply with your guess — I'll tell you higher or lower!_",
        parse_mode=ParseMode.MARKDOWN
    )


# ================= WORD SEARCH (image + text answers, resolved in listener.py) =================
@Bot.on_message(filters.command("wordsearch"), group=3682)
async def wordsearch_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running in this chat. Finish it first!")
        return
    grid, placed = generate_grid(size=10, word_count=5)
    start_game(chat_id, "wordsearch", {"words": set(w.lower() for w in placed), "found": set()})
    img = render_grid_image(grid)
    await message.reply_photo(
        img,
        caption=(
            f"🔍 **Word Search!** Find these `{len(placed)}` hidden words:\n"
            f"`{', '.join(placed)}`\n\n"
            "_Anyone in the group can reply with a word they spot. First correct guess claims it!_"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
