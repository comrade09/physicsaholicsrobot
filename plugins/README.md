# Aura Games Plugin

A drop-in Pyrogram/Kurigram plugin that adds a full points-based game system
to your bot, usable in **any group** (not hardcoded to one chat).

## What's inside

```
games/
  __init__.py     # imports everything so handlers register
  db.py           # Mongo (Motor) layer: aura, karma, per-group leaderboard
  state.py        # in-memory "live game" tracker (turns, boards, bets)
  keyboards.py    # inline keyboards (kurigram-style buttons)
  wordsearch.py   # word-search puzzle grid + PIL image renderer
  core.py         # /games menu, menu-button callback, /me, /auraboard, /karma
  solo.py         # coinflip, slots, trivia, hangman, emojiquiz, guessnumber, wordsearch
  multiplayer.py  # dicebattle, rps, tictactoe, mathrace, reaction, horserace, roulette, blackjack
  listener.py     # single shared text handler that resolves all "reply with an answer" games
```

15 games total: **Coin Flip, Slots, Trivia, Hangman, Emoji Quiz, Guess the
Number, Word Search, Dice Duel, Rock-Paper-Scissors, Tic-Tac-Toe, Math Race,
Reaction, Horse Race Betting, Roulette, Blackjack.**

## 1. Install dependencies

```bash
pip install pillow
```

You already have `motor` and `pyrogram`/`kurigram` per your existing bot.

## 2. Wire up your database import

`games/db.py` does:

```python
from database import database
```

This assumes your existing Mongo connection file is importable as
`database` (the file you shared, with `dbclient = AsyncIOMotorClient(...)`
and `database = dbclient[DB_NAME]`). **If that file has a different module
name**, change that one import line in `games/db.py` to match — nothing
else needs to change, since it only uses `database` to open new
collections (`aura`, `karma`, `game_group_members`), so it can't collide
with your existing `users` / `accounts` / `batches` collections.

## 3. Drop the folder in

Copy the whole `games/` folder next to your other plugins (wherever the
file defining `Bot` — e.g. `from bot import Bot` — is importable from).
If your loader auto-imports every plugin folder, you're done. Otherwise,
add this once in your startup file:

```python
import games  # noqa
```

## 4. Hook up your menu button

You said pressing "menu" shows plugin buttons, and you'll add a "Games"
button there. Make that button's `callback_data="games"` — this plugin
already listens for exactly that callback and will render the full game
menu (`games/core.py -> games_menu_callback`). Example button to add to
your existing main menu keyboard:

```python
InlineKeyboardButton("🎮 Games", callback_data="games")
```

## 5. How the points system works

- **Aura** is global per user, but `/auraboard` only ranks users who have
  played in *that specific group* (tracked via a lightweight
  `game_group_members` collection) — so every group gets its own board
  automatically, no per-group config needed.
- Winning a skill game (trivia, hangman, math race, etc.) adds a fixed
  aura reward. Betting games (coin flip, dice duel, horse race, roulette,
  blackjack, slots, RPS, tic-tac-toe) move aura between the pot and the
  player(s) based on the wager.
- **Karma** is a separate, simple reputation counter — reply to someone
  with `/karma` to give them +1 (once per day per pair, so it can't be
  farmed).

## 6. Notes on specific games

- **Word Search**: image is generated locally with Pillow (a 10x10 grid,
  5 hidden words) rather than depending on a third-party image API — this
  keeps it fast, free, and it can't break if some external service goes
  down. Anyone in the group can reply with a spotted word to claim aura
  for it.
- **Horse Race**: genuinely multiplayer — the first bet opens a 20-second
  window, anyone else in the group can join with
  `/horserace <amount> <horse 1-5>` before it resolves.
- **Math Race** and **Reaction** are open to the whole group at once —
  first correct answer / first tap wins, so any number of people (more
  than 2) can compete in the same round.
- All "live" game state (whose turn it is, what number you're guessing,
  who's placed a horse bet) is kept in memory (`games/state.py`) and only
  the **results** (aura/karma/wins) are written to MongoDB — this keeps
  gameplay fast. If you run multiple bot processes/workers behind a load
  balancer, note this in-memory state won't sync across them; for a single
  bot process (the typical setup) it works as-is.

## 7. Commands reference

| Command | Type | What it does |
|---|---|---|
| `/games` | any | Show the game menu |
| `/me` | any | Your aura, karma, wins, losses |
| `/auraboard` | group | Top aura holders in this group |
| `/karma` | reply | Give +1 karma to the replied user |
| `/coinflip <amt> <heads\|tails>` | any | Bet on a coin flip |
| `/slots <amt>` | any | Spin the slot machine |
| `/trivia` | group | Answer a trivia question in chat |
| `/hangman` | group | Guess letters / the word in chat |
| `/emojiquiz` | group | Guess the emoji riddle in chat |
| `/guessnumber` | group | Guess the 1-100 number in chat |
| `/wordsearch` | group | Find hidden words in the puzzle image |
| `/dicebattle <amt>` | group | Anyone can accept a dice duel |
| `/rps <amt>` (as a reply) | group | Rock-paper-scissors vs the replied user |
| `/tictactoe` (as a reply) | group | Tic-tac-toe vs the replied user |
| `/mathrace` | group | First correct answer wins |
| `/reaction` | group | Fastest tap after "GO" wins |
| `/horserace <amt> <1-5>` | group | Open betting window, multiple players |
| `/roulette <amt> <red\|black\|green\|0-36>` | any | Spin the wheel |
| `/blackjack <amt>` | any | Hit/Stand vs the dealer |
