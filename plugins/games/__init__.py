"""
games/ — Aura Games Plugin
============================
Drop this folder into your bot's plugins directory (wherever your other
plugin files/folders live, next to the file that defines `Bot`).

Importing this package registers every handler (all @Bot.on_message /
@Bot.on_callback_query decorators run on import), so make sure your bot's
plugin loader imports this package — most Pyrogram/Kurigram bots do this
automatically by scanning the plugins folder, but if yours imports modules
explicitly, add:

    import games  # noqa

somewhere in your bot's startup file.

Commands added to your bot (work in ANY group, not tied to one chat id):
    /games        - show the game menu
    /me           - your own aura/karma/wins stats
    /auraboard    - top aura holders IN THIS GROUP
    /karma        - reply to someone + /karma to give them karma
    /coinflip, /slots, /trivia, /hangman, /emojiquiz, /guessnumber,
    /wordsearch, /dicebattle, /rps, /tictactoe, /mathrace, /reaction,
    /horserace, /roulette, /blackjack

Menu button hook: your bot's main menu should have a button with
callback_data="games" — this plugin listens for exactly that and will
render the game menu in place.
"""
from . import db          # noqa: F401  (loaded first — other modules use it)
from . import state        # noqa: F401
from . import keyboards    # noqa: F401
from . import wordsearch   # noqa: F401
from . import core         # noqa: F401  (registers /games /me /auraboard /karma)
from . import solo         # noqa: F401  (registers solo game commands)
from . import multiplayer  # noqa: F401  (registers multiplayer game commands)
from . import listener     # noqa: F401  (registers the shared text-answer listener)
