import random
import asyncio
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode
from bot import Bot

from . import db
from .state import start_game, get_game, end_game, is_busy, active_games
from .keyboards import rps_keyboard, dice_join_keyboard, ttt_keyboard, reaction_keyboard, blackjack_keyboard


def _group_chat_id(message: Message):
    return message.chat.id if message.chat.type != "private" else None


# ========================================================
# DICE DUEL — 2 players, bet aura, high roll wins
# ========================================================
@Bot.on_message(filters.command("dicebattle") & filters.group, group=3911)
async def dicebattle_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return
    args = message.command[1:]
    if not args or not args[0].isdigit():
        await message.reply_text("🎲 Usage: `/dicebattle <amount>` (reply-free, anyone can accept)", parse_mode=ParseMode.MARKDOWN)
        return

    amount = int(args[0])
    user = message.from_user
    await db.ensure_registered(user.id, chat_id)
    if amount <= 0 or amount > await db.get_aura(user.id):
        await message.reply_text("⚠️ You don't have enough aura for that bet.")
        return

    start_game(chat_id, "dicebattle", {"challenger": user.id, "challenger_name": user.first_name, "amount": amount})
    await message.reply_text(
        f"🎲 **{user.first_name}** challenges the group to a Dice Duel for `{amount}` aura!\n"
        "Tap below to accept.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=dice_join_keyboard(chat_id)
    )


