from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def games_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Coin Flip", callback_data="ginfo_coinflip"),
         InlineKeyboardButton("🎲 Dice Duel", callback_data="ginfo_dicebattle")],
        [InlineKeyboardButton("✂️ RPS", callback_data="ginfo_rps"),
         InlineKeyboardButton("⭕ Tic Tac Toe", callback_data="ginfo_tictactoe")],
        [InlineKeyboardButton("🧠 Trivia", callback_data="ginfo_trivia"),
         InlineKeyboardButton("🔤 Hangman", callback_data="ginfo_hangman")],
        [InlineKeyboardButton("🔍 Word Search", callback_data="ginfo_wordsearch"),
         InlineKeyboardButton("➗ Math Race", callback_data="ginfo_mathrace")],
        [InlineKeyboardButton("🔢 Guess Number", callback_data="ginfo_guessnumber"),
         InlineKeyboardButton("🎰 Slots", callback_data="ginfo_slots")],
        [InlineKeyboardButton("🐎 Horse Race", callback_data="ginfo_horserace"),
         InlineKeyboardButton("😂 Emoji Quiz", callback_data="ginfo_emojiquiz")],
        [InlineKeyboardButton("⚡ Reaction", callback_data="ginfo_reaction"),
         InlineKeyboardButton("🃏 Blackjack", callback_data="ginfo_blackjack")],
        [InlineKeyboardButton("🎡 Roulette", callback_data="ginfo_roulette")],
        [InlineKeyboardButton("📊 Aura Board", callback_data="game_auraboard"),
         InlineKeyboardButton("👤 My Stats", callback_data="game_me")],
    ])


def back_to_games_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Games", callback_data="games")]])


def rps_keyboard(game_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨 Rock", callback_data=f"rps_{game_key}_rock"),
        InlineKeyboardButton("📄 Paper", callback_data=f"rps_{game_key}_paper"),
        InlineKeyboardButton("✂️ Scissors", callback_data=f"rps_{game_key}_scissors"),
    ]])


def dice_join_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Accept Duel", callback_data=f"dice_join_{chat_id}")]])


def ttt_keyboard(board: list, chat_id: int) -> InlineKeyboardMarkup:
    symbols = {0: "⬜", 1: "❌", 2: "⭕"}
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            label = symbols[board[i]]
            row.append(InlineKeyboardButton(label, callback_data=f"ttt_{chat_id}_{i}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def reaction_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⚡ TAP!", callback_data=f"react_{chat_id}")]])


def blackjack_keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🂠 Hit", callback_data=f"bj_hit_{key}"),
        InlineKeyboardButton("✋ Stand", callback_data=f"bj_stand_{key}"),
    ]])