@Bot.on_callback_query(filters.regex(r"^dice_join_(-?\d+)$"), group=8379)
async def dicebattle_join(bot: Bot, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    game = get_game(chat_id)
    if not game or game["type"] != "dicebattle":
        await query.answer("This duel is no longer active.", show_alert=True)
        return

    data = game["data"]
    opponent = query.from_user
    if opponent.id == data["challenger"]:
        await query.answer("You can't duel yourself!", show_alert=True)
        return

    await db.ensure_registered(opponent.id, chat_id)
    amount = data["amount"]
    if amount > await db.get_aura(opponent.id):
        await query.answer("You don't have enough aura!", show_alert=True)
        return

    end_game(chat_id)
    roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
    challenger_id, challenger_name = data["challenger"], data["challenger_name"]

    if roll1 == roll2:
        text = f"🎲 {challenger_name} rolled `{roll1}`, {opponent.first_name} rolled `{roll2}`.\n🤝 It's a tie! No aura lost."
    elif roll1 > roll2:
        await db.add_aura(challenger_id, amount)
        await db.add_aura(opponent.id, -amount)
        await db.record_result(challenger_id, True)
        await db.record_result(opponent.id, False)
        text = f"🎲 {challenger_name} rolled `{roll1}`, {opponent.first_name} rolled `{roll2}`.\n🏆 {challenger_name} wins `{amount}` aura!"
    else:
        await db.add_aura(opponent.id, amount)
        await db.add_aura(challenger_id, -amount)
        await db.record_result(opponent.id, True)
        await db.record_result(challenger_id, False)
        text = f"🎲 {challenger_name} rolled `{roll1}`, {opponent.first_name} rolled `{roll2}`.\n🏆 {opponent.first_name} wins `{amount}` aura!"

    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    await query.answer()


# ========================================================
# ROCK PAPER SCISSORS — 2 players, must reply to opponent
# ========================================================
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

@Bot.on_message(filters.command("rps") & filters.group, group=9963)
async def rps_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("✂️ Reply to your opponent's message with `/rps <amount>`.", parse_mode=ParseMode.MARKDOWN)
        return

    args = message.command[1:]
    if not args or not args[0].isdigit():
        await message.reply_text("✂️ Usage: `/rps <amount>` (as a reply to your opponent)", parse_mode=ParseMode.MARKDOWN)
        return

    amount = int(args[0])
    p1 = message.from_user
    p2 = message.reply_to_message.from_user
    if p1.id == p2.id:
        await message.reply_text("😅 You can't play against yourself.")
        return

    await db.ensure_registered(p1.id, chat_id)
    await db.ensure_registered(p2.id, chat_id)
    if amount > await db.get_aura(p1.id) or amount > await db.get_aura(p2.id):
        await message.reply_text("⚠️ Both players need enough aura for this bet.")
        return

    start_game(chat_id, "rps", {
        "p1": p1.id, "p1_name": p1.first_name,
        "p2": p2.id, "p2_name": p2.first_name,
        "amount": amount, "choices": {}
    })
    await message.reply_text(
        f"✂️ **RPS: {p1.first_name} vs {p2.first_name}** for `{amount}` aura!\nBoth players pick below 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=rps_keyboard(str(chat_id))
    )


@Bot.on_callback_query(filters.regex(r"^rps_(-?\d+)_(rock|paper|scissors)$"), group=534)
async def rps_choice(bot: Bot, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    choice = query.matches[0].group(2)
    game = get_game(chat_id)
    if not game or game["type"] != "rps":
        await query.answer("This match is no longer active.", show_alert=True)
        return

    data = game["data"]
    uid = query.from_user.id
    if uid not in (data["p1"], data["p2"]):
        await query.answer("You're not in this match!", show_alert=True)
        return
    if uid in data["choices"]:
        await query.answer("You already chose!", show_alert=True)
        return

    data["choices"][uid] = choice
    await query.answer(f"You picked {choice}!")

    if len(data["choices"]) < 2:
        return

    end_game(chat_id)
    c1, c2 = data["choices"][data["p1"]], data["choices"][data["p2"]]
    amount = data["amount"]

    if c1 == c2:
        result = "🤝 It's a tie! No aura lost."
    elif BEATS[c1] == c2:
        await db.add_aura(data["p1"], amount)
        await db.add_aura(data["p2"], -amount)
        await db.record_result(data["p1"], True)
        await db.record_result(data["p2"], False)
        result = f"🏆 {data['p1_name']} wins `{amount}` aura!"
    else:
        await db.add_aura(data["p2"], amount)
        await db.add_aura(data["p1"], -amount)
        await db.record_result(data["p2"], True)
        await db.record_result(data["p1"], False)
        result = f"🏆 {data['p2_name']} wins `{amount}` aura!"

    await query.message.edit_text(
        f"✂️ {data['p1_name']} chose **{c1}**, {data['p2_name']} chose **{c2}**.\n{result}",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================================================
# TIC TAC TOE — 2 players, reply to challenge
# ========================================================
def _check_winner(board):
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a, b, c in lines:
        if board[a] != 0 and board[a] == board[b] == board[c]:
            return board[a]
    if 0 not in board:
        return 0  # draw
    return None


@Bot.on_message(filters.command("tictactoe") & filters.group, group=9295)
async def ttt_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("⭕ Reply to your opponent's message with `/tictactoe` to challenge them.", parse_mode=ParseMode.MARKDOWN)
        return

    p1 = message.from_user
    p2 = message.reply_to_message.from_user
    if p1.id == p2.id:
        await message.reply_text("😅 You can't play against yourself.")
        return

    await db.ensure_registered(p1.id, chat_id)
    await db.ensure_registered(p2.id, chat_id)

    start_game(chat_id, "tictactoe", {
        "board": [0] * 9,
        "players": {p1.id: 1, p2.id: 2},
        "names": {p1.id: p1.first_name, p2.id: p2.first_name},
        "turn": p1.id,
    })
    await message.reply_text(
        f"⭕ **Tic Tac Toe**: {p1.first_name} (❌) vs {p2.first_name} (⭕)\n"
        f"{p1.first_name}'s turn!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ttt_keyboard([0]*9, chat_id)
    )


@Bot.on_callback_query(filters.regex(r"^ttt_(-?\d+)_(\d)$"), group=3357)
async def ttt_move(bot: Bot, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    cell = int(query.matches[0].group(2))
    game = get_game(chat_id)
    if not game or game["type"] != "tictactoe":
        await query.answer("This match is no longer active.", show_alert=True)
        return

    data = game["data"]
    uid = query.from_user.id
    if uid not in data["players"]:
        await query.answer("You're not in this match!", show_alert=True)
        return
    if uid != data["turn"]:
        await query.answer("It's not your turn!", show_alert=True)
        return
    if data["board"][cell] != 0:
        await query.answer("That cell is taken!", show_alert=True)
        return

    data["board"][cell] = data["players"][uid]
    winner = _check_winner(data["board"])

    if winner is None:
        other_id = [p for p in data["players"] if p != uid][0]
        data["turn"] = other_id
        await query.message.edit_text(
            f"⭕ **Tic Tac Toe**\n{data['names'][other_id]}'s turn!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ttt_keyboard(data["board"], chat_id)
        )
    else:
        end_game(chat_id)
        if winner == 0:
            text = "🤝 It's a draw!"
        else:
            winner_id = [p for p, m in data["players"].items() if m == winner][0]
            loser_id = [p for p in data["players"] if p != winner_id][0]
            await db.add_aura(winner_id, 15)
            await db.add_aura(loser_id, -5)
            await db.record_result(winner_id, True)
            await db.record_result(loser_id, False)
            text = f"🏆 **{data['names'][winner_id]} wins!** +`15` aura. ({data['names'][loser_id]} -`5`)"
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=ttt_keyboard(data["board"], chat_id))

    await query.answer()


# ========================================================
# MATH RACE — open to the whole group, first correct answer wins
# (text resolution lives in listener.py)
# ========================================================
def _make_math_problem():
    a, b = random.randint(2, 50), random.randint(2, 50)
    op = random.choice(["+", "-", "*"])
    expr = f"{a} {op} {b}"
    answer = eval(expr)  # safe: a,b,op are generated internally, not user input
    return expr, answer


@Bot.on_message(filters.command("mathrace") & filters.group, group=9028)
async def mathrace_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return
    expr, answer = _make_math_problem()
    start_game(chat_id, "mathrace", {"expr": expr, "answer": answer})
    await message.reply_text(
        f"➗ **Math Race!** First correct answer wins `10` aura.\n\n`{expr} = ?`",
        parse_mode=ParseMode.MARKDOWN
    )


# ========================================================
# REACTION SPEED — everyone in group taps, fastest wins
# ========================================================
@Bot.on_message(filters.command("reaction") & filters.group, group=6973)
async def reaction_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return

    start_game(chat_id, "reaction_wait", {})
    msg = await message.reply_text("⚡ **Get ready...** tap the button the instant it says GO!")
    delay = random.uniform(3, 8)
    await asyncio.sleep(delay)

    # Someone may have cancelled by starting another game meanwhile
    if get_game(chat_id) and get_game(chat_id)["type"] == "reaction_wait":
        start_game(chat_id, "reaction_go", {"resolved": False})
        await msg.edit_text("⚡ **GO!! TAP NOW!!**", reply_markup=reaction_keyboard(chat_id))


@Bot.on_callback_query(filters.regex(r"^react_(-?\d+)$"), group=3711)
async def reaction_tap(bot: Bot, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    game = get_game(chat_id)

    if not game or game["type"] == "reaction_wait":
        await query.answer("🚫 Too early! You jumped the gun.", show_alert=True)
        return
    if game["type"] != "reaction_go" or game["data"].get("resolved"):
        await query.answer("Already over!", show_alert=True)
        return

    game["data"]["resolved"] = True
    end_game(chat_id)
    winner = query.from_user
    await db.ensure_registered(winner.id, chat_id)
    await db.add_aura(winner.id, 10)
    await db.record_result(winner.id, True)
    await query.message.edit_text(f"⚡ **{winner.first_name} was fastest!** +`10` aura.", parse_mode=ParseMode.MARKDOWN)
    await query.answer("You won! ⚡")


# ========================================================
# HORSE RACE BETTING — open multiplayer betting window, aura wagered
# ========================================================
HORSES = ["🐎 #1", "🐎 #2", "🐎 #3", "🐎 #4", "🐎 #5"]

async def _resolve_horserace(bot: Bot, chat_id: int):
    game = get_game(chat_id)
    if not game or game["type"] != "horserace":
        return
    data = game["data"]
    end_game(chat_id)

    winner_idx = random.randint(0, 4)
    lines = [f"🏁 **The race is over!** Winner: {HORSES[winner_idx]}\n"]
    if not data["bets"]:
        lines.append("Nobody placed a bet.")
    for user_id, (horse, amount) in data["bets"].items():
        name = data["names"].get(user_id, str(user_id))
        if horse == winner_idx:
            payout = amount * 4
            await db.add_aura(user_id, payout)
            await db.record_result(user_id, True)
            lines.append(f"🎉 {name} bet on {HORSES[horse]} — WON `{payout}` aura!")
        else:
            await db.add_aura(user_id, -amount)
            await db.record_result(user_id, False)
            lines.append(f"💀 {name} bet on {HORSES[horse]} — lost `{amount}` aura.")

    await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@Bot.on_message(filters.command("horserace") & filters.group, group=7459)
async def horserace_cmd(bot: Bot, message: Message):
    chat_id = message.chat.id
    args = message.command[1:]
    if len(args) < 2 or not args[0].isdigit() or args[1] not in ("1", "2", "3", "4", "5"):
        await message.reply_text(
            "🐎 Usage: `/horserace <amount> <horse 1-5>`\nOpen for 20s — anyone can join!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    amount = int(args[0])
    horse = int(args[1]) - 1
    user = message.from_user
    await db.ensure_registered(user.id, chat_id)

    if amount <= 0 or amount > await db.get_aura(user.id):
        await message.reply_text("⚠️ You don't have enough aura for that bet.")
        return

    game = get_game(chat_id)
    if game and game["type"] == "horserace":
        if user.id in game["data"]["bets"]:
            await message.reply_text("⚠️ You've already placed a bet on this race.")
            return
        game["data"]["bets"][user.id] = (horse, amount)
        game["data"]["names"][user.id] = user.first_name
        await message.reply_text(f"🐎 {user.first_name} bets `{amount}` aura on {HORSES[horse]}!", parse_mode=ParseMode.MARKDOWN)
        return

    if is_busy(chat_id):
        await message.reply_text("⚠️ Another game is already running here.")
        return

    start_game(chat_id, "horserace", {
        "bets": {user.id: (horse, amount)},
        "names": {user.id: user.first_name},
    })
    await message.reply_text(
        f"🐎 **Horse Race Betting is OPEN for 20 seconds!**\n"
        f"{user.first_name} bets `{amount}` aura on {HORSES[horse]}.\n\n"
        "Others: `/horserace <amount> <horse 1-5>` to join!",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(_delayed_resolve(bot, chat_id))


async def _delayed_resolve(bot: Bot, chat_id: int):
    await asyncio.sleep(20)
    await _resolve_horserace(bot, chat_id)


# ========================================================
# ROULETTE — spin & bet on color or number
# ========================================================
RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

def _roulette_color(n: int) -> str:
    if n == 0:
        return "green"
    return "red" if n in RED_NUMBERS else "black"


@Bot.on_message(filters.command("roulette"), group=9754)
async def roulette_cmd(bot: Bot, message: Message):
    args = message.command[1:]
    if len(args) < 2 or not args[0].isdigit():
        await message.reply_text(
            "🎡 Usage: `/roulette <amount> <red|black|green|0-36>`", parse_mode=ParseMode.MARKDOWN
        )
        return

    amount = int(args[0])
    bet = args[1].lower()
    user = message.from_user
    await db.ensure_registered(user.id, _group_chat_id(message))

    if amount <= 0 or amount > await db.get_aura(user.id):
        await message.reply_text("⚠️ You don't have enough aura for that bet.")
        return

    spin = random.randint(0, 36)
    color = _roulette_color(spin)

    won, payout = False, 0
    if bet in ("red", "black", "green"):
        if bet == color:
            won = True
            payout = amount * (14 if color == "green" else 2)
    elif bet.isdigit() and 0 <= int(bet) <= 36:
        if int(bet) == spin:
            won = True
            payout = amount * 35
    else:
        await message.reply_text("⚠️ Bet must be `red`, `black`, `green`, or a number `0-36`.")
        return

    if won:
        await db.add_aura(user.id, payout)
        await db.record_result(user.id, True)
        text = f"🎡 Ball landed on **{spin} ({color})**.\n🎉 You won `{payout}` aura!"
    else:
        await db.add_aura(user.id, -amount)
        await db.record_result(user.id, False)
        text = f"🎡 Ball landed on **{spin} ({color})**.\n💀 You lost `{amount}` aura."

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ========================================================
# BLACKJACK — solo vs dealer, gamble aura
# ========================================================
def _draw_card():
    return random.choice([2,3,4,5,6,7,8,9,10,10,10,10,11])  # 11 = Ace (simplified)

def _hand_value(hand):
    total = sum(hand)
    aces = hand.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


@Bot.on_message(filters.command("blackjack"), group=4657)
async def blackjack_cmd(bot: Bot, message: Message):
    args = message.command[1:]
    if not args or not args[0].isdigit():
        await message.reply_text("🃏 Usage: `/blackjack <amount>`", parse_mode=ParseMode.MARKDOWN)
        return

    amount = int(args[0])
    user = message.from_user
    chat_id = message.chat.id
    key = f"bj_{chat_id}_{user.id}"
    await db.ensure_registered(user.id, _group_chat_id(message))

    if amount <= 0 or amount > await db.get_aura(user.id):
        await message.reply_text("⚠️ You don't have enough aura for that bet.")
        return

    player = [_draw_card(), _draw_card()]
    dealer = [_draw_card()]
    active_games[key] = {"type": "blackjack", "data": {"player": player, "dealer": dealer, "amount": amount, "user_id": user.id}}

    await message.reply_text(
        f"🃏 **Blackjack** — bet `{amount}` aura\n"
        f"Your hand: {player} = `{_hand_value(player)}`\n"
        f"Dealer shows: {dealer[0]}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=blackjack_keyboard(key)
    )


@Bot.on_callback_query(filters.regex(r"^bj_(hit|stand)_(bj_-?\d+_\d+)$"), group=206)
async def blackjack_action(bot: Bot, query: CallbackQuery):
    action = query.matches[0].group(1)
    key = query.matches[0].group(2)
    game = active_games.get(key)
    if not game or game["type"] != "blackjack":
        await query.answer("This hand is no longer active.", show_alert=True)
        return

    data = game["data"]
    if query.from_user.id != data["user_id"]:
        await query.answer("Not your hand!", show_alert=True)
        return

    if action == "hit":
        data["player"].append(_draw_card())
        pv = _hand_value(data["player"])
        if pv > 21:
            active_games.pop(key, None)
            await db.add_aura(data["user_id"], -data["amount"])
            await db.record_result(data["user_id"], False)
            await query.message.edit_text(
                f"🃏 Your hand: {data['player']} = `{pv}` — **BUST!** -`{data['amount']}` aura.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"🃏 Your hand: {data['player']} = `{pv}`\nDealer shows: {data['dealer'][0]}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=blackjack_keyboard(key)
            )
        await query.answer()
        return

    # stand -> dealer plays
    active_games.pop(key, None)
    dealer = data["dealer"]
    while _hand_value(dealer) < 17:
        dealer.append(_draw_card())

    pv, dv = _hand_value(data["player"]), _hand_value(dealer)
    amount = data["amount"]

    if dv > 21 or pv > dv:
        await db.add_aura(data["user_id"], amount)
        await db.record_result(data["user_id"], True)
        result = f"🎉 **You win!** +`{amount}` aura."
    elif pv == dv:
        result = "🤝 **Push.** Bet returned."
    else:
        await db.add_aura(data["user_id"], -amount)
        await db.record_result(data["user_id"], False)
        result = f"💀 **Dealer wins.** -`{amount}` aura."

    await query.message.edit_text(
        f"🃏 Your hand: {data['player']} = `{pv}`\nDealer hand: {dealer} = `{dv}`\n\n{result}",
        parse_mode=ParseMode.MARKDOWN
    )
    await query.answer()
